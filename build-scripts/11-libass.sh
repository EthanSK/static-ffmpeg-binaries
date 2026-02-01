#!/bin/bash

# libass - ASS/SSA subtitle renderer (requires freetype, fontconfig, fribidi)

set -e
set -x

# Set hardened/portable compiler flags for Linux (matches Ubuntu package builds)
if [[ "$RUNNER_OS" == "Linux" ]]; then
  export CFLAGS="-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2"
  export CXXFLAGS="$CFLAGS"
fi

LIBASS_VERSION="0.17.1"

curl -L "https://github.com/libass/libass/releases/download/${LIBASS_VERSION}/libass-${LIBASS_VERSION}.tar.xz" | tar xJ
cd "libass-${LIBASS_VERSION}"

./configure \
  --enable-static \
  --disable-shared

make
$SUDO make install
