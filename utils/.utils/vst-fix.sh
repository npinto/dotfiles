#!/bin/bash

set -e
set -x

sudo /usr/bin/xattr -cr "$1"
sudo codesign -f -s - "$1"
