#!/bin/bash

set -e
set -x

ext="${1##*.}"
outfn=${2-${1}.noaudio.${ext}}

ffmpeg -i "$1" -vcodec copy -an "$outfn"
