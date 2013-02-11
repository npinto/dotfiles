#!/bin/sh

# diffo.sh
#
# Written by Gary S. Weaver
# from http://stufftohelpyouout.blogspot.com/2009/12/find-and-diff-only-certain-files-in-one.html?m=1

set -e

d1="$1"
d2="$2"
exp="$3"

if [ $# -ne 3 ]; then
  echo
  echo "usage: diffonly.sh dir1 dir2 expression"
  echo
  exit 1
fi

# canonicalize and set as variables
d1c=`cd -P -- "$(dirname -- "$d1")" && printf '%s\n' "$(pwd -P)/$(basename -- "$d1")"`
d2c=`cd -P -- "$(dirname -- "$d2")" && printf '%s\n' "$(pwd -P)/$(basename -- "$d2")"`

set -x verbose
cd "${d1}"
find . -name "${exp}" -exec echo "Comparing \"${d1c}/{}\" to \"${d2c}/{}\" ..." \; -exec diff "{}" "${d2c}/{}" \;
