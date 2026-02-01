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

tag=$(repo-src/get-version.sh x264)
git clone https://code.videolan.org/videolan/x264.git
cd x264
git checkout "$tag"

# NOTE: disable OpenCL-based features because it uses dlopen and can interfere
# with static builds.
#
# IMPORTANT: We use -march=x86-64 -mtune=generic to fix segfaults on Cloud Run.
# Without these flags, the compiler may optimize for the GitHub Actions runner's CPU
# (effectively -march=native), generating instructions that don't work on Cloud Run's
# virtualized CPUs. This caused SIGSEGV crashes during libx264 encoding.
#
# The fix: compile C code for generic x86-64, while keeping ASM enabled.
# Runtime CPU detection in x264 will still use SSE/AVX/AVX2 optimizations
# based on what the actual CPU supports - so encoding stays fast.
#
# NOTE: If you get segfaults, try adding hardened flags for better crash diagnostics:
#   EXTRA_CFLAGS="-march=x86-64 -mtune=generic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2"
# This has a 5-15% performance hit but gives clearer error messages.
EXTRA_CFLAGS=""
if [[ "$RUNNER_OS" == "Linux" ]]; then
  EXTRA_CFLAGS="-march=x86-64 -mtune=generic -O2"
fi

./configure \
  --disable-opencl \
  --enable-static \
  --enable-pic \
  ${EXTRA_CFLAGS:+--extra-cflags="$EXTRA_CFLAGS"}

# Only build and install the static library.
make libx264.a
$SUDO make install-lib-static
