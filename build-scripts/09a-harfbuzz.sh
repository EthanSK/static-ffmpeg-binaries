#!/bin/bash

# HarfBuzz - text shaping library (dependency of libass)

set -e
set -x

# Set portable compiler flags for Linux to ensure compatibility with Cloud Run.
# NOTE: If you get segfaults, try adding hardened flags for better crash diagnostics:
#   export CFLAGS="-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2"
# This has a 5-15% performance hit but gives clearer error messages.
if [[ "$RUNNER_OS" == "Linux" ]]; then
  export CFLAGS="-march=x86-64 -mtune=generic -O2"
  export CXXFLAGS="$CFLAGS"
fi

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
