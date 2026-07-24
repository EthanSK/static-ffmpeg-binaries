#!/bin/bash

set -e
set -x

cd ffmpeg

./ffmpeg -hide_banner -decoders 2>&1 | grep -Eq 'webp_anim[[:space:]]+Animated WebP image'
./ffmpeg -hide_banner -demuxers 2>&1 | grep -Eq 'webp_anim[[:space:]]+Animated WebP'

test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
test_animation="$test_dir/animated.webp"

./ffmpeg \
  -hide_banner \
  -loglevel error \
  -f lavfi \
  -i testsrc2=size=32x32:rate=2:duration=1 \
  -frames:v 2 \
  -c:v libwebp_anim \
  -loop 0 \
  "$test_animation"

probe_result=$(./ffprobe \
  -v error \
  -count_frames \
  -select_streams v:0 \
  -show_entries stream=codec_name,nb_read_frames \
  -of csv=p=0 \
  "$test_animation")

[[ "$probe_result" == "webp_anim,2" ]] # The build must decode every animation frame, not merely recognise the WebP container or return its first frame.
