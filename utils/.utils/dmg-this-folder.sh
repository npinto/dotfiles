#!/bin/bash

set -e
set -x

VOLUME_NAME=$1
SRC_FOLDER=$2
DMG_FILENAME=$3

hdiutil create -volname "$VOLUME_NAME" -srcfolder "$SRC_FOLDER" -ov -format UDZO "$DMG_FILENAME"
