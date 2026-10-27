# Repository Learnings

- A scheduled or manually dispatched `latest` release must build, check out, and tag the same immutable commit SHA. Deleting only the GitHub release leaves the movable `latest` tag pointing at its previous commit.
- Animated-image support is not proven by decoder or demuxer listings alone. Generate two-frame GIF and WebP fixtures, count decoded frames from files, and repeat decoding through non-seekable stdin streams on every supported platform.
- Pass multi-word compiler flags to CMake through `CFLAGS`; expanding them as one unquoted command-line variable makes flags such as `-O2` become unknown CMake arguments.

- A shallow unpatched checkout and an index-applied patch retain the same Git HEAD. Use a patch/tree-identifying FFmpeg `--extra-version` suffix plus a verified full source tree and binary SHA256; the upstream version string alone cannot distinguish the candidate. Verified against FFmpeg's version script and the actual patch application.
- Run `gh` with explicit `-R EthanSK/static-ffmpeg-binaries`: this clone's `upstream` remote is marked as the resolved GitHub base, so an implicit repository could target shaka-project.
- Check copied packet timestamps with `-copyts -copypriorss 1` near a stream-time-base boundary. Accurate decode trimming can hide a rounded-forward seek. The synthetic PCM regression rejects a deliberately wrong target and verifies the first packet is at or before the requested timestamp.
