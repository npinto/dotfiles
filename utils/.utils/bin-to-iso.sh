#!/bin/bash

set -e
set -x

echo "bchunk file.bin file.cue file.iso [-w for wav]"


if [ -z "$4" ]
  then
      bchunk "$1" "$2" "$3"
  else
      bchunk "$4" "$1" "$2" "$3"
fi
