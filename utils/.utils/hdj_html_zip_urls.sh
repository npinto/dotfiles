#!/bin/bash

cat *.html | grep zip | cut -d'=' -f3 | cut -d' ' -f1 | sed -e 's/"//g'
