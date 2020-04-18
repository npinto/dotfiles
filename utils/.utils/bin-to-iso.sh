#!/bin/bash

set -e
set -x

echo "bchunk file.bin file.cue file.iso [-w for wav]"

bchunk "$4" "$1" "$2" "$3"
