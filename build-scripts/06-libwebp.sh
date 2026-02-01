#!/bin/bash

# libwebp - WebP image format library

set -e
set -x

# Set hardened/portable compiler flags for Linux (matches Ubuntu package builds)
if [[ "$RUNNER_OS" == "Linux" ]]; then
  export CFLAGS="-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2"
  export CXXFLAGS="$CFLAGS"
fi

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
