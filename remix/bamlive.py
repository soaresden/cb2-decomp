# Big Air Master: the live grade and the NEXT column without the trick's name (part of the mod `bam`, v53).
#
# The grade at the end of a session (func_8007461C): g = min(max(level - 1, 0) / 2, 10), level = D_8009CF10 (the
# number of the trick to do); TM's func_800893C4 unlocks Gray when 10 - g = 0, i.e. from the 21st trick on.
# Here, under TIME / COOL / UNCOOL: "GRADE g/10" and "GRAY IN n" (tricks to go) or "GRAY OK!" while the session runs,
# so that the player knows when Stop (remix/bamstop.py) is enough for Gray.
# NEXT column (remix.py `tl`, which draws the trick box of the next trick with 0x800756DC): its call goes through
# `nxw`, which raises FLAG around it; the trick box's call of the name line (0x80075908, jal func_8006A820) goes
# through `nnm`, which skips it while FLAG is up: the next trick shows its keys only. `nxw` then prints the grade lines
# with the game's font print (0x8008FFF4) into the ordering-table slot after tl's (tl moves what is linked into its own).
# Code and data in the dead function func_8007EDA4 of TM.
import struct
from asm import asm

OVL = 0x8005AEA8
CAVE, CAVE_END = 0x8007EDA4, 0x8007EDA4 + 0x66C
NAME_SITE, NAME_FN, BOX = 0x80075908, 0x8006A820, 0x800756DC
LEVEL = 0x8009CF10
FONT_PRINT = 0x8008FFF4
GX, GY, GDY = -152, -60, 12
TL, TL_END = 0x800953B0, 0x800953B0 + 0x1E8


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)
def J(op, t): return (op << 26) | ((t >> 2) & 0x3ffffff)


def code():
    D = CAVE                     # data: FLAG, RA, STR1 (12), STR2 (12), STR3 (12)
    FLAG, RA, S1, S2, S3 = D, D + 4, D + 8, D + 20, D + 32
    data = struct.pack('<II', 0, 0) + b'GRADE 00/10\0' + b'GRAY IN 00\0\0' + b'GRAY OK!\0\0\0\0'
    la = lambda r, a: [f'lui {r}, {H(a)}', f'addiu {r}, {r}, {L(a)}']
    pr = lambda s, y: ['addiu a0, s5, 4', 'lui a1, 0x800a', 'lw a1, -0x2084(a1)', *la('a2', s), f'addiu a3, zero, {GX}',
                       f'addiu t0, zero, {y}', 'sw t0, 0x10(sp)', f'jal {FONT_PRINT}', 'sw zero, 0x14(sp)']
    S = ['nxw:', f'lui t0, {H(D)}', f'sw ra, {L(RA)}(t0)', 'addiu t1, zero, 1', f'sw t1, {L(FLAG)}(t0)',
         f'jal {BOX}', 'nop', f'lui t0, {H(D)}', f'sw zero, {L(FLAG)}(t0)', 'addiu sp, sp, -0x20',
         f'lui t1, {H(LEVEL)}', f'lh t1, {L(LEVEL)}(t1)', 'nop', 'sw t1, 0x18(sp)', 'addiu t2, t1, -1', 'bgez t2, g1', 'nop', 'move t2, zero',
         'g1:', 'sra t2, t2, 1', 'slti at, t2, 11', 'bnez at, g2', 'nop', 'addiu t2, zero, 10',
         'g2:', *la('t3', S1 + 6), 'addiu t4, zero, 10', 'divu t2, t4', 'mflo t5', 'mfhi t6', 'addiu t5, t5, 0x30', 'addiu t6, t6, 0x30',
         'addiu t7, zero, 0x30', 'bne t5, t7, g3', 'nop', 'addiu t5, zero, 0x20', 'g3:', 'sb t5, 0(t3)', 'sb t6, 1(t3)',
         *pr(S1, GY),
         'lw t1, 0x18(sp)', 'addiu t7, zero, 21', 'subu t7, t7, t1', 'blez t7, g5', 'nop',
         *la('t3', S2 + 8), 'addiu t4, zero, 10', 'divu t7, t4', 'mflo t5', 'mfhi t6', 'addiu t5, t5, 0x30', 'addiu t6, t6, 0x30',
         'addiu t4, zero, 0x30', 'bne t5, t4, g4', 'nop', 'addiu t5, zero, 0x20', 'g4:', 'sb t5, 0(t3)', 'sb t6, 1(t3)',
         *pr(S2, GY + GDY), 'j g6', 'nop',
         'g5:', *pr(S3, GY + GDY),
         'g6:', 'addiu sp, sp, 0x20', f'lui t0, {H(D)}', f'lw ra, {L(RA)}(t0)', 'nop', 'jr ra', 'nop',
         'nnm:', f'lui t0, {H(D)}', f'lw t0, {L(FLAG)}(t0)', 'nop', 'bnez t0, nn9', 'nop', f'j {NAME_FN}', 'nop', 'nn9:', 'jr ra', 'nop']
    c, l = asm(S, D + len(data))
    assert c[-1][0] < CAVE_END
    words = [(D + i, struct.unpack_from('<I', data, i)[0]) for i in range(0, len(data), 4)] + c
    return words, l


def merge(disc, bam_ops):
    tm = disc.read_file('/TM.BIN'); w = lambda a: struct.unpack_from('<I', tm, a - OVL)[0]
    assert w(NAME_SITE) == J(3, NAME_FN)
    words, l = code()
    keys = {a for a, _ in words} | {NAME_SITE}
    out = [op for op in bam_ops if not (op[0] == 'w' and op[1] == '/TM.BIN' and op[2] + OVL in keys)]
    # tl's second call of the trick box (the NEXT entry) -> nxw
    calls = sorted(op[2] + OVL for op in out if op[0] == 'w' and op[1] == '/TM.BIN' and TL <= op[2] + OVL < TL_END
                   and op[4] in (J(3, BOX), J(3, l['nxw'])))
    assert len(calls) == 2, [hex(a) for a in calls]
    for op in out:
        if op[0] == 'w' and op[1] == '/TM.BIN' and op[2] + OVL == calls[1]: op[4] = J(3, l['nxw'])
    out += [['w', '/TM.BIN', a - OVL, w(a), x] for a, x in words] + [['w', '/TM.BIN', NAME_SITE - OVL, w(NAME_SITE), J(3, l['nnm'])]]
    return out
