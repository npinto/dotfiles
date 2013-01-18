#!/bin/bash


in_fn="$1"
in_ext="${1##*.}"
trans=${2:-0}
out_fn=${4:-"${in_fn}.transpose=${trans}.${in_ext}"}

set -e
set -x

ffmpeg -i "${in_fn}" -vf transpose=${trans} -an -q:v 1 "${out_fn}"
