#!/bin/bash

set -e
set -x

TMPDIR=$(mktemp -d)

INFLAC="$1"
OUTMP3="$1".2.mp3
LOG=${TMPDIR}/log.txt

mp3-reconvert-insane.sh "${INFLAC}"
flac-extract-cover.sh "${TMPDIR}" "${INFLAC}"
mp3-add-front-cover.sh "${TMPDIR}/FRONT_COVER.jpg" "${OUTMP3}"

bn=$(echo "${INFLAC}" | sed -e 's/\.flac//g')
mv -vf "${OUTMP3}" "${bn}".mp3 && rm -vf "${INFLAC}"
