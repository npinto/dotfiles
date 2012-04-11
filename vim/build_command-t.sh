#!/bin/bash

# build command-t C extension
command -v ruby &> /dev/null && (cd .vim/bundle/command-t/ruby/command-t && ruby extconf.rb && make)

# vim: expandtab tabstop=4 shiftwidth=4 autoindent smartindent tw=80:
