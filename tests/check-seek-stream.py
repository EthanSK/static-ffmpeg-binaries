#!/usr/bin/env python3
"""Offline content regressions for the optional initial input seek reference.

All inputs are synthetic. No playback, network input, or shared binary changes.
An optional matched unpatched build isolates patch effects from upstream drift.
"""

import argparse
from fractions import Fraction
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import wave


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class Checks:
    def __init__(self, ffmpeg, ffprobe, directory, unpatched=None):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.directory = directory
        self.unpatched = unpatched
        self.results = []

    def run(self, args, binary=None, success=True):
        result = subprocess.run(
            [str(binary or self.ffmpeg), "-nostdin", "-hide_banner", "-v", "error",
             "-y", "-threads", "1", "-filter_threads", "1",
             *map(str, args)], capture_output=True, timeout=60,
        )
        if success and result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace"))
        return result

    def record(self, name, **details):
        self.results.append({"case": name, "status": "passed", **details})
        print(f"PASS {name}", flush=True)

    def pcm(self, source, before, after, stream="0:a:0", binary=None, rate=48000):
        output = self.run([
            *before, "-i", source, *after, "-map", stream,
            "-c:a", "pcm_s16le", "-threads", "1", "-f", "wav", "pipe:1",
        ], binary).stdout
        with wave.open(io.BytesIO(output)) as audio:
            require(audio.getparams()[:3] == (1, 2, rate), "unexpected PCM format")
            return audio.readframes(audio.getnframes())

    def packets(self, source, before, after, stream="0:v:0", copy=False,
                binary=None):
        data = self.run([
            *before, "-i", source, *after, "-map", stream,
            "-c", "copy" if copy else "rawvideo", "-threads", "1", "-f", "framecrc", "pipe:1",
        ], binary).stdout
        # Build/version comments are not media. Keep every packet field,
        # including timestamps, duration, size and content checksum.
        return [line for line in data.splitlines() if line and not line.startswith(b"#")]

    def fixtures(self):
        def generate(args):
            return self.run(args, binary=self.unpatched)
        # A non-silent, changing sample vector gives an independent oracle for
        # position and content, rather than accepting silence of the right length.
        self.raw = b"".join(struct.pack("<h", (i * 97) % 24001 - 12000)
                            for i in range(48000 * 6))
        self.second = b"".join(struct.pack("<h", -(i * 71 % 20001 - 10000))
                               for i in range(44100 * 6))
        for name, data, rate in [("first.wav", self.raw, 48000), ("second.wav", self.second, 44100)]:
            with wave.open(str(self.directory / name), "wb") as audio:
                audio.setparams((1, 2, rate, 0, "NONE", "not compressed"))
                audio.writeframes(data)
        self.delayed = self.directory / "delayed.mov"
        self.offset = self.directory / "offset.mov"
        self.multi_audio = self.directory / "multi-audio.mov"
        self.multi_video = self.directory / "multi-video.mov"
        self.bframes = self.directory / "bframes.mov"
        for destination, codec, bframes in [
            (self.delayed, "mpeg4", "0"), (self.bframes, "libx264", "2"),
        ]:
            generate([
                "-itsoffset", "3", "-f", "lavfi", "-i", "testsrc2=s=32x32:r=10:d=3",
                "-i", self.directory / "first.wav", "-map", "0:v", "-map", "1:a",
                "-c:v", codec, "-threads:v", "1", "-g", "10", "-bf", bframes,
                "-fps_mode", "passthrough", "-c:a", "pcm_s16le",
                "-metadata:s:a:0", "handler_name=seek-audio", destination,
            ])
        generate(["-i", self.delayed, "-map", "0", "-c", "copy",
                  "-output_ts_offset", "5", self.offset])
        generate([
            "-i", self.directory / "first.wav", "-itsoffset", "2",
            "-i", self.directory / "second.wav", "-map", "0:a", "-map", "1:a",
            "-c:a", "pcm_s16le", self.multi_audio,
        ])
        generate([
            "-itsoffset", "3", "-f", "lavfi", "-i", "testsrc2=s=32x32:r=10:d=3",
            "-f", "lavfi", "-i", "testsrc2=s=32x32:r=10:d=6",
            "-map", "0:v", "-map", "1:v", "-c:v", "mpeg4", "-threads:v", "1",
            "-g", "10", "-bf", "0", "-fps_mode", "passthrough", self.multi_video,
        ])
        probe = subprocess.run([
            str(self.ffprobe), "-v", "error", "-show_streams", "-of", "json",
            str(self.delayed),
        ], capture_output=True, check=True, timeout=30)
        streams = json.loads(probe.stdout)["streams"]
        require([(s["codec_type"], float(s["start_time"])) for s in streams]
                == [("video", 3.0), ("audio", 0.0)], "fixture lost delayed video")
        probe = subprocess.run([
            str(self.ffprobe), "-v", "error", "-show_streams", "-of", "json",
            str(self.bframes),
        ], capture_output=True, check=True, timeout=30)
        require(json.loads(probe.stdout)["streams"][0]["has_b_frames"] > 0,
                "B-frame fixture contains no reordered frames")
        probe = subprocess.run([
            str(self.ffprobe), "-v", "error", "-show_entries", "stream=sample_rate,time_base",
            "-of", "json", str(self.multi_audio),
        ], capture_output=True, check=True, timeout=30)
        require([(s["sample_rate"], s["time_base"]) for s in json.loads(probe.stdout)["streams"]]
                == [("48000", "1/48000"), ("44100", "1/44100")],
                "multi-audio fixture lost its distinct stream clocks")
        self.aac = self.directory / "delayed-aac.mp4"
        self.mkv = self.directory / "delayed-aac.mkv"
        generate(["-i", self.bframes, "-map", "0", "-c:v", "copy", "-c:a", "aac", self.aac])
        generate(["-i", self.aac, "-map", "0", "-c", "copy", self.mkv])

    def check(self):
        self.fixtures()
        if self.unpatched:
            control = self.run([
                "-ss", "1", "-seek_stream", "a:0", "-i", self.delayed,
                "-t", "0.1", "-f", "null", "-",
            ], binary=self.unpatched, success=False)
            require(control.returncode > 0 and b"Unrecognized option 'seek_stream'" in control.stderr,
                    "comparison binary is not an unpatched control")
            self.record("control-rejects-new-option")
        expected = self.raw[48000 * 2:60000 * 2]
        missing = self.pcm(self.delayed, ["-ss", "1"], ["-t", "0.25"])
        require(not missing, "fixture no longer reproduces the missing early audio")
        self.record("automatic-seek-reproduces-issue", samples=0)
        for selector in ["a:0", "1", "m:handler_name:seek-audio"]:
            actual = self.pcm(self.delayed, ["-ss", "1", "-seek_stream", selector],
                              ["-t", "0.25"])
            require(actual == expected, f"wrong audio content for {selector}")
            self.record(f"selected-{selector}", samples=len(actual) // 2,
                        sha256=hashlib.sha256(actual).hexdigest())

        for source in [self.delayed, self.offset, self.bframes]:
            for at in ["1", "1.000013", "0.5001", "3.25"]:
                reference = self.pcm(source, [], ["-ss", at, "-t", "0.25"])
                selected = self.pcm(source, ["-ss", at, "-seek_stream", "a:0"],
                                    ["-t", "0.25"])
                require(len(reference) == 24000 and selected == reference,
                        f"wrong seek/trim content: {source.name} at {at}")
                self.record(f"content-{source.stem}-{at}", samples=12000)
                if self.unpatched:
                    before = ["-ss", at]
                    old = self.pcm(source, before, ["-t", "0.25"], binary=self.unpatched)
                    new = self.pcm(source, before, ["-t", "0.25"])
                    require(new == old, "patch changed automatic seek output")
                    if source == self.delayed and at == "1":
                        require(not old, "fixture no longer reproduces missing early audio")
                    self.record(f"default-equal-{source.stem}-{at}", samples=len(new) // 2)

        for before in [["-ss", "1"], ["-seek_timestamp", "1", "-ss", "6"],
                       ["-sseof", "-5"]]:
            actual = self.pcm(self.offset, [*before, "-seek_stream", "a:0"],
                              ["-t", "0.25"])
            require(actual == expected, f"timestamp origin changed for {before}")
            self.record("offset-" + "-".join(before))

        # Accurate decoding can hide an early/late demuxer seek. Preserve the
        # source timestamps and copied prior packet to test the seek itself.
        initial = self.packets(self.offset, ["-copyts"], ["-t", "5.1"], "0:a:0", copy=True)
        packet_ticks = int(initial[0].split(b",")[3])
        boundary = Fraction(packet_ticks * 47, 48000)
        target_us = boundary * 1000000
        microseconds = target_us.numerator // target_us.denominator
        if Fraction(microseconds, 1000000) == boundary:
            microseconds -= 1
        at = f"{microseconds // 1000000}.{microseconds % 1000000:06d}"
        target = Fraction(5) + Fraction(at)

        def seek_packet(seek_at):
            packets = self.packets(self.offset, ["-copyts", "-ss", seek_at,
                                   "-seek_stream", "a:0"],
                                   ["-copypriorss", "1", "-t", "9"], "0:a:0", copy=True)
            require(packets, "stream-copy position probe returned no packets")
            return Fraction(int(packets[0].split(b",")[2]), 48000)

        def in_window(timestamp):
            return target - Fraction(packet_ticks, 48000) < timestamp <= target

        first = seek_packet(at)
        require(in_window(first), "stream-copy seek rounded forward or used the wrong origin")
        wrong = seek_packet(str(float(at) + 1))
        require(not in_window(wrong), "seek-position oracle accepted a deliberately wrong target")
        self.record("packet-position-and-rounding", seek=at, first_pts=str(first),
                    wrong_target_rejected=True)

        for source in [self.aac, self.mkv]:
            actual = self.pcm(source, ["-ss", "1", "-seek_stream", "a:0"], ["-t", "1"])
            require(len(actual) == 96000, f"wrong AAC sample count in {source.name}")
            self.record(f"AAC-{source.suffix[1:]}", samples=48000)

        input_to = self.pcm(self.delayed, ["-ss", "1", "-to", "1.25", "-seek_stream", "a:0"], [])
        require(input_to == expected, "input -to changed the selected window")
        self.record("input-to", samples=12000)

        for selector in ["a:1", "1"]:
            actual = self.pcm(self.multi_audio, ["-ss", "2.5", "-seek_stream", selector],
                              ["-t", "0.25"], "0:a:1", rate=44100)
            require(actual == self.second[22050 * 2:33075 * 2], "wrong second audio")
            self.record(f"second-audio-{selector}", samples=11025, sample_rate=44100)

        trimmed = self.pcm(
            self.delayed, ["-ss", "1", "-seek_stream", "a:0"],
            ["-af", "atrim=start=0.1:duration=0.25,asetpts=PTS-STARTPTS"],
        )
        require(trimmed == self.raw[52800 * 2:64800 * 2], "seek plus filter trim changed content")
        self.record("seek-then-atrim", samples=12000)

        reference = self.packets(self.multi_video, [], ["-ss", "1", "-t", "0.5"], "0:v:1")
        for selector in ["v:1", "1"]:
            selected = self.packets(self.multi_video, ["-ss", "1", "-seek_stream", selector],
                                    ["-t", "0.5"], "0:v:1")
            require(len(reference) == 5 and selected == reference, "wrong second video")
            self.record(f"second-video-{selector}", frames=len(selected))

        # The option affects initial seeking, not loop seeks. This case has no
        # initial seek. Stream-copy comparison explicitly chooses the reference
        # video already used by the default; arbitrary references need not match.
        for name, source, before, after, stream, selector in [
            ("loop-no-initial-seek", self.delayed, ["-stream_loop", "1"], [], "0:a:0", "a:0"),
            ("B-frame-streamcopy", self.bframes, ["-ss", "3.25"], ["-t", "0.5"], "0:v:0", "v:0"),
            ("copyts-default-reference", self.bframes, ["-copyts", "-ss", "3.25"], ["-t", "6"], "0:v:0", "v:0"),
        ]:
            default = self.packets(source, before, after, stream, copy=True)
            selected = self.packets(source, [*before, "-seek_stream", selector],
                                    after, stream, copy=True)
            require(default and selected == default, f"compatibility changed: {name}")
            if self.unpatched:
                old = self.packets(source, before, after, stream, copy=True, binary=self.unpatched)
                require(default == old, f"automatic compatibility changed: {name}")
            self.record(name, packets=len(selected))

        for selector, message, source in [
            ("a:bogus", "Trailing garbage", self.delayed),
            ("a:9", "matches no streams", self.delayed),
            ("", "matches multiple streams", self.delayed),
            ("a", "matches multiple streams", self.multi_audio),
            ("m:handler_name:missing", "matches no streams", self.delayed),
        ]:
            result = self.run(["-ss", "1", "-seek_stream", selector, "-i", source,
                               "-t", "0.1", "-f", "null", "-"], success=False)
            require(result.returncode > 0 and message in result.stderr.decode(errors="replace"),
                    f"wrong error or signal for {selector!r}")
            self.record(f"reject-{selector!r}", exit_code=result.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ffmpeg", type=Path)
    parser.add_argument("ffprobe", type=Path)
    parser.add_argument("--unpatched", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="seek-", suffix=".noindex", dir=args.work_dir) as directory:
        checks = Checks(args.ffmpeg.resolve(), args.ffprobe.resolve(), Path(directory),
                        args.unpatched.resolve() if args.unpatched else None)
        status = "failed"
        try:
            checks.check()
            status = "passed"
        finally:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            programs = {"ffmpeg": args.ffmpeg, "ffprobe": args.ffprobe}
            if args.unpatched:
                programs["unpatched"] = args.unpatched
            identities = {name: {"path": str(path), "invoked_program_sha256":
                                hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None}
                          for name, path in programs.items()}
            args.report.write_text(json.dumps({"status": status, "checks": checks.results,
                                              "matched_control": bool(args.unpatched),
                                              "invoked_programs": identities,
                                              "test_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                              "test_commit": os.environ.get("GITHUB_SHA")}, indent=2) + "\n")


if __name__ == "__main__":
    main()
