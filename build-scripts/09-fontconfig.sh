#!/bin/bash

# Fontconfig - font configuration library (dependency of libass)

set -e
set -x

FONTCONFIG_VERSION="2.14.2"

curl -L "https://www.freedesktop.org/software/fontconfig/release/fontconfig-${FONTCONFIG_VERSION}.tar.xz" | tar xJ
cd "fontconfig-${FONTCONFIG_VERSION}"

./configure \
  --enable-static \
  --disable-shared \
  --disable-docs

make
$SUDO make install
