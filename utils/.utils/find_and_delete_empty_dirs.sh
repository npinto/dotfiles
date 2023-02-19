#!/bin/bash

set -e
set -x

find $1 -type d -empty -print -delete
