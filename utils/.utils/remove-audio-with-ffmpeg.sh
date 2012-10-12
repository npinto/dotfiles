#!/bin/bash

set -e
set -x

ffmpeg -i "$1" -vcodec copy -an "$2"
