#!/bin/bash

set -e
set -x

TMPDIR=$(mktemp -d)
WAV="${TMPDIR}/$(basename "$1")".wav
OUT="$1".2.mp3

ffmpeg -i "$1" "${WAV}"
lame --preset insane "${@:2}" "${WAV}" "${OUT}"

rm -rvf ${TMPDIR}
