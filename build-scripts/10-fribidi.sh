#!/bin/bash

# Fribidi - Unicode bidirectional text library (dependency of libass)

set -e
set -x

# Set hardened/portable compiler flags for Linux (matches Ubuntu package builds)
if [[ "$RUNNER_OS" == "Linux" ]]; then
  export CFLAGS="-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2"
  export CXXFLAGS="$CFLAGS"
fi

FRIBIDI_VERSION="1.0.13"

curl -L "https://github.com/fribidi/fribidi/releases/download/v${FRIBIDI_VERSION}/fribidi-${FRIBIDI_VERSION}.tar.xz" | tar xJ
cd "fribidi-${FRIBIDI_VERSION}"

./configure \
  --enable-static \
  --disable-shared

make
$SUDO make install
