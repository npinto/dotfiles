#!/bin/bash

# big endian
ffmpeg -f s16be -ar 44.1k -ac 2 -i %1 %2
