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
| libmp3lame | MP3 audio encoding |
| libwebp | WebP image/animation support |
| mbedtls | HTTPS URL support |
| libass | ASS/SSA subtitle rendering |
| freetype | Font rendering (for libass) |
| fontconfig | Font configuration (for libass) |
| harfbuzz | Text shaping (for libass) |
| fribidi | Bidirectional text (for libass) |

## What's NOT Included

- VAAPI/DRM hardware acceleration (causes segfaults on Cloud Run - no GPU)
- x265 (not needed, adds build complexity)
- Most other codecs (not needed for our use case)

## Build Environment

- Ubuntu 22.04 (GitHub Actions runner)
- GCC 11 (same as Ubuntu's FFmpeg package)
- FFmpeg n7.1
- Static linking (no shared library dependencies except glibc)

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
