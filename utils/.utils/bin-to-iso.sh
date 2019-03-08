#!/bin/bash

set -e
set -x

echo bchunk file.bin file.cue file.iso

bchunk "$1" "$2" "$3"
