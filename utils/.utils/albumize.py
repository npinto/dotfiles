#!/usr/bin/env python

from glob import glob
import os

fns = sorted(glob("./*.mp3"))

for i, fn in enumerate(fns):
    cmd = 'mp3info -n %d "%s"' % (i + 1, fn)
    print cmd
    err = os.system(cmd)
    assert err == 0
