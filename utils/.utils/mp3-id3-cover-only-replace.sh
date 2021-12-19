#!/bin/bash

set -e
set -x

infn="$1"
bn=$(echo "${infn}" | sed -e 's/\.mp3//g')

mp3-id3-cover-only.sh "${infn}" && mv -vf "$bn".mp3.PBQA_WO.mp3 "$bn".mp3 
