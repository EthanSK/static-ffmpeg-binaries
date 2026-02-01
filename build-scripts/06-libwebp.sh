#!/bin/bash

# libwebp - WebP image format library

set -e
set -x

LIBWEBP_VERSION="1.4.0"

curl -L "https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-${LIBWEBP_VERSION}.tar.gz" | tar xz
cd "libwebp-${LIBWEBP_VERSION}"

./configure \
  --enable-static \
  --disable-shared \
  --enable-libwebpmux \
  --enable-libwebpdemux

make
$SUDO make install
