#!/bin/bash

set -euo pipefail

ffmpeg_binary="$1"
ffprobe_binary="$2"
fixture_directory=$(cd "$(dirname "$0")" && pwd)
test_directory=$(mktemp -d)
trap 'rm -f "$test_directory/av1.ivf" "$test_directory/frames.md5"; rmdir "$test_directory"' EXIT

# The fixture is two synthetic 32x32 yuv420p frames, not private/user media.
base64 --decode < "$fixture_directory/av1-two-frames.ivf.base64" > "$test_directory/av1.ivf"
printf '%s  %s\n' \
  '32852de65a8c29c3f3c377bc0d14b4f4b2d5ae2622f98b5130eca923c1533775' \
  "$test_directory/av1.ivf" | shasum -a 256 -c -

# Listing the built-in "av1" hardware wrapper alone is not sufficient. Check
# software availability AND default CPU-only decoding, as used by the workers.
"$ffmpeg_binary" -hide_banner -decoders 2>&1 | grep -E 'libdav1d[[:space:]]' > /dev/null
"$ffmpeg_binary" -hide_banner -v error -xerror -hwaccel none -threads 1 \
  -i "$test_directory/av1.ivf" -map 0:v:0 -an \
  -f framemd5 "$test_directory/frames.md5"
[[ $(grep -c '^[0-9]' "$test_directory/frames.md5") == 2 ]]

probe_result=$("$ffprobe_binary" -v error -count_frames -select_streams v:0 \
  -show_entries stream=codec_name,width,height,nb_read_frames \
  -of csv=p=0 "$test_directory/av1.ivf")
[[ "$probe_result" == "av1,32,32,2" ]]
