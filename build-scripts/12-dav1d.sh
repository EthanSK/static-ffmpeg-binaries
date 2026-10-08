#!/bin/bash

# Software AV1 decoding is required on CPU-only workers. FFmpeg's native AV1
# hardware wrapper can recognise a stream without being able to decode it.
set -euo pipefail
set -x

if [[ "$RUNNER_OS" == "Linux" ]]; then
  export CFLAGS="-march=x86-64 -mtune=generic -O2"
fi

version=$(repo-src/get-version.sh dav1d)
checksum=$(repo-src/get-version.sh dav1d-sha256)
archive="dav1d-${version}.tar.xz"
curl --fail --location --output "$archive" \
  "https://downloads.videolan.org/pub/videolan/dav1d/${version}/${archive}"
printf '%s  %s\n' "$checksum" "$archive" | shasum -a 256 -c -
tar -xJf "$archive"
cd "dav1d-${version}"

meson setup build \
  --prefix=/usr/local \
  --libdir=lib \
  --buildtype=release \
  --default-library=static \
  -Db_staticpic=true \
  -Denable_tools=false \
  -Denable_tests=false
meson compile -C build -j 2
${SUDO:-} meson install -C build
