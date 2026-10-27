"""Exercise fail-closed patch application using real disposable Git indexes."""

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "prepare_ffmpeg", Path(__file__).resolve().parents[1] / "tools/prepare-ffmpeg.py")
prepare_ffmpeg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_ffmpeg)


class PatchTests(unittest.TestCase):
    def git(self, *args):
        return subprocess.check_output([
            "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
            "-C", str(self.source), *args,
        ], text=True).strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(suffix=".noindex", dir=os.environ.get("FFMPEG_TEST_TMP"))
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.source = self.repo / "source"
        self.source.mkdir()
        self.git("init", "-q")
        self.code = self.source / "fftools/ffmpeg_opt.c"
        self.code.parent.mkdir()
        self.code.write_text("original\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        base = self.git("rev-parse", "HEAD")
        self.code.write_text('original\n"seek_stream"\n')
        self.git("add", ".")
        tree = self.git("write-tree")
        self.patch = self.repo / "seek.patch"
        self.patch.write_text(self.git("diff", "--cached", "--full-index") + "\n")
        self.git("reset", "--hard", "-q", "HEAD")
        self.config = {"ffmpeg": base, "ffmpeg-patch": "seek.patch",
                       "ffmpeg-patch-sha256": hashlib.sha256(self.patch.read_bytes()).hexdigest(),
                       "ffmpeg-patched-tree": tree}
        self.save_config()

    def save_config(self):
        (self.repo / "versions.txt").write_text("".join(f"{k}: {v}\n" for k, v in self.config.items()))

    def test_exact_reviewed_tree(self):
        self.assertEqual(prepare_ffmpeg.prepare(self.repo, self.source), self.config["ffmpeg-patched-tree"])
        self.assertIn('"seek_stream"', self.code.read_text())

    def test_control_remains_clean_and_unpatched(self):
        self.assertEqual(prepare_ffmpeg.prepare(self.repo, self.source, True), self.git("rev-parse", "HEAD^{tree}"))
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.code.read_text(), "original\n")

    def test_reapplication_is_rejected(self):
        prepare_ffmpeg.prepare(self.repo, self.source)
        with self.assertRaisesRegex(ValueError, "not clean"):
            prepare_ffmpeg.prepare(self.repo, self.source)

    def test_wrong_source_pin_is_rejected(self):
        self.config["ffmpeg"] = "0" * 40
        self.save_config()
        with self.assertRaisesRegex(ValueError, "pinned commit"):
            prepare_ffmpeg.prepare(self.repo, self.source)

    def test_dirty_source_is_rejected(self):
        self.code.write_text("unrelated edits\n")
        with self.assertRaisesRegex(ValueError, "not clean"):
            prepare_ffmpeg.prepare(self.repo, self.source)
        self.assertEqual(self.code.read_text(), "unrelated edits\n")

    def test_wrong_patch_digest_is_rejected(self):
        self.patch.write_text(self.patch.read_text() + "unexpected text\n")
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            prepare_ffmpeg.prepare(self.repo, self.source)

    def test_wrong_reviewed_tree_is_rejected(self):
        self.config["ffmpeg-patched-tree"] = "0" * 40
        self.save_config()
        with self.assertRaisesRegex(ValueError, "reviewed tree"):
            prepare_ffmpeg.prepare(self.repo, self.source)

    def test_incompatible_patch_is_rejected_before_editing(self):
        self.patch.write_text(self.patch.read_text().replace(" original\n", " missing context\n"))
        self.config["ffmpeg-patch-sha256"] = hashlib.sha256(self.patch.read_bytes()).hexdigest()
        self.save_config()
        with self.assertRaises(subprocess.CalledProcessError):
            prepare_ffmpeg.prepare(self.repo, self.source)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_already_integrated_source_is_rejected(self):
        self.code.write_text('original\n"seek_stream"\n')
        self.git("add", ".")
        self.git("commit", "-qm", "upstream implementation")
        self.config["ffmpeg"] = self.git("rev-parse", "HEAD")
        self.save_config()
        with self.assertRaisesRegex(ValueError, "already defines"):
            prepare_ffmpeg.prepare(self.repo, self.source)


if __name__ == "__main__":
    unittest.main()
