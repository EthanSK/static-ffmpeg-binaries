#!/bin/bash
set -euo pipefail

check_args=(ffmpeg/ffmpeg ffmpeg/ffprobe --work-dir seek-tests.noindex
            --report qualification.noindex/seek-stream.json)
if [[ "${QUALIFY:-false}" == true ]]; then
  check_args+=(--unpatched "$PWD/ffmpeg-control/ffmpeg")
fi
python3 repo-src/tests/check-seek-stream.py "${check_args[@]}"

cd ffmpeg
cases=(specifier index fractional offset sseof default invalid unmatched ambiguous)
targets=()
for name in "${cases[@]}"; do targets+=("fate-ffmpeg-seek-stream-$name"); done
mkdir -p ../qualification.noindex
make -j2 "${targets[@]}" 2>&1 | tee ../qualification.noindex/seek-fate.log
[[ $(grep -c '^TEST[[:space:]].*ffmpeg-seek-stream-' ../qualification.noindex/seek-fate.log) == 9 ]]
