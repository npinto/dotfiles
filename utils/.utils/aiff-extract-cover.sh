#!/bin/bash

set -e
set -x

OUTDIR="$1"
INAIFF="$2"

kid3-cli -c 'select "'"$INAIFF"'"' -c 'get picture:"'"${OUTDIR}"'/FRONT_COVER.jpg"'
ls "${OUTDIR}/FRONT_COVER.jpg"
