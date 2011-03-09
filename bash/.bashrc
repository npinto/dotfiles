

export PATH=$HOME/local/bin:$PATH
export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH
export NPROCESSORS=$(cat /proc/cpuinfo | grep processor | wc -l)

export PYTHONVERSION=$(python -c 'import sys; print sys.version[:3]')
export PYTHONPATH_HOME=$HOME/local/lib/python$PYTHONVERSION/site-packages
export PYTHONPATH=${PYTHONPATH_HOME}:$PYTHONPATH
export VIRTUALENV_USE_DISTRIBUTE=1

export EDITOR=vim

# ssh keychain / ssh-agent
if [[ -f ~/.bashrc && -f /usr/bin/keychain ]]; then
keychain ~/.ssh/id_rsa &> /dev/null;
. ~/.keychain/$HOSTNAME-sh;
fi

# aliases
alias ll='ls -halF'
alias l='ls -hlF'
alias la='ls -haF'

alias clean-pyc='find . -name "*pyc" -exec rm -vf {} \;'
alias clean-~='find . -name "*~" -exec rm -vf {} \;'
alias clean='clean-pyc; clean-~';

alias ipy=ipython
