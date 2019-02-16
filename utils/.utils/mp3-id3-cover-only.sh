#!/bin/bash

set -e
set -x

TMPDIR=$(mktemp -d)
TMPWAV=${TMPDIR}/$(basename "$1").wav
OUTMP3="$1".PBQA_WO.mp3

eyeD3 --write-images=${TMPDIR} "$1"
ffmpeg -i "$1" "${TMPWAV}"
lame --preset insane "${TMPWAV}" "${OUTMP3}"
FRONT_COVER=$(ls "${TMPDIR}"/FRONT_COVER*)
 eyeD3 --add-image "${FRONT_COVER}:FRONT_COVER" "${OUTMP3}"

