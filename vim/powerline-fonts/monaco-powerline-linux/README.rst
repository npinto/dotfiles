
INSTALL
=======

Just download and put into your ~/.fonts dir and run ``fc-cache -vf``

If you're using urxvt add something like this to your ~/.Xresources or ~/.Xdefaults::

    URxvt*font:                 xft:Monaco for Powerline:regular:size=8
    URxvt*imFont:               xft:Monaco for Powerline:regular:size=8
    URxvt*boldFont:             xft:Monaco for Powerline:bold:size=8
    URxvt*italicFont:           xft:Monaco for Powerline:italic:size=8
    URxvt*boldItalicFont:       xft:Monaco for Powerline:bold:italic:size=8


Make sure to run ``xrdb -merge ~/.Xresources`` afterwards and close all urxvt terminals.


