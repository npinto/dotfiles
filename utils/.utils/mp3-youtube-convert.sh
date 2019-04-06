#!/bin/bash

set -e
set -x

COVER=$1
AUDIO=$2
VIDEO=$3

ffmpeg -loop 1 -r 1 -i "${COVER}" -i "${AUDIO}" -c:a copy -shortest "${VIDEO}"

