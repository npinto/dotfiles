#!/usr/bin/env python3

import sys
import urllib.parse

infn = sys.argv[1]

data = open(infn).readlines()

grep_v_in_l = [
    'Copyright owners',
    'Ad revenue',
    'Content found during',
    'some territories',
    'cannot be monetized',
    'Copyright owner',
    'On behalf',
    'GmbH',
    'LLC',
    'Content used',
    'Claim type',
    'Impact on the video',
    'Actions',
    '/',
]
grep_v_eq_l = [
    '1.00\n'
]

out_lines = []
accum = []
for line in data:
    skip = False
    for grep in grep_v_in_l:
        if grep in line:
            skip = True
            break
    if skip:
        continue
    for grep in grep_v_eq_l:
        if line == grep:
            skip = True
            break
    if skip:
        continue
    line = line.replace(' – ', ' => ')
    accum.append(line)
    if ' => ' in line:
        if len(accum) == 3:
            out_line = accum[1].strip() + ' - ' + accum[0].strip()
        elif len(accum) == 4:
            out_line = accum[2].strip() + ' - ' + accum[1].strip()
        else:
            raise IndexError
        out_lines.append(out_line + '\n')
        out_lines.append(accum[-1])
        out_lines.append('URL ' + urllib.parse.quote(out_line) + '\n')
        out_lines.append('\n')
        accum = []

print(''.join(out_lines))
