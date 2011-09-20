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
if $TERM =~ '^linux'
    set t_Co=8
else
    set t_Co=256
    colorscheme mustang_np
    "colorscheme ir_black
endif

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
" -- Buffer Navigation
" ------------------------------------------
" -- miniBufExpl plugin
let g:miniBufExplMapWindowNavVim = 1
let g:miniBufExplMapWindowNavArrows = 1
let g:miniBufExplModSelTarget = 1
let g:miniBufExplUseSingleClick = 1
" Replace the following
"let g:miniBufExplMapCTabSwitchBufs = 1
" with tmux-like bindings to avoid conflicts with snipMate <C-TAB>
noremap <C-n> :MBEbn<CR>
noremap <C-p> :MBEbp<CR>
" Fix bug described in
" https://github.com/fholgado/minibufexpl.vim/issues/1
au BufEnter * call MyLastWindow()
function! MyLastWindow()
  " if the window is quickfix go on
  if &buftype=="nofile"
    " if this window is last on screen quit without warning
    if winnr('$') < 2
      quit!
    endif
  endif
endfunction


" ------------------------------------------
" -- Editing Helpers
" ------------------------------------------

" folding (with shortcuts)
augroup vimrc
  au BufReadPre * setlocal foldmethod=indent
  au BufWinEnter * if &fdm == 'indent' | setlocal foldmethod=manual | endif
augroup END
"set foldlevelstart=20
nnoremap <space> za
vnoremap <space> zf
" save and restores folds when a file is closed and re-opened
"au BufWinLeave *.* mkview
"au BufWinEnter *.* silent loadview
let g:skipview_files = [
            \ '[EXAMPLE PLUGIN BUFFER]'
            \ ]
function! MakeViewCheck()
    if has('quickfix') && &buftype =~ 'nofile'
        " Buffer is marked as not a file
        return 0
    endif
    if empty(glob(expand('%:p')))
        " File does not exist on disk
        return 0
    endif
    if len($TEMP) && expand('%:p:h') == $TEMP
        " We're in a temp dir
        return 0
    endif
    if len($TMP) && expand('%:p:h') == $TMP
        " Also in temp dir
        return 0
    endif
    if index(g:skipview_files, expand('%')) >= 0
        " File is in skip list
        return 0
    endif
    return 1
endfunction
augroup vimrcAutoView
    autocmd!
    " Autosave & Load Views.
    autocmd BufWritePost,BufLeave,WinLeave ?* if MakeViewCheck() | mkview | endif
    autocmd BufWinEnter ?* if MakeViewCheck() | silent loadview | endif
augroup end

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
"
" ------------------------------------------
" -- Python related
" ------------------------------------------

" application to exec on :make and take current filename -- for python, mine
set makeprg=python\ %<.py

" ipython syntax highlighting
au FileType ipy set syntax=python

let g:pyflakes_use_quickfix = 0

"" Do make with different makeprg settings.
"" Error lists from each makeprg are combined into one quickfix list.
"command! Pycheck call DoMake('pyflakes', 'pep8')
"function! DoMake(...)
  "update  " save any changes because makeprg checks the file on disk
  "let savemp = &makeprg
  "let qflist = []
  "for prg in a:000
    "let &makeprg = prg . ' %'
    "silent make!
    "let qflist += getqflist()
  "endfor
  "if empty(qflist)
    "cclose
  "else
    "call setqflist(qflist)
    "copen
    "cfirst
  "endif
  "let &makeprg = savemp
"endfunction

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

" use bash-like file auto-completion
set wildmenu
set wildmode=list:longest

"" http://vim.wikia.com/wiki/Show_entire_multiline_error_in_quickfix
"" \cc
"map <Leader>cc :cwindow<CR>:cc<CR><c-w>bz<CR><CR>
"" \cn
"map <Leader>cn :cwindow<CR>:cn<CR><c-w>bz<CR><CR>
"" \cp
"map <Leader>cp :cwindow<CR>:cp<CR><c-w>bz<CR><CR>

" Quickfix jump to error line through press Enter
" http://vim.1045645.n5.nabble.com/Quickfix-jumping-td1191243.html
"set errorformat=%A%f\ IBM%nI\ %t\ %l.0\ %m,%Z%m
map <leader>qn :cn<CR>
map <leader>qp :cp<CR>
