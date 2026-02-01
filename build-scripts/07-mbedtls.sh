#!/bin/bash

# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e
set -x

tag=$(repo-src/get-version.sh mbedtls)
git clone --depth 1 https://github.com/ARMmbed/mbedtls.git -b "$tag"

cd mbedtls

# Remove some compiler flags that cause build failures on macOS arm64.  This
# can't be done through CMake variables, so we have to patch the source.
sed -e 's/-Wdocumentation//' -e 's/-Wno-documentation-deprecated-sync//' \
  -i.bk library/CMakeLists.txt

# Set portable compiler flags for Linux to ensure compatibility with Cloud Run.
# NOTE: If you get segfaults, try adding hardened flags for better crash diagnostics:
#   CMAKE_EXTRA_FLAGS="-DCMAKE_C_FLAGS=-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2"
# This has a 5-15% performance hit but gives clearer error messages.
CMAKE_EXTRA_FLAGS=""
if [[ "$RUNNER_OS" == "Linux" ]]; then
  CMAKE_EXTRA_FLAGS="-DCMAKE_C_FLAGS=-march=x86-64 -mtune=generic -O2"
fi

# NOTE: without CMAKE_INSTALL_PREFIX on Windows, files are installed
# to c:\Program Files.
cmake . \
  -DCMAKE_INSTALL_PREFIX=/usr/local \
  -DENABLE_PROGRAMS=OFF \
  -DUNSAFE_BUILD=OFF \
  -DGEN_FILES=OFF \
  -DENABLE_TESTING=OFF \
  $CMAKE_EXTRA_FLAGS

make
$SUDO make install
