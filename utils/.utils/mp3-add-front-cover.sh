#!/bin/bash

frontcover="$1"
mp3file="$2"

eyeD3 --add-image "${frontcover}:FRONT_COVER" "${mp3file}"
