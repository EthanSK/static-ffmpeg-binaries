#!/bin/bash

# A diagnostic, not a universal memory certificate or a production tier change.
set -euo pipefail

binary_directory=$(cd "$1" && pwd)
fixture_directory=$(cd "$(dirname "$0")" && pwd)
diagnostic_directory="$PWD/diagnostics"
mkdir -p "$diagnostic_directory"
base64 --decode < "$fixture_directory/square-10bit-16refs.mp4.base64" > "$diagnostic_directory/source.mp4"
printf '%s  %s\n' \
  '42c86eae71c9c9c921ecf21fb005aaedca588c908abc799b382580dfcb030158' \
  "$diagnostic_directory/source.mp4" | sha256sum -c -
sha256sum "$binary_directory/ffmpeg-linux-x64" "$binary_directory/ffprobe-linux-x64" > "$diagnostic_directory/binary-sha256.txt"
uname -a > "$diagnostic_directory/host.txt"

# Native Linux runner only. Keep the same 8 GiB / 2 CPU contract as the earlier
# emulated test, without sharing the user's local Docker host or dev stacks.
container_id=$(docker create --memory=8g --memory-swap=8g --cpus=2 \
  --read-only --network=none --pids-limit=128 \
  --tmpfs /output:rw,size=16m \
  --mount "type=bind,src=$binary_directory/ffmpeg-linux-x64,dst=/ffmpeg,readonly" \
  --mount "type=bind,src=$binary_directory/ffprobe-linux-x64,dst=/ffprobe,readonly" \
  --mount "type=bind,src=$diagnostic_directory/source.mp4,dst=/source.mp4,readonly" \
  ffmpeg-capacity-base sh -c '
    /ffmpeg -hide_banner -nostdin -benchmark -threads 1 -filter_threads 1 \
      -max_pixels 16777216 -i /source.mp4 -map 0:v:0 -an \
      -vf "scale=4096:4096:force_original_aspect_ratio=decrease,pad=4096:4096:(ow-iw)/2:(oh-ih)/2,setsar=1" \
      -c:v libx264 -threads 2 -preset veryfast -crf 21 -pix_fmt yuv420p \
      -movflags +faststart /output/result.mp4
    encode_status=$?
    printf "encode_exit=%s\n" "$encode_status"
    printf "cgroup_peak_bytes="
    cat /sys/fs/cgroup/memory.peak || true
    cat /sys/fs/cgroup/memory.events || true
    if [ "$encode_status" -eq 0 ]; then
      /ffprobe -v error -count_frames -select_streams v:0 \
        -show_entries stream=codec_name,width,height,pix_fmt,nb_read_frames \
        -of csv=p=0 /output/result.mp4 || exit $?
    fi
    exit "$encode_status"
  ')
trap 'docker rm -f "$container_id" >/dev/null 2>&1 || true' EXIT
set +e
docker start --attach "$container_id" 2>&1 | tee "$diagnostic_directory/conversion.log"
attach_status=${PIPESTATUS[0]}
set -e
docker inspect --format '{{json .State}}' "$container_id" > "$diagnostic_directory/container-state.json"
if [[ "$attach_status" -ne 0 ]]; then
  exit "$attach_status"
fi
grep -q '^h264,4096,4096,yuv420p,36$' "$diagnostic_directory/conversion.log"
