#!/usr/bin/env python

import wave
import pyogg
import numpy as np

import sys

infn = sys.argv[1]
outbn = sys.argv[2]


mogg = pyogg.VorbisFile(infn)
n_ch = mogg.channels
print(infn, n_ch)

buff = mogg.buffer

for i in range(n_ch):
    outfn = outbn + '.%d.wav' % i
    print(outfn, i)
    buff_arr = np.frombuffer(buff, dtype='int16')
    with wave.open(outfn, "wb") as outf:
        outf.setnchannels(1)
        outf.setsampwidth(2) # number of bytes
        outf.setframerate(44100)
        outf.writeframesraw(buff_arr[i::11].tobytes())
