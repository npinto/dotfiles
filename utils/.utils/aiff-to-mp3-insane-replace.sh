#!/bin/bash

set -e
set -x

infn="$1"
bn=$(echo "${infn}" | sed -e 's/\.aiff//g')

aiff-to-mp3-insane.sh "${infn}" && mv -vf "$bn".aiff.2.mp3 "$bn".mp3 && rm -vf "${bn}".aiff
