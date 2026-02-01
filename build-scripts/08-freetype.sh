#!/bin/bash

# Freetype - font rendering library (dependency of fontconfig and libass)

set -e
set -x

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
