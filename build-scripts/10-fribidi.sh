#!/bin/bash

# Fribidi - Unicode bidirectional text library (dependency of libass)

set -e
set -x

FRIBIDI_VERSION="1.0.13"

curl -L "https://github.com/fribidi/fribidi/releases/download/v${FRIBIDI_VERSION}/fribidi-${FRIBIDI_VERSION}.tar.xz" | tar xJ
cd "fribidi-${FRIBIDI_VERSION}"

./configure \
  --enable-static \
  --disable-shared

make
$SUDO make install
