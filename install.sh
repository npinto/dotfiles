#!/bin/bash

set -e
set -x

if [ $(command -v keychain) ]; then
    for f in ~/.ssh/id_?sa; do
        keychain $f &> /dev/null;
    done;
    . ~/.keychain/$(hostname)-sh;
fi

./git-pup

for d in `ls -d */`; do
    pushd $d
    test -f ./install.sh && ./install.sh;
    popd;
done;

set +e
set +x
