#!/bin/bash

for d in awesome/ bash/ git/ ipython/ screen/ terminator/ tmux/ vim/; do
    (cd $d; ./install.sh) ;
done;


