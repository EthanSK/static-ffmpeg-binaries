#!/bin/bash

# Freetype - font rendering library (dependency of fontconfig and libass)

set -e
set -x

# Set hardened/portable compiler flags for Linux (matches Ubuntu package builds)
if [[ "$RUNNER_OS" == "Linux" ]]; then
  export CFLAGS="-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2"
  export CXXFLAGS="$CFLAGS"
fi

FREETYPE_VERSION="2.13.2"

curl -L "https://download.savannah.gnu.org/releases/freetype/freetype-${FREETYPE_VERSION}.tar.xz" | tar xJ
cd "freetype-${FREETYPE_VERSION}"

./configure \
  --enable-static \
  --disable-shared \
  --with-png=no \
  --with-harfbuzz=no \
  --with-bzip2=no \
  --with-brotli=no

make
$SUDO make install
