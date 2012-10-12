#!/bin/bash

in_fn="$1"

staty=$(stat -c %y "${in_fn}" | sed -e 's/\..*$//')

date=$(echo "${staty}" | awk '{print $1}')
hours=$(echo ${staty} | sed 's/:/ /g' | awk '{print $2}')
minutes=$(echo ${staty} | sed 's/:/ /g' | awk '{print $3}')
seconds=$(echo ${staty} | sed 's/:/ /g' | awk '{print $4}')

sha1=$(sha1sum "${in_fn}" | cut -d' ' -f1)
ext="${in_fn##*.}"

out_fn="${date}_${hours}h${minutes}m${seconds}s.${sha1}.${ext}"
echo "${out_fn}"
