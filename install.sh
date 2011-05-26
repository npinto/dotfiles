#!/bin/bash

for d in `ls -d */`; do
    (cd $d; test -f ./install.sh && ./install.sh) ;
done;


