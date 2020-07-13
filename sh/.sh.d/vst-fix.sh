#!/bin/bash

set -e
set -x

sudo xattr -cr "$1"
sudo codesign -f -s - "$1"
