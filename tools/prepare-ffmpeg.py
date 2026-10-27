#!/usr/bin/env python3
"""Fail closed unless the checkout and carried patch have their reviewed trees."""

import argparse
import hashlib
from pathlib import Path
import subprocess


def versions(repo):
    return dict(line.split(": ", 1) for line in
                (repo / "versions.txt").read_text().splitlines() if ": " in line)


def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()


def prepare(repo, source, control=False):
    config = versions(repo)
    if git(source, "rev-parse", "HEAD") != config["ffmpeg"]:
        raise ValueError("FFmpeg checkout does not match the pinned commit")
    if git(source, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("FFmpeg checkout/index is not clean; refusing to reuse or reapply")
    if '"seek_stream"' in (source / "fftools/ffmpeg_opt.c").read_text():
        raise ValueError("Upstream already defines seek_stream; drop or reconcile the patch")
    patch = repo / config["ffmpeg-patch"]
    if hashlib.sha256(patch.read_bytes()).hexdigest() != config["ffmpeg-patch-sha256"]:
        raise ValueError("Carried FFmpeg patch SHA256 mismatch")
    if control:
        return git(source, "rev-parse", "HEAD^{tree}")
    # git apply has no fuzzy-context fallback; the exact source pin, clean
    # index and final whole-tree equality also reject offsets or partial edits.
    git(source, "apply", "--index", "--check", "--whitespace=error-all", str(patch))
    git(source, "apply", "--index", "--whitespace=error-all", str(patch))
    tree = git(source, "write-tree")
    if tree != config["ffmpeg-patched-tree"]:
        raise ValueError(f"Patched source tree {tree} differs from the reviewed tree")
    return tree


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    print(prepare(args.repo.resolve(), args.source.resolve(), args.control))
