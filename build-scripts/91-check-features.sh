#!/bin/bash

set -e
set -o pipefail
set -x

cd ffmpeg

bash ../repo-src/tests/check-av1.sh ./ffmpeg ./ffprobe

./ffmpeg -hide_banner -decoders 2>&1 | grep -E 'gif[[:space:]]+GIF \(Graphics Interchange Format\)' > /dev/null
./ffmpeg -hide_banner -decoders 2>&1 | grep -E 'webp_anim[[:space:]]+Animated WebP image' > /dev/null
./ffmpeg -hide_banner -demuxers 2>&1 | grep -E 'gif_pipe[[:space:]]+piped gif sequence' > /dev/null
./ffmpeg -hide_banner -demuxers 2>&1 | grep -E 'webp_anim[[:space:]]+Animated WebP' > /dev/null
./ffmpeg -hide_banner -demuxers 2>&1 | grep -E 'webp_pipe[[:space:]]+piped webp sequence' > /dev/null

test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
gif_animation="$test_dir/animated.gif"
webp_animation="$test_dir/animated.webp"

./ffmpeg \
  -hide_banner \
  -loglevel error \
  -f lavfi \
  -i testsrc2=size=32x32:rate=2:duration=1 \
  -frames:v 2 \
  -c:v gif \
  -loop 0 \
  "$gif_animation"

./ffmpeg \
  -hide_banner \
  -loglevel error \
  -f lavfi \
  -i testsrc2=size=32x32:rate=2:duration=1 \
  -frames:v 2 \
  -c:v libwebp_anim \
  -loop 0 \
  "$webp_animation"

verify_animation() {
  local test_animation="$1"
  local expected_codec="$2"
  local probe_result
  local streamed_frames

  probe_result=$(./ffprobe \
    -v error \
    -count_frames \
    -select_streams v:0 \
    -show_entries stream=codec_name,nb_read_frames \
    -of csv=p=0 \
    "$test_animation")

  [[ "$probe_result" == "$expected_codec,2" ]]

  streamed_frames=$(./ffmpeg \
    -hide_banner \
    -loglevel error \
    -i pipe:0 \
    -map 0:v:0 \
    -f framemd5 \
    pipe:1 \
    < "$test_animation" | grep -c '^[0-9]')

  [[ "$streamed_frames" == "2" ]]
}

# The build must decode every animation frame from both a seekable file and a
# non-seekable stdin stream, not merely recognise the container or return its
# first frame.
verify_animation "$gif_animation" gif
verify_animation "$webp_animation" webp_anim
