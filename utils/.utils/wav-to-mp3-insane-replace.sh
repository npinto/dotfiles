#!/bin/bash

set -e
set -x

infn="$1"
bn=$(echo "${infn}" | sed -e 's/\.wav//g')

lame --preset insane "${infn}" && rm -vf "${infn}"
