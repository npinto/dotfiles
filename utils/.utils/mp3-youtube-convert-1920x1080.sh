#!/bin/bash

set -e
set -x

COVER=$1
AUDIO=$2
VIDEO=$3

ffmpeg -loop 1 -r 1 -i "${COVER}" -i "${AUDIO}" -vf scale="'if(gt(a,4/3),1920,-1)':'if(gt(a,4/3),-1,1080)',pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p" -c:v libx264 -c:a aac -b:a 320k -strict -2 -shortest "${VIDEO}"

