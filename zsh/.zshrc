# Path to your oh-my-zsh configuration.
export ZSH=$HOME/.oh-my-zsh

# Set name of the theme to load.
# Look in $ZSH/themes/
export ZSH_THEME="npinto"
#export ZSH_THEME="sorin"

# Set to this to use case-sensitive completion
# export CASE_SENSITIVE="true"

# Comment this out to disable weekly auto-update checks
export DISABLE_AUTO_UPDATE="true"

# Uncomment following line if you want to disable colors in ls
#export DISABLE_LS_COLORS="true"

# Uncomment following line if you want to disable autosetting terminal title.
# export DISABLE_AUTO_TITLE="true"

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-zsh/plugins/*)
# Example format: plugins=(rails git textmate ruby lighthouse)
plugins=(git vi-mode pip brew git-flow git-prompt)

# OMZ !
source $ZSH/oh-my-zsh.sh

# Customize to your needs...
# common bourne shell config
test -f $HOME/.shrc && source $HOME/.shrc

# disable auto-correct
unsetopt correct_all


export HISTFILE=$HOME/.history

# ----------------------------------------------------------------------------
#  Keybindings
# ----------------------------------------------------------------------------
# search in history
bindkey -M viins "^R" history-incremental-search-backward
bindkey -M vicmd "A" vi-add-eol
# ctrl-e end of line
bindkey -M viins "^E" end-of-line
bindkey -M vicmd "^E" end-of-line
# ctlr-a beg of line
bindkey -M viins "^A" beginning-of-line
bindkey -M vicmd "^A" beginning-of-line
# undo last undo
bindkey -M vicmd "^R" redo
# show cursor position info
bindkey -M vicmd "ga" what-cursor-position
# swap case over movement
bindkey -M vicmd "g~" vi-oper-swap-case
# search in history
bindkey -M viins "^R" history-incremental-search-backward
# more at http://www.opensource.cse.ohio-state.edu/sites/default/files/zshrc.txt

# -- fn+delete on MacOSX
bindkey "^[[3~" delete-char
bindkey -M vicmd "^[[3~" delete-char
bindkey -M viins "^[[3~" delete-char

