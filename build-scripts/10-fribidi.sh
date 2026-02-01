#!/bin/bash

# Fribidi - Unicode bidirectional text library (dependency of libass)

set -e
set -x

# Set portable compiler flags for Linux to ensure compatibility with Cloud Run.
# NOTE: If you get segfaults, try adding hardened flags for better crash diagnostics:
#   export CFLAGS="-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2"
# This has a 5-15% performance hit but gives clearer error messages.
if [[ "$RUNNER_OS" == "Linux" ]]; then
  export CFLAGS="-march=x86-64 -mtune=generic -O2"
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
