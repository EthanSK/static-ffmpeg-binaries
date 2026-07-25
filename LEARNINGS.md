# Repository Learnings

- A scheduled or manually dispatched `latest` release must build, check out, and tag the same immutable commit SHA. Deleting only the GitHub release leaves the movable `latest` tag pointing at its previous commit.
- Animated-image support is not proven by decoder or demuxer listings alone. Generate two-frame GIF and WebP fixtures, count decoded frames from files, and repeat decoding through non-seekable stdin streams on every supported platform.
- Pass multi-word compiler flags to CMake through `CFLAGS`; expanding them as one unquoted command-line variable makes flags such as `-O2` become unknown CMake arguments.
