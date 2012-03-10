#!/bin/bash

backup_dir=backup-$(date +"%Y-%m-%d_%Hh%Mm%Ss")

set -x
set -e

srcdn=$HOME/Dropbox/config/ssh
dstdn=$HOME/.ssh
for srcfn in $srcdn/{config,.sh.d}; do
    echo $srcfn;
    srcbn=$(basename $srcfn);
    dstfn=$dstdn/$srcbn
    if [[ -f $srcbn ]]; then
        if [[ -e $dstfn ]]; then
            mkdir -p $backup_dir;
            mv $dstfn $backup_dir;
        fi;
        ln -sf $srcfn $dstfn;
    fi;
done;

# vim: expandtab tabstop=4 shiftwidth=4 autoindent smartindent tw=80:
