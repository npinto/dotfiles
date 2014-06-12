#!/usr/bin/env python

import sys
from glob import iglob
pattern = sys.argv[1]
print pattern
fnames = iglob(pattern)
i = 0
for fname in fnames:
    i += 1
    if i % 100 == 0:
        print '%e' % i
print '%e' % i
