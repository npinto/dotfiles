#!/bin/bash

for f in *zip; do d=${f%.*}; echo $d; mkdir -p "$d"; mv -vf "$f" "$d"; (cd "$d"; x "$f" && rm -vf "$f"); done;
