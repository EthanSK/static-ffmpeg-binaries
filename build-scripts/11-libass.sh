#!/bin/bash

# libass - ASS/SSA subtitle renderer (requires freetype, fontconfig, fribidi)

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

LIBASS_VERSION="0.17.1"

curl -L "https://github.com/libass/libass/releases/download/${LIBASS_VERSION}/libass-${LIBASS_VERSION}.tar.xz" | tar xJ
cd "libass-${LIBASS_VERSION}"

./configure \
  --enable-static \
  --disable-shared

make
$SUDO make install
