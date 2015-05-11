#!/bin/bash

backup_dir=backup-$(date +"%Y-%m-%d_%Hh%Mm%Ss")

function verbose {
    echo $*
    $*
}

for f in .ipython; do
    echo $f;
    if [[ -e ~/$f ]]; then
        verbose mkdir -p $backup_dir;
        verbose mv ~/$f $backup_dir;
    fi;
    verbose mkdir -p $(dirname ~/$f);
    verbose ln -sf $(pwd)/$f ~/$f;
done;

# vim: expandtab tabstop=4 shiftwidth=4 autoindent smartindent tw=80:
