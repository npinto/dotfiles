#!/bin/bash

set -e
set -x

cd ${HOME}/dotfiles
git pull
./install.sh
