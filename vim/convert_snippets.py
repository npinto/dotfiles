#!/usr/bin/env python2.6
"""
About
=====

Convert Texmate snippets into snipmate compatible snippets

http://www.vim.org/scripts/script.php?script_id=2540
http://macromates.com/

Requires Python2.6+ since it relies on plistlib.

The plistlib module cannot read binary plist objects. See this OS X Hint for
details on how to convert them.

http://hints.macworld.com/article.php?story=20050430105126392

Usage
=====

$ mkdir ~/converted_snippets
$ cd path/to/Some.tmbundle/Snippets
$ snipmatize.py

The stock bundles can be found in the TextMate.app package. For example,
here is the path to the CSS bundle.

/Applications/TextMate.app/Contents/SharedSupport/Bundles/CSS.tmbundle/Snippets

Any bundles that you have modified or installed manually will be in your
Library directory:

~/Library/Application\ Support/TextMate/Bundles

TODO
====

- handle backtick enclosed items and make them use system()
- handle $TM_* vars
- un-nesting placeholders needs work
"""
import codecs
import os
import re
from glob import glob
from optparse import OptionParser
from plistlib import readPlist
from xml.parsers.expat import ExpatError


def convert_snippets(input_dir, output_dir):
    """Convert a folder full of TextMate snippets to snipMate
    snippets
    """
    # regex to find the snip tabs
    snip_num_re = r"(?:\$(\d+)|\${(\d+)})"
    snip_place_re = r"#(\d*)#"
    # XXX: this is quite ugly, but we need to remove the placeholder
    #      nesting since snipMate doesn't support it.
    nested_re = r"\${\d+:([^#}]*#\d+#[^#}]*)}"
    # TODO: should be able to specify a single file as well.
    tm_snippets = glob('%s/*.tmSnippet' % input_dir)
    plists = glob('%s/*.plist' % input_dir)
    tm_snippet_files = tm_snippets + plists
    for tm_snippet_file in tm_snippet_files:
        try:
            tm_snippet = readPlist(tm_snippet_file)
        except ExpatError:
            msg = "Could not read binary plist (see the docs for help): %s"
            print msg % tm_snippet_file
            continue
        trigger = tm_snippet.get('tabTrigger', None)
        if trigger is None:
            continue
        scope = tm_snippet.get('scope', 'NOSCOPE')
        sf = "%s/%s.snippets" % (output_dir, scope)
        snippet_file = codecs.open(sf, 'a', encoding='utf-8')
        snip_lines = tm_snippet['content'].split("\n")
        new_snippet = []
        snip_name = tm_snippet['name']
        snip_shortcut = "snippet %s" % trigger
        snip_comment = "# %s" % snip_name
        # put some info about the previous snippet
        new_snippet.append("%s\n" % snip_comment)
        new_snippet.append("%s\n" % snip_shortcut)
        # XXX this is pretty dumb, but works for now
        for line in snip_lines:
            if re.search(snip_num_re, line):
                try:
                    # replace the tab stop with our placeholder
                    line = re.sub(snip_num_re, "#\g<2>#", line)
                except re.error:
                    # replace the other kind of tab stop with ours
                    line = re.sub(snip_num_re, "#\g<1>#", line)
            # remove the nesting
            if re.findall(nested_re, line):
                line = re.sub(nested_re, "\g<1>", line)
            # put it back together
            if re.findall(snip_place_re, line):
                line = re.sub(snip_place_re, "${\g<1>}", line)
            # add the newly formatted line
            new_snippet.append("\t%s\n" % line)
        new_snippet_str = "".join(new_snippet)
        try:
            snippet_file.write(new_snippet_str)
        except UnicodeEncodeError:
            # otherwise just brutally make it ascii
            snippet_file.write(new_snippet_str.encode('ascii', 'ignore'))
        snippet_file.close()


def main():
    parser = OptionParser()
    parser.add_option(
        "-i",
        dest="input_dir",
        default='.',
        )
    parser.add_option(
        "-o",
        dest="output_dir",
        default=os.path.expanduser('~/converted_snippets'),
        )
    options, args = parser.parse_args()
    convert_snippets(options.input_dir, options.output_dir)


if __name__ == '__main__':
    main()