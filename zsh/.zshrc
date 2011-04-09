
test -f $HOME/.bashrc && source $HOME/.bashrc

# -- Prompt
# different colors for root and users
if [ "`id -u`" -eq 0 ]; then
  export PS1="%{[33;36;1m%}%T%{[0m%} %{[33;34;1m%}%n%{[0m[33;33;1m%}@%{[33;37;1m%}%m %{[33;32;1m%}%~%{[0m[33;33;1m%}
%#%{[0m%} "
else
  export PS1="%{[33;36;1m%}%T%{[0m%} %{[33;31;1m%}%n%{[0m[33;33;1m%}@%{[33;37;1m%}%m %{[33;32;1m%}%~%{[0m[33;33;1m%}
%#%{[0m%} "
fi

# -- Key bindings
# Home
bindkey '^A' beginning-of-line
# End
bindkey '^E' end-of-line
# Del
bindkey '^D' delete-char
bindkey '[3~' delete-char
# Insert
bindkey '[2~' overwrite-mode
# PageUp
bindkey '[5~' history-search-backward
# Page Down
bindkey '[6~' history-search-forward

# -- Console-specific key bindings
if [ "$TERM" = "linux" -o "$TERM" = "screen" -o "$TERM" = "rxvt" ]
then
    # Home
    bindkey '[1~' beginning-of-line
    # End
    bindkey '[4~' end-of-line
fi

# xterm specific key bindings
if [ "$TERM" = "xterm" ]
then
    # Home
    bindkey '[H'  beginning-of-line
    # End
    bindkey '[F'  end-of-line
fi

# -- various zsh options

# no beep, ever
unsetopt beep
unsetopt histbeep
unsetopt listbeep

# don't overwrite when using '>', use '>|' to force
unsetopt clobber

# ^D = 'logout'
unsetopt ignore_eof

setopt print_exit_value

# ask confirmation for 'rm *'
unsetopt rm_star_silent

#setopt auto_remove_slash

# completion on hidden files
setopt glob_dots

# Traite les liens symboliques comme il faut
setopt chase_links

setopt hist_verify

# cd goodies
setopt auto_cd
setopt auto_pushd
setopt pushd_ignore_dups
setopt pushd_silent
setopt pushd_to_home

# bg jobs get niced to '0'
unsetopt bg_nice
# don't send hup when the shell exists
unsetopt hup

# to fix an old bug (line breaking?)
unsetopt PROMPT_CR

# -- Completion
zstyle ':completion:*' matcher-list '' 'm:{a-z}={A-Z}'
zstyle ':completion:*' max-errors 3 numeric
zstyle ':completion:*' use-compctl false

# ########################################
# non zsh-specific options
# ########################################

# -- History
export HISTORY=1000
export SAVEHIST=1000
export HISTFILE=$HOME/.history

# -- ls colors
if [ -x /usr/bin/dircolors ]
then
  if [ -r ~/.dir_colors ]
  then
    eval "`dircolors ~/.dir_colors`"
  elif [ -r /etc/dir_colors ]
  then
    eval "`dircolors /etc/dir_colors`"
  fi
fi

# -- Aliases
#alias cp='cp --interactive'
#alias mv='mv --interactive'
#alias rm='rm --interactive'

alias ll='ls -alF'
alias la='ls -a'
alias lla='ls -la'

alias c='clear'
alias less='less --quiet'
alias s='cd ..'
alias df='df -h'
alias du='du -h'

#alias emacs='vim'
alias vi='vim'
alias iv='vim'
alias sl='ls'


