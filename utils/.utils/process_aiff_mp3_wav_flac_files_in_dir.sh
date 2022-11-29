#!/bin/bash

for f in *.mp3; do mp3-id3-cover-only-replace.sh "$f"; done;
for f in *.aiff; do aiff-to-mp3-insane-replace.sh "$f"; done;
for f in *.wav; do wav-to-mp3-insane-replace.sh "$f"; done;
for f in *.flac; do flac-to-mp3-insane-replace.sh "$f"; done;
