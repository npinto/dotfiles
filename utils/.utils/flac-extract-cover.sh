#!/bin/bash

set -e
set -x

OUTDIR="$1"
INFLAC="$2"

metaflac "${INFLAC}" --export-picture-to="${OUTDIR}/FRONT_COVER.jpg"
ls "${OUTDIR}/FRONT_COVER.jpg"
