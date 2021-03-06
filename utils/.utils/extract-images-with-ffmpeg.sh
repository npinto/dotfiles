#!/bin/bash

in_fn="$1"
ext=${2:-jpg}
fps=${3:-30}
out_dir=${4:-"${in_fn}.${ext}_files"}
framerate=$([[ ${fps} -ne 0 ]] && echo "-r ${fps}")

echo "Using ${in_fn}"
echo "Using ${fps} fps: option='${framerate}'"

set -e
set -x

test ! -d "${out_dir}"

mkdir -p "${out_dir}"
ffmpeg -i "${in_fn}" -an -f image2 -q:v 1 ${framerate} -vsync 0 "${out_dir}/%09d.${ext}"
# -vsync 0 will not dump dupes
