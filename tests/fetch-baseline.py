#!/usr/bin/env python3
"""Download only the checksum-pinned previous release pair for this platform."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("suffix")
parser.add_argument("output", type=Path)
args = parser.parse_args()
baseline = json.loads((Path(__file__).parent / "qualification-baseline.json").read_text())
args.output.mkdir(parents=True, exist_ok=True)
selected = [asset for asset in baseline["assets"] if asset["name"].endswith(args.suffix)]
if len(selected) != 2:
    raise ValueError("Expected one pinned ffmpeg/ffprobe baseline pair")
for asset in selected:
    subprocess.run(["gh", "release", "download", baseline["tag_name"],
                    "-R", "EthanSK/static-ffmpeg-binaries", "--pattern", asset["name"],
                    "--dir", str(args.output)], check=True)
    binary = args.output / asset["name"]
    if "sha256:" + hashlib.sha256(binary.read_bytes()).hexdigest() != asset["digest"]:
        raise ValueError("Previous release changed; qualification baseline digest mismatch")
    binary.chmod(0o755)
    version = subprocess.check_output([str(binary.resolve()), "-version"], text=True)
    if baseline["ffmpeg_commit"][:7] not in version.splitlines()[0]:
        raise ValueError("Previous release version does not match its source pin")
print("Verified previous release pair against the recorded SHA256 digests")
