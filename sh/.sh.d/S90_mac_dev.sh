#!/bin/bash

if [[ "`uname`" == "Darwin" ]]; then
    if [[ "`uname -r`" == "10.8.0" ]]; then
        export MACOSX_DEPLOYMENT_TARGET=10.6;
        export ARCHFLAGS="-arch i386 -arch x86_64";
    fi;
    if [[ "`uname -r`" == "12.1.0" ]]; then
        export MACOSX_DEPLOYMENT_TARGET=10.8;
        export ARCHFLAGS="-arch i386 -arch x86_64";
    fi;
fi;

