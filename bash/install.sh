#!/bin/bash

backup_dir=backup-$(date +"%Y-%m-%d_%Hh%Mm%Ss")

for f in .bashrc .bash_profile; do
    echo $f;
    if [[ -f ~/$f ]]; then
        mkdir -p $backup_dir;
        mv -vf ~/$f $backup_dir;
    fi;
    ln -sf $(pwd)/$f ~/;
done;

# vim: expandtab tabstop=4 shiftwidth=4 autoindent smartindent tw=80:
