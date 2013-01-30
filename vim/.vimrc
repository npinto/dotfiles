" -------------------------------------------------------------------
" -- pathogen
" -------------------------------------------------------------------
call pathogen#runtime_append_all_bundles()
call pathogen#helptags()

" ftplugin
filetype plugin on
filetype plugin indent on

" -------------------------------------------------------------------
" -- colorscheme
" -------------------------------------------------------------------
if $TERM =~ '^linux'
    set t_Co=8
    set background=dark
    colorscheme solarized
    let g:solarized_termcolors=16
else
    set t_Co=256
    "colorscheme  desert256
    "colorscheme mustang_np
    "colorscheme ir_black
    " -- solarized
    " http://ethanschoonover.com/solarized
    set background=dark
    colorscheme solarized
    let g:solarized_termcolors=256
endif

" -------------------------------------------------------------------
" -- Keybindings
" -------------------------------------------------------------------
" set leader key
let mapleader=","

" Press ,, to Escape
imap ,, <Esc>
" Press ,. to Escape
imap ,. <Esc>
" Press <C-\> to Escape
imap <C-\> <Esc>l
" Press jj to Escape
"imap jj <Esc>

" http://nvie.com/posts/how-i-boosted-my-vim/
nnoremap ; :

" Use Q for formatting the current paragraph (or selection)
vmap Q gq
nmap Q gqap

" Fix backspace
set bs=2

" Press \\ to save and exit (ZZ)
map \\ ZZ

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

" map Enter to open line in command mode
map <CR> o<Esc>
"map <C-CR> O<Esc>

" Make it easy to update/reload vimrc
nmap <leader>v :e $MYVIMRC<CR><C-W>_
nmap <silent> <leader>V :source $MYVIMRC<CR>:filetype detect<CR>:exec ":echo '$MYVIMRC reloaded'"<CR>

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
"map <C-p> :tabp<cr>
"map <C-n> :tabn<cr>

" replace self.A = B by B = self.A
command! -bar -range=% SwapEqual :<line1>,<line2>s/\(\s*\)\([^=]*\)\s\+=\s\+\([^;]*\)/\1\3 = \2/g | :nohl
nohl

" NERDTree
nmap <silent> <Leader>nt :NERDTreeToggle<CR>
nmap <silent> <Leader>nf :NERDTreeFind<CR>
nmap <silent> <Leader>no :NERDTreeFocus<CR>
let NERDTreeShowHidden=1

" -------------------------------------------------------------------
" -- Indentation
" -------------------------------------------------------------------
" copy indent from current line when starting new line
set autoindent
" indent based on {}
" can be disabled with :set nosmartindent
set smartindent
" cindent gets annoying at times,
" so do :set nocindent if you want it off
set cindent
filetype indent on


" -------------------------------------------------------------------
" -- Tabs/Spaces
" -------------------------------------------------------------------
set tabstop=4 softtabstop=4 shiftwidth=4

" convert tabs to spaces
set expandtab

" tab inserts blanks according to 'shiftwidth'
set smarttab

" -------------------------------------------------------------------
" -- Syntax Highlighting
" -------------------------------------------------------------------

" syntax
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
"highlight SpellBad ctermbg=darkgray

" Gentoo's ebuild
" from www.gentoo.org/proj/en/devrel/handbook/handbook.xml?part=2&chap=1
au BufRead,BufNewFile *.e{build,class} let is_bash=1|setfiletype sh
au BufRead,BufNewFile *.e{build,class} set ts=4 sw=4 noexpandtab


" -------------------------------------------------------------------
" -- Visuals
" -------------------------------------------------------------------
" numbers
set number

" highlight search terms
"set hlsearch
" don't highlight search terms
set nohlsearch

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
":nnoremap <Leader>c :set cursorline! cursorcolumn!<CR>

" visual bell
set visualbell

" Tired of clearing highlighted searches
" by searching for “ldsfhjkhgakjks”?
" Use this:
nmap <silent> <leader>/ :set hlsearch! hlsearch?<CR>
"nnoremap <esc> :noh<return><esc>

" Disable all blinking:
set guicursor+=a:blinkon0

" -------------------------------------------------------------------
" -- Mouse Support
" -------------------------------------------------------------------
set mouse=a

" get around the "/dev/gpmctl: No such file or directory"
" bug with set mouse=a
set ttymouse=xterm2

" -------------------------------------------------------------------
" -- Folds
" -------------------------------------------------------------------

" Don't open folds when browsing with "(", "{", "[[", "[{", etc.
set foldopen-=block

" Don't open folds when searching
set foldopen-=search

" Don't open folds when in insert mode
"set foldopen-=insert

" Don't underlines my folds
hi Folded term=NONE cterm=NONE ctermfg=NONE ctermbg=NONE
hi Folded gui=NONE guifg=NONE guibg=NONE
set fillchars="fold: "

" -------------------------------------------------------------------
" -- Buffer Navigation
" -------------------------------------------------------------------
" -- miniBufExpl plugin
let g:miniBufExplMapWindowNavVim = 1
let g:miniBufExplMapWindowNavArrows = 1
let g:miniBufExplModSelTarget = 1
let g:miniBufExplUseSingleClick = 1
let g:miniBufExplSplitBelow=1
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


" -------------------------------------------------------------------
" -- Window Navigation
" -------------------------------------------------------------------

" From http://stackoverflow.com/questions/2228353/how-to-swap-files-between-windows-in-vim
if version >= 700

    function! HOpen(dir,what_to_open)

        let [type,name] = a:what_to_open

        if a:dir=='left' || a:dir=='right'
            vsplit
            elseif a:dir=='up' || a:dir=='down'
            split
        end

        if a:dir=='down' || a:dir=='right'
            exec "normal! \<c-w>\<c-w>"
        end

        if type=='buffer'
            exec 'buffer '.name
            else
            exec 'edit '.name
        end
    endfunction

    function! HYankWindow()
        let g:window = winnr()
        let g:buffer = bufnr('%')
        let g:bufhidden = &bufhidden
    endfunction

    function! HDeleteWindow()
        call HYankWindow()
        set bufhidden=hide
        close
    endfunction

    function! HPasteWindow(direction)
        let old_buffer = bufnr('%')
        call HOpen(a:direction,['buffer',g:buffer])
        let g:buffer = old_buffer
        let &bufhidden = g:bufhidden
    endfunction

    noremap <c-w>d :call HDeleteWindow()<cr>
    noremap <c-w>y :call HYankWindow()<cr>
    noremap <c-w>p<up> :call HPasteWindow('up')<cr>
    noremap <c-w>p<down> :call HPasteWindow('down')<cr>
    noremap <c-w>p<left> :call HPasteWindow('left')<cr>
    noremap <c-w>p<right> :call HPasteWindow('right')<cr>
    noremap <c-w>pk :call HPasteWindow('up')<cr>
    noremap <c-w>pj :call HPasteWindow('down')<cr>
    noremap <c-w>ph :call HPasteWindow('left')<cr>
    noremap <c-w>pl :call HPasteWindow('right')<cr>
    noremap <c-w>pp :call HPasteWindow('here')<cr>
    noremap <c-w>P :call HPasteWindow('here')<cr>

endif


" -------------------------------------------------------------------
" -- Editing Helpers
" -------------------------------------------------------------------

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
  "let l:modeline = printf(" vim: set ts=%d sw=%d tw=%d :",
  let l:modeline = printf(" vim: set ts=%d sw=%d :",
        \ &tabstop, &shiftwidth, &textwidth)
  let l:modeline = substitute(&commentstring, "%s", l:modeline, "")
  call append(line("$"), l:modeline)
endfunction
command! -bar -nargs=0 AppendModeline call AppendModeline()
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
"set backspace=indent,eol,start

" When editing a text file, if you want word wrapping, but only want line
" breaks inserted when you explicitly press the Enter key:
" (see http://vim.wikia.com/wiki/Word_wrap_without_line_breaks)
"set wrap
"set linebreak
"set nolist  " list disables linebreak
"set wrapmargin=0

" Put (vim) at the end of the window title
set title titlestring=%t\ (vim)

" Fast saving
nmap <leader>w :w!<CR>

" GRB: use fancy buffer closing that doesn't close the split
" from http://goo.gl/AVz1V
cnoremap <expr> bd (getcmdtype() == ':' ? 'Bclose' : 'bd')


" -------------------------------------------------------------------
" -- Search
" -------------------------------------------------------------------

" ignore case when searching
set ignorecase

" ... except when there are caps in the pattern
set smartcase

" incremental search (as you type)
"set incsearch

" -------------------------------------------------------------------
" -- Text Width and Highlight
" -------------------------------------------------------------------

" -- Text Width
"
" text width at 72 characters
" (best to view 4 vertical windows on 30'' screen)
"let g:textwidth = 72
"set textwidth=g:textwidth
set textwidth=72
" set formatoptions to avoid breaking lines in insert mode
"set formatoptions=roqM1
set formatoptions=qM1
" disable textwidth entirely
"set textwidth=0

" -- OverLength Highlight
"
au FileType python highlight OverLength ctermbg=darkred ctermfg=white guibg=#592929
au FileType python highlight OverLength ctermbg=red ctermfg=white guibg=#592929
au FileType python match OverLength /\%81v.\+/

" -------------------------------------------------------------------
" -- Whitespace preferences by filetype
" -------------------------------------------------------------------
autocmd Filetype html setlocal ts=2 sts=2 sw=2
autocmd Filetype ruby setlocal ts=2 sts=2 sw=2
autocmd Filetype javascript setlocal ts=4 sts=4 sw=4


" -------------------------------------------------------------------
" -- Auto Completion
" -------------------------------------------------------------------

" -- SuperTab
let g:SuperTabDefaultCompletionType = "context"
let g:SuperTabRetainCompletionDuration = "completion"
let g:SuperTabNoCompleteAfter = [',', '\s']
let g:SuperTabLongestEnhanced = 1
" Default to Keyword Completion
let g:SuperTabContextTextOmniPrecedence = ['&completefunc']
let g:SuperTabContextDiscoverDiscovery = ["&completefunc:<c-x><c-u>"]

" -- Omnicomplete
filetype plugin on
set ofu=syntaxcomplete#Complete
autocmd FileType python set omnifunc=pythoncomplete#Complete
"autocmd FileType python set completefunc=pythoncomplete#Complete

" If you prefer the Omni-Completion tip window to close when a selection
" is made, these lines close it on movement in insert mode or when
" leaving insert mode
" from http://stackoverflow.com/questions/3105307/how-do-you-automatically-remove-the-preview-window-after-autocompletion-in-vim
autocmd CursorMovedI * if pumvisible() == 0|pclose|endif
autocmd InsertLeave * if pumvisible() == 0|pclose|endif

" remap omnicomplete's c-x c-o to c-space
inoremap <Nul> <C-x><C-o>

" -- autocomplete on dashed-words, very useful for css
set iskeyword+=-

" From Paul Ivanov:
""
"" XXX: i think this is slow in large projects!
"" not even sure if this works, don't really use it
"autocmd FileType python set omnifunc=pythoncomplete#Complete
"" ctrl-space to omnicomplete
""inoremap <Nul> <C-x><C-o>
"inoremap <Nul> <space>
"set suffixesadd+=.c,.cpp,.h,.java,.l,.py,.cu,.rst,
""set background=dark
""let's see if this is any good
""set clipboard=unnamed
""filetype on
""filetype indent on
"filetype plugin indent on
""colorscheme kate
""colorscheme wombat
"colorscheme tortepi
"colorscheme blue
""highlight Comment ctermbg=darkgreen guifg=darkgreen
"set spelllang=en,ru
"command! SpellCheck :set spell
"command! Spell :!aspell -c "%"
"command! T :Tlist
"" don't use this anymore - use rubber instead
"" command! Latex :set makeprg=latex\ %\ &&\ dvipdf\ %<.dvi
""iab ,b \begin{}<Esc>i
""iab ,e \end{}<Esc>i
""iab ,m $$ $$hh
""iab ., {}h
"map <F8> :make<cr><cr>
"map <F7> :w!<CR>:Spell<CR>:e! %<CR>
"map <F6> :w!<CR>:!wc %<CR>
"map <F2> :!sort -n<CR>
"map <F4> :Todo<CR>

" Speed up switching between splits
map <C-J> <C-W>j
map <C-K> <C-W>k
map <C-h> <C-W>h
map <C-l> <C-W>l


" -------------------------------------------------------------------
" -- Python related
" -------------------------------------------------------------------

" autopep8
cmap apep8 !autopep8 -i %

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
    """let &makeprg = prg . ' %'
    """silent make!
    """let qflist += getqflist()
  "endfor
  "if empty(qflist)
    "cclose
  "else
    """call setqflist(qflist)
    """copen
    """cfirst
  "endif
  "let &makeprg = savemp
"endfunction

" Python PEP8 text width (79 for code, 72 for comments)
"function! GetPythonTextWidth()
    "if !exists('g:python_normal_text_width')
        "let normal_text_width = 79
    "else
        "let normal_text_width = g:python_normal_text_width
    "endif

    "if !exists('g:python_comment_text_width')
        "let comment_text_width = 72
    "else
        "let comment_text_width = g:python_comment_text_width
    "endif

    "let cur_syntax = synIDattr(synIDtrans(synID(line("."), col("."), 0)), "name")
    "if cur_syntax == "Comment"
        "return comment_text_width
    "elseif cur_syntax == "String"
        "" Check to see if we're in a docstring
        "let lnum = line(".")
        "while lnum >= 1 && (synIDattr(synIDtrans(synID(lnum, col([lnum, "$"]) - 1, 0)), "name") == "String" || match(getline(lnum), '\v^\s*$') > -1)
            "if match(getline(lnum), "\\('''\\|\"\"\"\\)") > -1
                """ Assume that any longstring is a docstring
                ""return comment_text_width
            "endif
            "let lnum -= 1
        "endwhile
    "endif

    "return normal_text_width
"endfunction

"augroup pep8
    "au!
    "autocmd CursorMoved,CursorMovedI * :if &ft == 'python' | :exe 'setlocal textwidth='.GetPythonTextWidth() | :endif
"augroup END


" -------------------------------------------------------------------
" -- Folding
" -------------------------------------------------------------------

" folding (with shortcuts)
augroup vimrc
  au BufReadPre * setlocal foldmethod=indent
  au BufWinEnter * if &fdm == 'indent' | setlocal foldmethod=manual | endif
  au BufWinEnter * normal zR
augroup END
set foldlevelstart=100
set foldlevel=100
"set nofoldenable
"autocmd Syntax c,cpp,vim,xml,html,xhtml,perl,python,ebuild normal zR
set foldmethod=manual

nnoremap <space> za
vnoremap <space> zf

"" save and restores folds when a file is closed and re-opened
" XXX: FIXME
au BufWinLeave *.* mkview
au BufWinEnter *.* silent loadview

"let g:skipview_files = [
            "\ '[EXAMPLE PLUGIN BUFFER]'
            "\ ]

"function! MakeViewCheck()
    "if has('quickfix') && &buftype =~ 'nofile'
        "" Buffer is marked as not a file
        "return 0
    "endif
    "if empty(glob(expand('%:p')))
        "" File does not exist on disk
        "return 0
    "endif
    "if len($TEMP) && expand('%:p:h') == $TEMP
        "" We're in a temp dir
        "return 0
    "endif
    "if len($TMP) && expand('%:p:h') == $TMP
        "" Also in temp dir
        "return 0
    "endif
    "if index(g:skipview_files, expand('%')) >= 0
        "" File is in skip list
        "return 0
    "endif
    "return 1
"endfunction

"augroup vimrcAutoView
    "autocmd!
    "" Autosave & Load Views.
    "autocmd BufWritePost,BufLeave,WinLeave ?* if MakeViewCheck() | mkview | endif
    "autocmd BufWinEnter ?* if MakeViewCheck() | silent loadview | endif
"augroup end


" -------------------------------------------------------------------
" -- Code analysis
" -------------------------------------------------------------------
"autocmd BufWritePost *.py call Flake8()


" -------------------------------------------------------------------
" -- MISC
" -------------------------------------------------------------------

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

" -- Comments
" overrides 'comments.vim' with NERD Commetners
map <C-c> <leader>c<space>
map <C-x> <leader>c<space>

" -- Don't flicker when executing macros/functions
set lazyredraw

" -- vim-powerline
let g:Powerline_symbols = 'fancy'
