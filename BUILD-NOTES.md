# FFmpeg Build Notes

## Critical: Portable Compiler Flags

All libraries are compiled with these flags on Linux:

```bash
-march=x86-64 -mtune=generic -O2
```

### Why This Matters

**The Problem:**
Without explicit `-march=x86-64 -mtune=generic`, the compiler may optimize for the build machine's CPU (GitHub Actions runner), effectively using `-march=native`. This generates CPU instructions that cause **SIGSEGV segfaults** on Cloud Run's virtualized CPUs.

**The Fix:**
- `-march=x86-64 -mtune=generic` = compile C code for generic x86-64, no fancy instructions
- ASM optimizations stay ENABLED (not disabled) for fast encoding
- Runtime CPU detection in FFmpeg/x264 picks SSE/AVX/AVX2 based on actual CPU features

**Result:** Fast encoding that works everywhere.

### Optional: Hardened Flags (for debugging segfaults)

If you encounter segfaults and need better crash diagnostics, you can enable hardened flags:

```bash
-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2
```

And add `--toolchain=hardened` to FFmpeg's configure.

These provide:
- Better crash diagnostics (clear error messages instead of cryptic segfaults)
- Security against buffer overflows
- Matches Ubuntu's package builds

**Trade-off:** 5-15% performance hit. Only enable if debugging issues.

## Libraries Included

| Library | Purpose |
|---------|---------|
| libx264 | H.264 video encoding |
| dav1d | AV1 software decoding on CPU-only workers |
| libmp3lame | MP3 audio encoding |
| libwebp | WebP image/animation encoding |
| mbedtls | HTTPS URL support |
| libass | ASS/SSA subtitle rendering |
| freetype | Font rendering (for libass) |
| fontconfig | Font configuration (for libass) |
| harfbuzz | Text shaping (for libass) |
| fribidi | Bidirectional text (for libass) |

## What's NOT Included

- VAAPI/DRM hardware acceleration (causes segfaults on Cloud Run - no GPU)
- x265 (not needed, adds build complexity)
- Additional third-party encoder libraries not explicitly enabled above; native FFmpeg codecs remain available according to the recorded build configuration.

## Build Environment

- Ubuntu 22.04 (GitHub Actions runner)
- GCC 11 (same as Ubuntu's FFmpeg package)
- FFmpeg source and carried-patch identities are pinned in `versions.txt`; the previous release used `20b009e30136cb55022ee32cfb4b2dcae1630bb4`.
- Static linking (no shared library dependencies except glibc)

## AV1 decoding

`12-dav1d.sh` builds the pinned, SHA-256-verified VideoLAN archive as a static
library with two compile jobs. FFmpeg links it using `--enable-libdav1d`.
This adds a software decoder, not an AV1 encoder or a GPU requirement.

`91-check-features.sh` runs `tests/check-av1.sh` against both freshly built
binaries. The check decodes both frames of a committed synthetic AV1 fixture
with hardware acceleration disabled. Merely listing FFmpeg's native `av1`
hardware wrapper does not pass: that wrapper cannot decode on a CPU-only worker.

Source changes do not update released or deployed binaries. Before activation,
run the Linux x64 and macOS arm64 build matrix and its existing static-linkage
checks, publish the qualified artifacts, then update the consuming application's
binaries and deployment separately.

## Optional native conversion capacity diagnostic

The manually dispatched `Diagnose conversion capacity` workflow downloads an
existing successful Build run's Linux artifact; it does not rebuild FFmpeg.
It converts the committed synthetic 36-frame, 4096-square, 10-bit 4:4:4 H264
fixture in an isolated 8 GiB / 2 CPU container on a native Linux runner.
The fixture was encoded with `ref=16:bframes=0`; `ffprobe`'s stream-level `refs`
field alone is not a maximum decoded-buffer certificate.

The diagnostic records actual binary checksums, FFmpeg time/RSS, cgroup memory
peak and OOM state, and verifies all 36 output frames. It only qualifies this
small fixture with explicitly limited decoder, filter and encoder threads.
It neither changes application worker tiers nor proves a complete worker fits
that tier after runtime, remote input and large RAM-backed output are included.

When the selected build artifact includes a matched unpatched control, this
diagnostic also runs the current seek regressions against those exact bytes
(including separate 48 kHz and 44.1 kHz audio clocks). It then tests the pinned
old pair, control and candidate sequentially in the same native 2 CPU / 8 GiB
container contract, retaining separate timings, RSS, cgroup/OOM and output
checks. This reuses successful build artifacts; it does not rebuild FFmpeg or
replace `latest`. Reports identify the test script and invoked programs by
SHA256. Single-fixture timings remain observations, not a worker cost estimate.

## 2026-10-08 AV1 artifact qualification

Build run `37806734886` passed on native Linux x64 and macOS arm64 at source
commit `70c48afce7457cb81e9d34665f7c876874c4e2c7`. It ran actual default AV1 CPU
decoding with both FFmpeg and FFprobe, preserved the animated GIF/WebP file and
stdin checks, and passed the existing platform-linkage workflow checks.
The diagnostic/docs-only commits after that source commit do not change those
binary build inputs. Their qualification-record commit skips a redundant full
matrix; the separate capacity diagnostic is run explicitly against its artifact.

## Debugging Segfaults

If you see segfaults, check:

1. **With hardened flags:** You'll see `*** stack smashing detected ***` or `*** buffer overflow detected ***` instead of just `Segmentation fault`

2. **CPU compatibility:** Run `ffmpeg -version` and check the `configuration:` line includes `--enable-runtime-cpudetect`

3. **Compare with Ubuntu's package:**
   ```bash
   docker run --rm --platform linux/amd64 ubuntu:22.04 bash -c \
     "apt update && apt install -y ffmpeg && ffmpeg -version"
   ```
   See `ubuntu-22.04-ffmpeg-flags.txt` for the full configuration.

## Carried seek-reference patch and qualification

The optional input `-seek_stream a:0` selects the first audio stream as the
reference for the initial `-ss`/`-sseof` seek. Put it before the relevant `-i`.
It does not choose output streams, change the file clock, or change loop seeks.
Omitting it follows the existing automatic reference path. Demuxer seeking and
other-track decodability remain format-dependent. In particular, an MKV seek
can still scan bytes; this option is not a universal fast-seek guarantee.

Sample-exact replacement of linear trimming also needs application testing.
The rc2 macOS binaries matched linear PCM trimming for long PCM MOV/MKV and
AAC MP4 fixtures, but a ten-minute 48 kHz AAC MKV with its first picture at
300 seconds yielded 48,008 samples when seeking to 250 seconds for one second,
versus 48,000 with linear `atrim`; the selected window began eight samples
(about 0.17 ms) earlier. Keep a sample-sensitive application workaround until
its real commands and media are qualified. Passing short AAC cases alone does
not establish this equivalence.

The source pin, patch SHA256, expected whole-source tree and upstream links
live in `versions.txt`. `tools/prepare-ffmpeg.py` checks a fresh exact checkout,
applies with Git's index, and verifies the reviewed tree before configure.
Dirty, incompatible, changed or already integrated inputs stop the build.
Patched builds carry a `seek-stream-<tree>` version suffix; the matched control
is unpatched. Dependency pins and codec/CPU flags are preserved. Compiler jobs
are limited to two per native platform runner; the control reuses that runner's
dependency builds, without rebuilding libraries or running on Ethan's Mac.

Every build runs generated-media seek/content regressions and all nine carried
FATE cases, plus the existing real AV1 and animated GIF/WebP checks. Candidate
qualification additionally compares the checksum-pinned previous release,
matched new-unpatched control, and candidate: configuration, required features,
linkage, glibc/macOS minimum, default decode/copy/encode outputs, and ffprobe
fields. It runs full FATE without external samples and Linux CPU fallback tests
under QEMU Nehalem without AVX. Reports and provenance are release assets.
An old/control byte or metadata difference is recorded as upgrade evidence;
required features, output counts, platform requirements and candidate/control
default equality are gates. Native-runner and emulated-CPU checks do not qualify
the actual cloud image, remote HTTP/Range input, browser timing or every codec.

Publish a new, never-reused `*-seek-stream-rcN` tag from the candidate branch.
The release workflow enables qualification and uses `--prerelease --latest=false`.
The normal main/latest paths remain untouched until application qualification.
Use the exact candidate and control digests in testing; do not rebuild after a
successful qualification and assume the bytes are equivalent. Keep the old
release pair by digest for rollback. Removing the option restores automatic
seeking for the new version; restoring the old binary pair also reverses the
upstream upgrade. Do not remove an application workaround until its owner has
qualified real media, previews, timing, CPU, latency, memory and I/O.

Local generated outputs belong in `build.noindex/` or task-owned external
scratch. To run the media checks against isolated binaries:

```sh
python3 tests/check-seek-stream.py /path/to/candidate/ffmpeg /path/to/candidate/ffprobe \
  --unpatched /path/to/control/ffmpeg --work-dir /external/scratch/tests.noindex \
  --report /external/scratch/seek-results.json
```

Source identity is reproducible from the pin and patch. OS package bootstrap,
compiler and hosted runner images still move; provenance records them but this
does not promise bit-identical recompilation. Bumping the pin or changing the
carried patch requires repeating qualification. Drop/reconcile the patch when
an equivalent upstream change lands, rather than silently skipping it.

Observed upgrade delta: the new upstream demuxer drops AAC encoder padding at
the declared audio end. A six-second, 48 kHz MP4 previously yielded 768 extra
samples (16 ms); the unpatched control and patched version both stop at six
seconds. Qualification checks this exact correction and gates other unexpected
sample-count changes. Application qualification must include audio end timing.
On macOS the upstream pin also auto-detects the system libcurl protocol; native
HTTP/HTTPS remains the default (`prefer_libcurl=0`). Linux dependency names and
glibc 2.35 remain unchanged in the first native comparison.
