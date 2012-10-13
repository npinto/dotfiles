#!/bin/bash

set -e
set -x

if [ ! "$#" -eq 4 ]; then
    echo "Usage: $0 RSYNC_OPTIONS INCLUDE_ONLY SRC DST"
    return 1
fi

# -- parse args
RSYNC_OPTIONS=$1
INCLUDE_ONLY=$2
SRC=$3
DST=$4

# -- construct command
CMD="rsync ${RSYNC_OPTIONS}"
CMD="${CMD} --include \"*/\" --include \"${INCLUDE_ONLY}\""
CMD="${CMD} --exclude=\"*\" "
CMD="${CMD} \"${SRC}\" \"${DST}\""
echo ${CMD}

# -- execute command
eval ${CMD}
