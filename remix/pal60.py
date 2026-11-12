#!/usr/bin/env python3
"""Cool Boarders 2 PAL at 60 Hz (prototype).

The European version is the USA one adapted to 50 Hz: it starts in PAL video mode (SetVideoMode(1)) and many constants
(durations in frames, thresholds, screen height 256, positions) were changed, mostly by x5/6 or x6/5. This module
gives back the USA values to the European code, so the European disc runs at 60 Hz at the right speed:
  1. video mode NTSC at start-up (exe 0x800122E0: 'addiu a0, zero, 1' -> 0),
  2. every constant of the aligned code (same instruction in both versions, see tools/port_usa.py) that differs
     takes the USA value: addiu/ori from $zero, slti/sltiu/andi.
Not handled yet: the few blocks the European version inserted to rescale values (e.g. x35/25 on the spin input).
usage: python3 remix/pal60.py PAL_fs USA_fs  -> list of (file, PAL address, old word, new word)
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from port_usa import FILES, words

def patches(port, pal_fs, usa_fs):
    out = [('/SCES_009.92', 0x800122E0, 0x24040001, 0x24040000)]          # SetVideoMode(MODE_NTSC) (delay slot of the call)
    W = {}
    for pf, uf, b, ub, hdr in FILES:
        W[pf] = (words(os.path.join(pal_fs, pf), hdr), words(os.path.join(usa_fs, uf), hdr), b, ub)
    for (f, pa), ua in sorted(port.cmap.items()):
        P, U, b, ub = W[f]; x = P[(pa - b) // 4]; y = U[(ua - ub) // 4]
        if x == y or (x & 0xffff0000) != (y & 0xffff0000): continue
        op = x >> 26; rs = (x >> 21) & 31
        if op in (10, 11, 12) or (op in (8, 9, 13) and rs == 0):
            out.append(('/' + f, pa, x, y))
    return out

if __name__ == '__main__':
    import pickle
    port = pickle.load(open(os.path.join(ROOT, 'work', 'port_usa.pkl'), 'rb'))
    P = patches(port, sys.argv[1], sys.argv[2])
    print(len(P), 'mots')
