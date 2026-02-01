#!/bin/bash

# Fontconfig - font configuration library (dependency of libass)

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

FONTCONFIG_VERSION="2.14.2"

curl -L "https://www.freedesktop.org/software/fontconfig/release/fontconfig-${FONTCONFIG_VERSION}.tar.xz" | tar xJ
cd "fontconfig-${FONTCONFIG_VERSION}"

./configure \
  --enable-static \
  --disable-shared \
  --disable-docs

make
$SUDO make install
