#!/bin/bash

if [ ! "$#" -eq 2 ]; then
    echo "Usage: $(basename $0) <hashfunction> <filename>";
    echo;
    echo "Supported <hashfunction>: 'sha1' or 'md5'";
    echo;
    exit 1;
fi
echo $2.$1;
(cd $(dirname $2); ${1}sum $(basename $2) > $(basename $2).$1);
