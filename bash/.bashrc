
# -----------------------------------------------------------------------------
# -- bash prompt
# -----------------------------------------------------------------------------
#export PS1='\h:\W \u\$'
if [ "$0" = "-zsh" ]; then
    if [ "`id -u`" -eq 0 ]; then
      export PS1="%{[33;36;1m%}%T%{[0m%} %{[33;34;1m%}%n%{[0m[33;33;1m%}@%{[33;37;1m%}%m %{[33;32;1m%}%~%{[0m[33;33;1m%}
    %#%{[0m%} "
    else
      export PS1="%{[33;36;1m%}%T%{[0m%} %{[33;31;1m%}%n%{[0m[33;33;1m%}@%{[33;37;1m%}%m %{[33;32;1m%}%~%{[0m[33;33;1m%}
    %#%{[0m%} "
    fi
else
    export PS1='\[\033[01;32m\]\u@\h\[\033[01;34m\] \w \$\[\033[00m\] '
fi


# -----------------------------------------------------------------------------
# -- default editor
# -----------------------------------------------------------------------------
export EDITOR=vim

# -----------------------------------------------------------------------------
# -- local path
# -----------------------------------------------------------------------------
test -d $HOME/local/bin && export PATH=$HOME/local/bin:$PATH
test -d $HOME/local/lib && export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH

# -----------------------------------------------------------------------------
# -- processors
# -----------------------------------------------------------------------------
if [[ -f /proc/cpuinfo ]]; then
    export NPROCESSORS=$(cat /proc/cpuinfo | grep processor | wc -l)
else
    export NPROCESSORS=1
fi

# MKL
export MKL_NUM_THREADS=$NPROCESSORS

# -----------------------------------------------------------------------------
# -- python related
# -----------------------------------------------------------------------------
export PYTHONVERSION=$(python -c 'import sys; print sys.version[:3]')
export PYTHONPATH_HOME=$HOME/local/lib/python$PYTHONVERSION/site-packages:$HOME/local/lib64/python$PYTHONVERSION/site-packages
export PYTHONPATH=${PYTHONPATH_HOME}:$PYTHONPATH

export VIRTUALENV_USE_DISTRIBUTE=1

# -----------------------------------------------------------------------------
# -- CUDA related
# -----------------------------------------------------------------------------
test -d /usr/local/cuda/bin && export PATH=$PATH:/usr/local/cuda/bin
test -d /usr/local/cuda/lib && export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib
test -d /usr/local/cuda/lib64 && export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64

# -----------------------------------------------------------------------------
# -- ssh keychain / ssh-agent
# -----------------------------------------------------------------------------
if [ "$(command -v keychain && test -f ~/.bashrc)" ]; then
    keychain ~/.ssh/id_rsa &> /dev/null;
    . ~/.keychain/$HOSTNAME-sh;
fi

# -- ls colors
command -v dircolors &> /dev/null && eval "$(dircolors -b)"

# -----------------------------------------------------------------------------
# -- aliases
# -----------------------------------------------------------------------------
alias ll='ls -halF'
alias l='ls -hlF'
alias la='ls -haF'

alias grep='grep --colour=auto'

alias clean-pyc='find . -name "*pyc" -exec rm -vf {} \;'
alias clean-coverage='find . -name ".coverage" -exec rm -vf {} \;'
alias clean-~='find . -name "*~" -exec rm -vf {} \;'
alias clean='clean-pyc; clean-coverage; clean-~'

alias py=python
alias ipy=ipython

alias tmux='tmux -2'

alias current='cd ~/goto/current'

# fix nose/virtualenv bug, see:
# http://stackoverflow.com/questions/864956/problems-using-nose-in-a-virtualenv
alias nosetests-hack='python `which nosetests`'

alias pudb='python -m pudb.run'

# MacVim
test -x "/Applications/MacVim.app/Contents/MacOS/Vim" && alias vim=/Applications/MacVim.app/Contents/MacOS/Vim

# -----------------------------------------------------------------------------
# -- LD_LIBRARY_PATH Final Updates
# -----------------------------------------------------------------------------
# remove useless semicolons from LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$(echo $LD_LIBRARY_PATH | sed -e 's/:*$//g' -e 's/^:*//g')

# -----------------------------------------------------------------------------
# -- MacOSX specific
# -----------------------------------------------------------------------------
export DYLD_LIBRARY_PATH=$LD_LIBRARY_PATH

# MacPorts
test -d /opt/local/bin && export PATH=/opt/local/bin:$PATH
test -d /opt/local/sbin && export PATH=/opt/local/sbin:$PATH

# Fink
test -r /sw/bin/init.sh && . /sw/bin/init.sh

# MacOSX's Python
PYTHON_MACOSX=/Library/Frameworks/Python.framework/Versions/Current/bin
test -d $PYTHON_MACOSX && export PATH=$PYTHON_MACOSX:$PATH

# emacs with small font on MacOSX
function am
 {
    # Create the files as needed -- not as good as raw emacs, but acceptable
    for f in "$@"
    do
    test -e $f || touch $f
    done
    open -a /Applications/Aquamacs.app "$@"
 }
alias em="emacs -fn -apple-courier-medium-r-normal--10-100-72-72-m-100-mac-roman"

# -----------------------------------------------------------------------------
# -- Local Profile
# -----------------------------------------------------------------------------
test -f $HOME/local/.profile && source $HOME/local/.profile

