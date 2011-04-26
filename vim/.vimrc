syntax on
set number

set mouse=a

set tabstop=4 softtabstop=4 shiftwidth=4
set expandtab
set smarttab

filetype plugin indent on

if exists("+cursorcolumn")
    " vertical line
    set cursorcolumn
    " horizontal line
    set cursorline
endif
"set paste

" make {C,S}-{left,right} work in screen or tmux
map OC <Right>
map OD <Left>
map [C <S-Right>
map [D <S-Left>

" snipMate
filetype plugin on

" syntax for .cu files
au BufNewFile,BufRead *.cu setf cuda

" get around the "/dev/gpmctl: No such file or directory" bug with set mouse=a
set ttymouse=xterm2

" spellchecker
"setlocal spell spelllang=en_us
"set nospell
"autocmd BufNewFile,BufRead *.txt,*.html,README,*tex set spell

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

" Map a key to make the current window as large as possible
" (without closing other windows)
map <F5> <C-W>_<C-W><Bar>

"" pydiction
"filetype plugin on
"let g:pydiction_location = '~/.vim/plugin/pydiction-1.2/complete-dict'
"let python_higlight_all = 1
"let python_slow_sync = 1
"let python_print_as_function = 0

"" --------------------
"" MiniBufExpl
"" --------------------
"let g:miniBufExplTabWrap = 1 " make tabs show complete (no broken on two lines)
"let g:miniBufExplModSelTarget = 1 " If you use other explorers like TagList you can (As of 6.2.8) set it at 1:
"let g:miniBufExplUseSingleClick = 1 " If you would like to single click on tabs rather than double clicking on them to goto the selected buffer.
"let g:miniBufExplMaxSize = 1 " <max lines: defualt 0> setting this to 0 will mean the window gets as big as needed to fit all your buffers.
""let g:miniBufExplForceSyntaxEnable = 1 " There is a Vim bug that can cause buffers to show up without their highlighting. The following setting will cause MBE to
""let g:miniBufExplorerMoreThanOne = 1 " Setting this to 0 will cause the MBE window to be loaded even
""let g:miniBufExplMapWindowNavArrows = 1
""for buffers that have NOT CHANGED and are NOT VISIBLE.
"highlight MBENormal  ctermfg=LightBlue  guibg=LightGray guifg=DarkGray
"" buffers that have NOT CHANGED and are VISIBLE
"highlight MBEVisibleNormal term=bold cterm=bold gui=bold guibg=Gray guifg=Black ctermbg=Blue  ctermfg=Green
"" for buffers that HAVE CHANGED and are NOT VISIBLE
"highlight MBEChanged ctermfg=DarkRed guibg=Red guifg=DarkRed
"" buffers that HAVE CHANGED and are VISIBLE
"highlight MBEVisibleChanged term=bold cterm=bold gui=bold guibg=DarkRed guifg=Black ctermbg=Blue ctermfg=Red

"let g:miniBufExplMapWindowNavVim = 1
"let g:miniBufExplMapWindowNavArrows = 1
"let g:miniBufExplMapCTabSwitchBufs = 1
"let g:miniBufExplModSelTarget = 1

" Stolen from Paul Ivanov
set hlsearch     " highlight search terms
"set incsearch    " incremental search
set confirm      " confirm dialog instead of 'use ! to override'
set showmatch    " show matching parens
set ruler        " show row/col positions
set ignorecase   " ignore case when searching
set smartcase    " ... except when there are caps in the pattern
set showmode     " show current mode in bottom left corner
set laststatus=2 " Always display status line

" disable backup/swapfile (annoying)
set nobackup
set noswapfile

nnoremap <F2> :set invpaste paste? ruler<CR>
set pastetoggle=<F2>
set showmode

set modeline

" Tired of clearing highlighted searches by searching for “ldsfhjkhgakjks”?
" Use this:
nmap <silent> ,/ :nohlsearch<CR>
"nnoremap <esc> :noh<return><esc>

" Finally, a trick by Steve Losh for when you forgot to sudo before editing a
" file that requires root privileges (typically /etc/hosts). This lets you use
" w!! to do that after you opened the file already:
cmap w!! w !sudo tee % >/dev/null

"
filetype plugin indent on
autocmd filetype python set expandtab

" pylint
" autocmd FileType python compiler pylint

" colorscheme
"colorscheme desert
colorscheme mustang

" Vim can highlight whitespaces for you in a convenient way:
set list
"set listchars=tab:>.,trail:.,extends:#,nbsp:.
set listchars=tab:>.,trail:.,extends:#

" Disable all blinking:
set guicursor+=a:blinkon0

" indent
set autoindent
"set smartindent
set nosmartindent
set cindent
filetype indent on

" python stuff
set makeprg=python\ %<.py    " application to exec on :make and take current filename -- for python, mine


map <C-t><up> :tabr<cr>
map <C-t><down> :tabl<cr>
map <C-t><left> :tabp<cr>
map <C-t><right> :tabn<cr>

set t_Co=256
syntax on
"colorscheme wombat256mod


":set cursorline
" tweak cursorline and cursorcolumn, activate them by \c
" :hi CursorLine   cterm=NONE ctermbg=darkred ctermfg=white guibg=darkred guifg=white
":hi CursorColumn cterm=NONE ctermbg=gray ctermfg=white guibg=darkred guifg=white
" :nnoremap <Leader>c :set cursorline! cursorcolumn!<CR>
:nnoremap <Leader>c :set cursorline! <CR>

" map c-e to end-of-line
map <C-e> $<RIGHT>
imap <C-e> <ESC>$i<RIGHT>
" map c-a to start-of-line
map <C-a> 0
imap <C-a> <ESC>0i

" use bash-like file auto-completion
set wildmenu
set wildmode=list:longest


" add underscore as keyword (i.e. like a space)
"set iskeyword-=_

"" -- single character insert
"" inserts an underscore and then starts a command to replace a single
"" character. Thus when you type the character you want, it replaces the
"" underscore inserted by the mapping " from
"" http://ztatlock.blogspot.com/2009/01/vim-single-character-insert.html
"nmap <Space> i_<Esc>r


" -- Make it easy to update/reload vimrc
" <Leader> is \ by default, so those commands can be invoked
" by doing \v and \s
nmap <Leader>s :source $MYVIMRC
nmap <Leader>v :e $MYVIMRC


" see CamelCaseMotion plugin
"map <silent> w <Plug>CamelCaseMotion_w
"map <silent> b <Plug>CamelCaseMotion_b
"map <silent> e <Plug>CamelCaseMotion_e
"sunmap w
"sunmap b
"sunmap e


vmap r "_dP



function ShowSpaces(...)
  let @/='\v(\s+$)|( +\ze\t)'
  let oldhlsearch=&hlsearch
  if !a:0
    let &hlsearch=!&hlsearch
  else
    let &hlsearch=a:1
  end
  return oldhlsearch
endfunction

function TrimSpaces() range
  let oldhlsearch=ShowSpaces(1)
  execute a:firstline.",".a:lastline."substitute ///gec"
  let &hlsearch=oldhlsearch
endfunction

command -bar -nargs=? ShowSpaces call ShowSpaces(<args>)
command -bar -nargs=0 -range=% TrimSpaces <line1>,<line2>call TrimSpaces()
"nnoremap <F12>     :ShowSpaces 1<CR>
"nnoremap <S-F12>   m`:TrimSpaces<CR>``
"vnoremap <S-F12>   :TrimSpaces<CR>

" highlight error color for pyflakes (and any other SpellBad-dependent stuff)
highlight SpellBad ctermbg=darkgray


