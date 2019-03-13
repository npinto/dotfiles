#!/bin/bash

set -e
set -x

m=$1
echo -e "\nFound $m"
dd=`hdiutil attach "$m" | grep Volumes | cut -f3`
echo -e "\nFound ${m%.iso} - $dd"
#cp -a "$dd"/ .
cp -a "$dd"/ ./"${m%.iso}"/
if [ $? -ne 0 ]; then
    exit 10
else
    hdiutil detach "$dd"
fi
