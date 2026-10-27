#!/usr/bin/env python3
"""Record source identity, actual binary configuration, linkage and SHA256."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def command(*args):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True)
    return {"exit_code": result.returncode, "output": (result.stdout + result.stderr).strip()}


def identity(binary):
    version = command(binary.resolve(), "-version")
    if version["exit_code"]:
        raise RuntimeError(version["output"])
    data = {"sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "size": binary.stat().st_size, "version": version["output"],
            "buildconf": command(binary.resolve(), "-buildconf")["output"]}
    if os.uname().sysname == "Linux":
        dynamic = command("readelf", "-d", binary)
        symbols = command("readelf", "--version-info", binary)
        if dynamic["exit_code"] or symbols["exit_code"]:
            raise RuntimeError("Cannot inspect Linux linkage")
        data["needed_libraries"] = sorted(re.findall(r"Shared library: \[(.*?)\]", dynamic["output"]))
        versions = re.findall(r"GLIBC_([0-9.]+)", symbols["output"])
        data["glibc_max"] = max(versions, key=lambda v: tuple(map(int, v.split(".")))) if versions else None
    elif os.uname().sysname == "Darwin":
        linked = command("otool", "-L", binary)
        if linked["exit_code"]:
            raise RuntimeError(linked["output"])
        data["needed_libraries"] = [line.strip().split(" (", 1)[0]
                                    for line in linked["output"].splitlines()[1:] if line.strip()]
        load_commands = command("otool", "-l", binary)["output"]
        minimum = re.search(r"\bminos\s+([0-9.]+)", load_commands)
        if not minimum:
            minimum = re.search(r"LC_VERSION_MIN_MACOSX\s+cmdsize\s+\d+\s+version\s+([0-9.]+)", load_commands)
        data["macos_minimum"] = minimum.group(1) if minimum else None
        data["signature"] = command("codesign", "--verify", "--verbose=2", binary)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("assets", type=Path)
    parser.add_argument("suffix")
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    pins = dict(line.split(": ", 1) for line in (repo / "versions.txt").read_text().splitlines() if ": " in line)
    prefix = "control-unpatched-" if args.control else ""
    binaries = {}
    args.assets.mkdir(parents=True, exist_ok=True)
    for name in ["ffmpeg", "ffprobe"]:
        source = args.source / name
        filename = prefix + name + args.suffix
        destination = args.assets / filename
        destination.write_bytes(source.read_bytes())
        destination.chmod(0o755)
        binaries[filename] = identity(destination)
    config = (args.source / "ffbuild/config.mak").read_text()
    source_commit = subprocess.check_output(["git", "-C", str(args.source), "rev-parse", "HEAD"], text=True).strip()
    source_tree = subprocess.check_output(["git", "-C", str(args.source), "write-tree"], text=True).strip()
    expected_tree = (subprocess.check_output(["git", "-C", str(args.source), "rev-parse", "HEAD^{tree}"], text=True).strip()
                     if args.control else pins["ffmpeg-patched-tree"])
    if source_commit != pins["ffmpeg"] or source_tree != expected_tree:
        raise ValueError("Built source identity no longer matches the pinned reviewed input")
    if hashlib.sha256((repo / pins["ffmpeg-patch"]).read_bytes()).hexdigest() != pins["ffmpeg-patch-sha256"]:
        raise ValueError("Carried patch digest changed during the build")
    dependencies = {}
    for path in args.source.parent.iterdir():
        if path.name not in ["repo-src", "ffmpeg", "ffmpeg-control"] and (path / ".git").exists():
            dependencies[path.name] = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    result = {
        "build_repository_commit": command("git", "-C", repo, "rev-parse", "HEAD")["output"],
        "source_commit": source_commit, "source_tree": source_tree,
        "patch_applied": not args.control, "pins": pins,
        "host": command("uname", "-a")["output"], "compiler": command("cc", "--version")["output"],
        "runner": {key: os.environ.get(key) for key in
                   ["GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "ImageOS", "ImageVersion"]},
        "compile_flags": dict(re.findall(r"^(CFLAGS|LDFLAGS)\s*[:?+]?=\s*(.*)$", config, re.MULTILINE)),
        "binaries": binaries,
        "dependency_source_commits": dependencies,
    }
    output = args.assets / (prefix + "provenance" + args.suffix + ".json")
    output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
