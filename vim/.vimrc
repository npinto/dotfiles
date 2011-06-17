" ------------------------------------------
" -- pathogen
" ------------------------------------------
call pathogen#runtime_append_all_bundles()
call pathogen#helptags()

" ftplugin
filetype plugin on
filetype plugin indent on

" ------------------------------------------
" -- colorscheme
" ------------------------------------------
set t_Co=256
colorscheme mustang_np

" ------------------------------------------
" -- Keybindings
" ------------------------------------------
" set leader key
let mapleader=","

" make {C,S}-{left,right} work in screen or tmux
map OC <Right>
map OD <Left>
map [C <S-Right>
map [D <S-Left>

" map c-e to end-of-line
map <C-e> $<RIGHT>
imap <C-e> <ESC>$i<RIGHT>
" map c-a to start-of-line
map <C-a> 0
imap <C-a> <ESC>0i

" Make it easy to update/reload vimrc
nmap <Leader>s :source $MYVIMRC
nmap <Leader>v :e $MYVIMRC

"list the buffers and await choice
"(either numbers or some substring, enter keeps you in the same buffer)
map <leader>b :ls<cr>:buffer<space>
"go to the next buffer
map <leader>] :bn<CR>
"go to the previous buffer
map <leader>[ :bp<CR>
"kill the current buffer
map <leader>k :bd<CR>

" tabs
map <C-t><up> :tabr<cr>
map <C-t><down> :tabl<cr>
map <C-t><left> :tabp<cr>
map <C-t><right> :tabn<cr>

" replace self.A = B by B = self.A
command! -bar -range=% SwapEqual :<line1>,<line2>s/\(\s*\)\([^=]*\)\s\+=\s\+\([^;]*\)/\1\3 = \2/g | :nohl
nohl


" ------------------------------------------
" -- Indentation
" ------------------------------------------
" copy indent from current line when starting new line
set autoindent
" indent based on {}
" can be disabled with :set nosmartindent
set smartindent
" cindent gets annoying at times,
" so do :set nocindent if you want it off
set cindent
filetype indent on

" ------------------------------------------
" -- Tabs/Spaces
" ------------------------------------------
set tabstop=4 softtabstop=4 shiftwidth=4

" convert tabs to spaces
set expandtab

" tab inserts blanks according to 'shiftwidth'
set smarttab

" ------------------------------------------
" -- Syntax Highlighting
" ------------------------------------------
"" syntax
syntax on

" syntax for .cu files
au BufNewFile,BufRead *.cu setf cuda

" Highlight color definition for bad whitespace
highlight BadWhitespace ctermbg=red guibg=red
" Display tabs at the beginning of a line as bad.
match BadWhitespace /^\t\+/
" Display trailing whitespace as bad.
match BadWhitespace /\s\+$/

" highlight error color for pyflakes (and any other SpellBad-dependent stuff)
highlight SpellBad ctermbg=darkgray

" ------------------------------------------
" -- Visuals
" ------------------------------------------
" numbers
set number

" highlight search terms
set hlsearch

" Show current mode at the bottom left corner
set showmode

" Always display status line
set laststatus=2

" show matching parentheses
set showmatch

" show row/col positions
set ruler

" toggle terminal/mouse support for select/copy/paste
nmap <leader>mt :set mouse=a number list <CR>
nmap <leader>mm :set mouse= nonumber nolist <CR>

" Use the same symbols as TextMate for tabstops and EOLs
" from http://vimcasts.org/episodes/show-invisibles
"set listchars=tab:>.,trail:.,extends:#,nbsp:.
set list
set listchars=tab:▸\ ,eol:¬,trail:~
" Shortcut to rapidly toggle `set list`
nmap <leader>l :set list!<CR>

" visual guides
if exists("+cursorcolumn")
    " vertical line
    set cursorcolumn
    " horizontal line
    set cursorline
endif
:nnoremap <Leader>c :set cursorline! cursorcolumn!<CR>

" visual bell
set visualbell

" Tired of clearing highlighted searches
" by searching for “ldsfhjkhgakjks”?
" Use this:
nmap <silent> <leader>/ :nohlsearch<CR>
"nnoremap <esc> :noh<return><esc>

" Disable all blinking:
set guicursor+=a:blinkon0

" ------------------------------------------
" -- Mouse Support
" ------------------------------------------
set mouse=a

" get around the "/dev/gpmctl: No such file or directory"
" bug with set mouse=a
set ttymouse=xterm2

" ------------------------------------------
" -- Editing Helpers
" ------------------------------------------

" folding (with shortcuts)
augroup vimrc
  au BufReadPre * setlocal foldmethod=indent
  au BufWinEnter * if &fdm == 'indent' | setlocal foldmethod=manual | endif
augroup END
set foldlevelstart=20
nnoremap <space> za
vnoremap <space> zf

" paste mode
nnoremap <F2> :set invpaste paste? ruler<CR>
set pastetoggle=<F2>

" Twiddle case:
" press ~ to convert the text to UPPER CASE, then to lower case, then to
" Title Case. Keep pressing ~ until you get the case you want.
function! TwiddleCase(str)
  if a:str ==# toupper(a:str)
    let result = tolower(a:str)
  elseif a:str ==# tolower(a:str)
    let result = substitute(a:str,'\(\<\w\+\>\)', '\u\1', 'g')
  else
    let result = toupper(a:str)
  endif
  return result
endfunction
vnoremap ~ ygv"=TwiddleCase(@")<CR>Pgv

" modeline
" allows inline settings at the beginning/end of file
" (e.g. :ai:ts=4:)
set modeline

" Append modeline after last line in buffer.
" Use substitute() instead of printf() to handle '%%s' modeline in LaTeX
" files.
function! AppendModeline()
  let l:modeline = printf(" vim: set ts=%d sw=%d tw=%d :",
        \ &tabstop, &shiftwidth, &textwidth)
  let l:modeline = substitute(&commentstring, "%s", l:modeline, "")
  call append(line("$"), l:modeline)
endfunction
nnoremap <silent> <Leader>ml :call AppendModeline()<CR>

" sudo trick
" by Steve Losh for when you forgot to sudo before editing a
" file that requires root privileges (typically /etc/hosts). This lets you use
" w!! to do that after you opened the file already:
cmap w!! w !sudo tee % >/dev/null

" Show and Trim Whitespaces
function! ShowSpaces(...)
  let @/='\v(\s+$)|( +\ze\t)'
  let oldhlsearch=&hlsearch
  if !a:0
    let &hlsearch=!&hlsearch
  else
    let &hlsearch=a:1
  end
  return oldhlsearch
endfunction

function! TrimSpaces() range
  let oldhlsearch=ShowSpaces(1)
  execute a:firstline.",".a:lastline."substitute ///gec"
  let &hlsearch=oldhlsearch
endfunction

command! -bar -nargs=? ShowSpaces call ShowSpaces(<args>)
command! -bar -nargs=0 -range=% TrimSpaces <line1>,<line2>call TrimSpaces()
"nnoremap <F12>     :ShowSpaces 1<CR>
"nnoremap <S-F12>   m`:TrimSpaces<CR>``
"vnoremap <S-F12>   :TrimSpaces<CR>

" Make the backspace key wrap lines
set backspace=indent,eol,start

" Put (vim) at the end of the window title
set title titlestring=%t\ (vim)

" Fast saving
nmap <leader>w :w!<CR>


" ------------------------------------------
" -- Search
" ------------------------------------------

" ignore case when searching
set ignorecase

" ... except when there are caps in the pattern
set smartcase

" incremental search (as you type)
"set incsearch

" ------------------------------------------
" -- MISC
" ------------------------------------------

" Map a key to make the current window as large as possible
" (without closing other windows)
map <F6> <C-W>_<C-W><Bar>

" confirm dialog instead of 'use ! to override'
set confirm

" When switching buffers, do not warn if file is modified
set hidden

" disable backup/swapfile (annoying)
set nobackup
set noswapfile

" application to exec on :make and take current filename -- for python, mine
set makeprg=python\ %<.py

" ipython syntax highlighting
au FileType ipy set syntax=python

" doc/release/0.8.0-notes.rst

" use bash-like file auto-completion
set wildmenu
set wildmode=list:longest
