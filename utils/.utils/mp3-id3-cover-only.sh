#!/bin/bash

set -e
set -x

TMPDIR=$(mktemp -d)
TMPWAV=${TMPDIR}/$(basename "$1").wav
OUTMP3="$1".PBQA_WO.mp3
LOG=${TMPDIR}/log.txt

eyeD3 --no-color --write-images=${TMPDIR} "$1" | tee ${LOG}
grep Writing ${LOG}
ffmpeg -i "$1" "${TMPWAV}"
lame --preset insane "${TMPWAV}" "${OUTMP3}"
#FRONT_COVER=$(ls "${TMPDIR}"/FRONT_COVER*)
FRONT_COVER=$(grep Writing ${LOG} | cut -d' ' -f2 | sed 's/\.\.\.$//g' | head -n1)
eyeD3 --add-image "${FRONT_COVER}:FRONT_COVER" "${OUTMP3}"

rm -rvf ${TMPDIR}
