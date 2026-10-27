#!/usr/bin/env python3
"""Attribute synthetic media/configuration changes to upgrade or carried patch."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


media = module("seek_checks", ROOT / "tests/check-seek-stream.py")
provenance = module("provenance", ROOT / "tools/collect-provenance.py")


def require(value, message):
    if not value:
        raise AssertionError(message)


def output(binary, *args):
    return subprocess.check_output([str(binary), "-hide_banner", *args], stderr=subprocess.STDOUT, text=True)


def component_names(kind, text):
    if kind in ["protocols", "bsfs", "hwaccels"]:
        return set(re.findall(r"(?m)^\s*([a-z][a-z0-9_]*)\s*$", text))
    pattern = r"(?m)^\s*[A-Z. ]+\s+([a-zA-Z0-9_,]+)\s+"
    return {name for names in re.findall(pattern, text) for name in names.split(",")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path)
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("ffprobe", type=Path)
    parser.add_argument("old_ffprobe", type=Path)
    parser.add_argument("control_ffprobe", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    bins = [p.resolve() for p in [args.old, args.control, args.candidate]]
    report = {"status": "failed", "binaries": {}, "component_delta": {}, "cases": [], "timing_delta": []}
    args.work_dir.mkdir(parents=True, exist_ok=True)
    try:
        for label, binary in zip(["old", "control", "candidate"], bins):
            report["binaries"][label] = provenance.identity(binary)
        old, control, candidate = [report["binaries"][label] for label in ["old", "control", "candidate"]]
        def config(data):
            line = next(line for line in data["version"].splitlines() if line.strip().startswith("configuration:"))
            return shlex.split(line.split(":", 1)[1])
        control_flags = config(control)
        candidate_flags = config(candidate)
        extra = [flag for flag in candidate_flags if flag.startswith("--extra-version=")]
        pins = dict(line.split(": ", 1) for line in (ROOT / "versions.txt").read_text().splitlines() if ": " in line)
        require(extra == ["--extra-version=seek-stream-" + pins["ffmpeg-patched-tree"][:7]], "candidate version suffix mismatch")
        require([flag for flag in candidate_flags if flag not in extra] == control_flags,
                "candidate/control configure flags differ beyond version suffix")
        require(candidate["needed_libraries"] == control["needed_libraries"], "patch changed linkage")
        if "glibc_max" in control:
            require(set(control["needed_libraries"]) <= set(old["needed_libraries"]), "upgrade added Linux runtime libraries")
            require(tuple(map(int, control["glibc_max"].split("."))) <= tuple(map(int, old["glibc_max"].split("."))),
                    "upgrade raised the required glibc version")
        else:
            require(all(p.startswith(("/System/", "/usr/lib/")) for p in control["needed_libraries"]),
                    "macOS build links a non-system dynamic library")
            require(control["macos_minimum"] is not None, "missing macOS minimum-version metadata")
            # This candidate is for the current fleet, with the old supported
            # minimum retained rather than silently raising its OS requirement.
            require(tuple(map(int, control["macos_minimum"].split("."))) <=
                    tuple(map(int, old["macos_minimum"].split("."))), "upgrade raised minimum macOS")
        kinds = ["encoders", "decoders", "muxers", "demuxers", "filters", "protocols", "bsfs", "hwaccels"]
        listings = {kind: [output(binary, "-" + kind) for binary in bins] for kind in kinds}
        help_text = [output(binary, "-h", "full") for binary in bins]
        for line in (ROOT / "tests/required-features.txt").read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            kind, name = line.split()
            if kind == "input_options":
                option, value = name.split("=", 1)
                results = {}
                with tempfile.TemporaryDirectory(suffix=".noindex", dir=args.work_dir) as temp:
                    source = Path(temp) / "input.f32le"
                    source.write_bytes(bytes(480 * 4))
                    for label, binary in zip(["old", "control", "candidate"], bins):
                        result = subprocess.run([
                            str(binary), "-nostdin", "-v", "error", "-threads", "1",
                            option, value, "-f", "f32le", "-ar", "48000", "-ac", "1",
                            "-i", str(source), "-f", "null", "-",
                        ], capture_output=True, text=True, timeout=30)
                        results[label] = {"exit_code": result.returncode,
                                          "error": result.stderr.splitlines()[:1]}
                report.setdefault("input_option_scopes", {})[name] = results
                require(results["old"]["exit_code"] == 0,
                        f"invalid baseline for required input option {option}")
                rejected = [label for label in ["control", "candidate"]
                            if results[label]["exit_code"] != 0]
                require(not rejected, f"required input option {option} rejected by {', '.join(rejected)}")
                continue
            for label, index in [("control", 1), ("candidate", 2)]:
                if kind == "options":
                    available = re.search(r"(?m)^\s*" + re.escape(name) + r"(?:\s|$)", help_text[index])
                else:
                    available = name in component_names(kind, listings[kind][index])
                require(available, f"required {kind} entry {name} missing in {label}")
        for kind, texts in listings.items():
            names = [component_names(kind, text) for text in texts]
            require(names[1] == names[2], f"patch changed {kind}")
            report["component_delta"][kind] = {"added": sorted(names[1] - names[0]),
                                                "removed": sorted(names[0] - names[1])}
        old_options = set(re.findall(r"(?m)^\s*(-[a-zA-Z0-9_]+)(?:\s|$)", help_text[0]))
        new_options = set(re.findall(r"(?m)^\s*(-[a-zA-Z0-9_]+)(?:\s|$)", help_text[1]))
        candidate_options = set(re.findall(r"(?m)^\s*(-[a-zA-Z0-9_]+)(?:\s|$)", help_text[2]))
        require(candidate_options - new_options == {"-seek_stream"} and not new_options - candidate_options,
                "patch changed CLI options beyond seek_stream")
        report["option_delta"] = {"added": sorted(new_options - old_options), "removed": sorted(old_options - new_options)}

        with tempfile.TemporaryDirectory(suffix=".noindex", dir=args.work_dir) as temp:
            checks = media.Checks(bins[1], args.ffprobe.resolve(), Path(temp))
            checks.fixtures()
            for source in [checks.delayed, checks.offset, checks.bframes, checks.aac, checks.mkv, checks.multi_audio]:
                for before in [[], ["-ss", "1"], ["-ss", "1.000013"], ["-ss", "3.25"],
                               ["-sseof", "-1.5"], ["-seek_timestamp", "1", "-ss", "6"],
                               ["-stream_loop", "1", "-ss", "1"]]:
                    values = [checks.pcm(source, before, ["-t", "0.25"], binary=binary) for binary in bins]
                    require(values[1] == values[2], f"patch changed default PCM: {source.name} {before}")
                    counts = [len(value) // 2 for value in values]
                    row = {"input": source.name, "options": before, "output": "PCM",
                           "samples_old_control_candidate": counts, "candidate_equals_control": True,
                           "upgrade_bytes_equal": values[0] == values[1]}
                    report["cases"].append(row)
                    if source == checks.aac and before == ["-seek_timestamp", "1", "-ss", "6"]:
                        # Verified upstream demux.c change: use the full codec
                        # frame size to discard AAC end padding, not the last
                        # packet's shorter valid duration. The fixture declares
                        # 288000 valid samples; old emits 768 beyond that end.
                        require(counts == [768, 0, 0], "known AAC padding correction changed")
                        row["expected_upgrade_change"] = "Discard 768 AAC padding samples after the declared six-second end"
                    else:
                        require(counts[0] == counts[1], f"unreviewed upgrade sample-count change: {source.name} {before}: {counts}")
            for source, stream in [(checks.bframes, "0:v:0"), (checks.multi_video, "0:v:1")]:
                for copy in [False, True]:
                    for before, after in [([], ["-t", "6"]), (["-ss", "3.25"], ["-t", "0.5"]),
                                          (["-copyts", "-ss", "3.25"], ["-t", "9"])]:
                        values = [checks.packets(source, before, after, stream, copy, binary) for binary in bins]
                        require(values[1] == values[2], "patch changed default video packets")
                        require(len(values[0]) == len(values[1]), "upgrade changed video packet/frame count")
                        report["cases"].append({"input": source.name, "options": before,
                                                "output": "copy" if copy else "rawvideo", "packets": len(values[1]),
                                                "candidate_equals_control": True, "upgrade_bytes_equal": values[0] == values[1]})
            for codec, extension, stream in [("libx264", "mp4", "0:v:0"), ("aac", "m4a", "0:a:0"),
                                              ("libmp3lame", "mp3", "0:a:0"), ("libwebp_anim", "webp", "0:v:0"),
                                              ("gif", "gif", "0:v:0")]:
                values = []
                counts = []
                timings = []
                for index, binary in enumerate(bins):
                    destination = Path(temp) / f"{codec}-{index}.{extension}"
                    flags = ["-ss", "3.25", "-i", checks.bframes, "-t", "0.5", "-map", stream,
                             "-fflags", "+bitexact", "-flags", "+bitexact", "-c", codec, "-threads", "1"]
                    if codec == "libx264":
                        flags += ["-preset", "ultrafast", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
                    checks.run([*flags, destination], binary)
                    values.append(destination.read_bytes())
                    probe = subprocess.check_output([str(args.ffprobe.resolve()), "-v", "error", "-count_frames",
                                                     "-show_entries", "stream=nb_read_frames,start_time,duration,time_base,initial_padding:format=start_time,duration",
                                                     "-of", "json", str(destination)])
                    details = json.loads(probe)
                    counts.append(details["streams"][0].get("nb_read_frames"))
                    timings.append(details)
                require(values[1] == values[2], f"patch changed default {codec} encode")
                require(counts[0] == counts[1], f"upgrade changed {codec} decoded frame count")
                report["cases"].append({"output": codec, "decoded_frames": counts[1], "candidate_equals_control": True,
                                        "upgrade_bytes_equal": values[0] == values[1], "bytes": list(map(len, values)),
                                        "timings_old_control_candidate": timings})
            timing_keys = ["codec_type", "codec_name", "start_time", "duration", "time_base", "nb_frames",
                           "r_frame_rate", "avg_frame_rate", "initial_padding"]
            for source in [checks.delayed, checks.offset, checks.aac, checks.mkv]:
                data = []
                full_probe = []
                for probe in [args.old_ffprobe.resolve(), args.control_ffprobe.resolve(), args.ffprobe.resolve()]:
                    streams = json.loads(subprocess.check_output([str(probe), "-v", "error", "-show_streams",
                                                                 "-show_format", "-of", "json", str(source)]))
                    full_probe.append(streams)
                    data.append({"streams": [{key: stream.get(key) for key in timing_keys} for stream in streams["streams"]],
                                 "format": {key: streams["format"].get(key) for key in ["start_time", "duration"]},
                                 "stream_keys": [sorted(stream) for stream in streams["streams"]]})
                require(full_probe[1] == full_probe[2], "patch changed default ffprobe JSON output")
                report["timing_delta"].append({"input": source.name, "old": data[0], "control": data[1],
                                                "candidate_equals_control": True, "equal": data[0] == data[1]})
        report["status"] = "passed"
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS {len(report['cases'])} old/control/candidate media comparisons")


if __name__ == "__main__":
    main()
