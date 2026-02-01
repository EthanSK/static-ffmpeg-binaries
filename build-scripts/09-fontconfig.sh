#!/bin/bash

# Fontconfig - font configuration library (dependency of libass)

set -e
set -x

# Set hardened/portable compiler flags for Linux (matches Ubuntu package builds)
if [[ "$RUNNER_OS" == "Linux" ]]; then
  export CFLAGS="-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2"
  export CXXFLAGS="$CFLAGS"
fi

FONTCONFIG_VERSION="2.14.2"

curl -L "https://www.freedesktop.org/software/fontconfig/release/fontconfig-${FONTCONFIG_VERSION}.tar.xz" | tar xJ
cd "fontconfig-${FONTCONFIG_VERSION}"

./configure \
  --enable-static \
  --disable-shared \
  --disable-docs

make
$SUDO make install
