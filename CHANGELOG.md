# Unreleased

 - Pin FFmpeg to the first upstream revision with native animated WebP demuxing and decoding.
 - Verify release binaries can decode every frame of generated animated GIF and WebP files, including through stdin streams.
 - Keep manual and monthly `latest` releases pinned to the exact commit that produced their binaries.
 - Build and validate every push to `main`.

# n7.1-1

 - Update FFmpeg to n7.1 (PR #48)
 - Upgrade all deps (PR #32)
 - Switch from libaom to libsvtav1 (PR #27)
 - Stabilize versions of x264, x265 (PR #19)
 - Enable Linux hardware encoding with Ubuntu-specific dynamic builds (PR #48, issue #10)
 - Fully-static Linux builds based on musl and Alpine Linux (PR #42, issue #28)
 - Add macOS arm64 builds (PR #41, issue #40)


# n4.4-2

Fix missing TLS support in FFmpeg and FFprobe (#2, PR #3)


# n4.4-1

Initial release (PR #1)
