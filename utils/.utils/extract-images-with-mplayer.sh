#!/bin/bash

in_fn="$1"
ext=${2:-jpeg}
fps=${3:-30}
out_dir=${4:-"${in_fn}.${ext}_files"}
framerate=$([[ ${fps} -ne 0 ]] && echo "-r ${fps}")

echo "Using ${in_fn}"
echo "Using ${fps} fps: option='${framerate}'"

command -v mplayer

set -e
set -x

test ! -d "${out_dir}"

# the following doesn't work with png
#mplayer "${in_fn}" -vo ${ext}:quality=100:outdir="${out_dir}"
mplayer "${in_fn}" -nosound -benchmark -vo ${ext}:outdir="${out_dir}"
