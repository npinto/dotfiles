#!/bin/bash
set -e
set -x

outdn="$1"
infn="$2"

eyeD3 --write-images="${outdn}" "${infn}"
