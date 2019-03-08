#!/bin/bash

set -e
set -x

m=$1
echo -e "\nFound $m"
dd=`hdiutil attach "$m" | cut -f3`
echo -e "\nFound ${m%%.*} - $dd"
cp -a "$dd"/ .
if [ $? -ne 0 ]; then
    exit 10
else
    hdiutil detach "$dd"
fi
