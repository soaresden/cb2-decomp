# Stats MAX in the rider's pose (part of the mod `max`, v49).
#
# On the BOARDER screen, R1 puts every stat bar at 10 (remix.py `maxd`, hooked into the bars loop at MAIN_SEL
# 0x800614B8). After the outfit is chosen, the rider strikes a pose and says his line: those frames draw the bars
# with two other copies of the same loop (0x80061300 and 0x80061910: "lh a0, 0(a1)" reads the stat of the table
# D_8007B328), and the still bars of the pose with four "addu v0, s2, v0 / lh v1, 0(v0)" (0x800644B4, 0x8006450C,
# 0x8006484C, 0x800648A4), so the bars went back to the rider's own values. All go through `maxv` / `maxw`: the stat, or 10 while
# MAX is on (FLAG). Uses at and a0 only, like the load it replaces (the loop keeps t0/t1/a1..a3/v1 live).
# Code at the end of the dead function that holds the MAX code (0x8002957C..0x8002979F, remix.py).
import struct
from asm import asm

EXE_BASE = 0x8000F800
FLAG = 0x8002957C                         # remix.py: FLAG = DZ
MAXV = 0x80029690
SITES = [0x80061300, 0x80061910]          # MAIN_SEL: lh a0, 0(a1)
LH = 0x84A40000
SITES_V1 = [0x800644B4, 0x8006450C, 0x8006484C, 0x800648A4]   # MAIN_SEL: addu v0, s2, v0 / lh v1, 0(v0) (still bars)
ADDU, LH_V1 = 0x02421021, 0x84430000
OVL = 0x8005AEA8


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)


def ops(disc):
    ex = disc.read_file('/SCES_009.92'); ms = disc.read_file('/MAIN_SEL.BIN')
    we = lambda a: struct.unpack_from('<I', ex, a - EXE_BASE)[0]
    wm = lambda a: struct.unpack_from('<I', ms, a - OVL)[0]
    c, l = asm(['maxv:', 'lh a0, 0(a1)', f'lui at, {H(FLAG)}', f'lw at, {L(FLAG)}(at)', 'nop', 'beqz at, mv1', 'nop',
                'addiu a0, zero, 10', 'mv1:', 'jr ra', 'nop',
                'maxw:', 'addu v0, s2, v0', 'lh v1, 0(v0)', f'lui at, {H(FLAG)}', f'lw at, {L(FLAG)}(at)', 'nop', 'beqz at, mw1', 'nop',
                'addiu v1, zero, 10', 'mw1:', 'jr ra', 'nop'], MAXV)
    assert c[-1][0] < 0x800297A0
    out = [['w', '/SCES_009.92', a - EXE_BASE, we(a), x] for a, x in c]
    for s in SITES:
        assert wm(s) == LH, hex(wm(s))
        out.append(['w', '/MAIN_SEL.BIN', s - OVL, LH, (3 << 26) | ((MAXV >> 2) & 0x3ffffff)])
    for s in SITES_V1:      # inside a pending mult: maxw leaves HI / LO alone; the load moves into maxw (the word after
        # it, now the delay slot of its jal, would have run first: "addiu v0, zero, 1" at two of the sites), a nop instead
        assert wm(s) == ADDU and wm(s + 4) == LH_V1, hex(wm(s))
        out.append(['w', '/MAIN_SEL.BIN', s - OVL, ADDU, (3 << 26) | ((l['maxw'] >> 2) & 0x3ffffff)])
        out.append(['w', '/MAIN_SEL.BIN', s + 4 - OVL, LH_V1, 0])
    return out


def merge(disc, max_ops):
    """the mod max's operations with these (earlier ones of this module replaced)"""
    new = ops(disc); keys = {(op[1], op[2]) for op in new}
    return [op for op in max_ops if not (op[0] == 'w' and (op[1], op[2]) in keys)] + new
