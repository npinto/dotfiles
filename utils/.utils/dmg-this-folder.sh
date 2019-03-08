#!/bin/bash


set -e
set -x

hdiutil create -volname "$1" -srcfolder "$2" -ov -format UDZO "$3"
