#!/usr/bin/env bash
# convert_audio_to_mp4.sh
# Usage: ./convert_audio_to_mp4.sh input_audio.mp3 output_video.mp4

set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $(basename "$0") <input_audio> <output_video.mp4>" >&2
  exit 1
fi

INPUT="$1"
OUTPUT="$2"

ffmpeg -y \
  -f lavfi -i color=c=black:s=1280x720:r=30 \
  -i "$INPUT" \
  -c:v libx264 -pix_fmt yuv420p \
  -c:a copy -shortest \
  "$OUTPUT"

