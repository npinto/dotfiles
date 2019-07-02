#!/bin/bash

set -e
set -x

outfn=$1
infn=$2

metaflac --export-picture-to=${outfn} ${infn}
