#!/bin/bash

set -e
set -x

#spleeter separate -p spleeter:5stems-16kHz -o spleeter -i "$1"
spleeter separate -p spleeter:5stems-16kHz -o spleeter "$1"
