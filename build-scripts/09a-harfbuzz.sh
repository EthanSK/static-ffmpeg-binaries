#!/bin/bash

# HarfBuzz - text shaping library (dependency of libass)

set -e
set -x

HARFBUZZ_VERSION="8.3.0"

curl -L "https://github.com/harfbuzz/harfbuzz/releases/download/${HARFBUZZ_VERSION}/harfbuzz-${HARFBUZZ_VERSION}.tar.xz" | tar xJ
cd "harfbuzz-${HARFBUZZ_VERSION}"

# HarfBuzz uses meson, but also supports autotools
# Use a minimal build - we only need the core library for libass
./configure \
  --enable-static \
  --disable-shared \
  --with-freetype=yes \
  --with-glib=no \
  --with-gobject=no \
  --with-cairo=no \
  --with-icu=no

make
$SUDO make install
