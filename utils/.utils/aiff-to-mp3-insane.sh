#!/bin/bash

set -e
set -x

TMPDIR=$(mktemp -d)

INAIFF="$1"
OUTMP3="$1".2.mp3
LOG=${TMPDIR}/log.txt

mp3-reconvert-insane.sh "${INAIFF}"
aiff-extract-cover.sh "${TMPDIR}" "${INAIFF}"
mp3-add-front-cover.sh "${TMPDIR}/FRONT_COVER.jpg" "${OUTMP3}"
