#!/bin/bash

# libass - ASS/SSA subtitle renderer (requires freetype, fontconfig, fribidi)

set -e
set -x

LIBASS_VERSION="0.17.1"

curl -L "https://github.com/libass/libass/releases/download/${LIBASS_VERSION}/libass-${LIBASS_VERSION}.tar.xz" | tar xJ
cd "libass-${LIBASS_VERSION}"

./configure \
  --enable-static \
  --disable-shared

make
$SUDO make install
