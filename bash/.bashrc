

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

# ls colors
command -v dircolors &> /dev/null && eval "$(dircolors -b)"

# aliases
alias ll='ls -halF'
alias l='ls -hlF'
alias la='ls -haF'

alias clean-pyc='find . -name "*pyc" -exec rm -vf {} \;'
alias clean-~='find . -name "*~" -exec rm -vf {} \;'
alias clean='clean-pyc; clean-~';

alias ipy=ipython

alias tmux='tmux -2';

alias current='cd ~/goto/current'

# fix nose/virtualenv bug, see:
# http://stackoverflow.com/questions/864956/problems-using-nose-in-a-virtualenv
alias nosetests-hack='python `which nosetests`'
