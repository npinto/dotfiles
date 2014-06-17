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
#plugins=(git vi-mode pip brew git-flow git-prompt)
plugins=(vi-mode pip brew git-flow git-prompt)

# -- systemwide .profile
test -z ${EPREFIX} && test -f /etc/profile && source /etc/profile

# OMZ !
test -f $ZSH/oh-my-zsh.sh && source $ZSH/oh-my-zsh.sh

# -- Customize to your needs...

# common bourne shell config
test -f $HOME/.shrc && source $HOME/.shrc

# disable auto-correct
unsetopt correct_all

# disable shared history
unsetopt share_history

# prevent > redirection from truncating the given file if it already exists
setopt no_clobber

export HISTFILE=$HOME/.history

# Print the exit value of programs with non-zero exit status
setopt PRINT_EXIT_VALUE

# Efficient completion
zstyle ':completion:*' accept-exact '*(N)'
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path ~/.zsh/cache

# ----------------------------------------------------------------------------
#  Keybindings
# ----------------------------------------------------------------------------
# search in history
bindkey -M viins "^R" history-incremental-search-backward
bindkey -M vicmd "A" vi-add-eol
# kill line
bindkey "^K" kill-line
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

# -- inserting the last word from the previous command.
bindkey '\e.' insert-last-word

# -- bind jj to Esc
#bindkey "jj" vi-cmd-mode

# -- ESC-v to edit in an external editor
bindkey -M vicmd v edit-command-line

fpath=(/usr/local/share/zsh-completions $fpath)

# -- history goodness
bindkey ' ' magic-space
bindkey -M vicmd "gg" beginning-of-history
bindkey -M vicmd "G" end-of-history
bindkey -M vicmd "k" history-search-backward
bindkey -M vicmd "j" history-search-forward
bindkey -M vicmd "?" history-incremental-search-backward
bindkey -M vicmd "/" history-incremental-search-forward

# -- (duplicate stuff)
bindkey -M viins "^L" clear-screen
bindkey -M viins "^W" backward-kill-word
bindkey -M viins "^A" beginning-of-line
bindkey -M viins "^E" end-of-line
