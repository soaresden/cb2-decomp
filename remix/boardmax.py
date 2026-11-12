# Board MAX as a line of the BOARD screen (mod `max`, v24).
#
# BOARD screen (MAIN_SEL func_8006B2D0): under the last line of the style (SPECIAL, or TYPE-3 while the SPECIAL is
# locked) a "MAX" line. Down on the last line selects it (the game itself does not move there), Up leaves it (Up is
# taken from the pad while MAX is selected, and until it is released, so the game's cursor stays put). While it is
# selected the game's own type label is drawn unselected (the "original board" test of the label loop answers yes).
# Selected = FLAGB (the flag the race-entry hook already reads to give the player's board the MAX row).
#
# DESIGN screen (func_8006CED4): while MAX is selected, Left / Right go through the 21 designs of the game
# (0..17 = the 6 of each style, 18..20 = the SPECIAL ones) instead of the 6 of the style; the carousel shows the
# neighbours from the whole list; the "MAX" label stays on screen. The design number is global in the game: a race
# loads design n of BOARD.DAT whatever the board (checked in the emulator), so nothing else is needed.
#
# Code and data in func_8001B774 of the exe (never referenced), FLAGB in the board MAX block (func_8002815C).
import os, struct
from asm import asm

DZ3 = 0x8001B774; DZ3_END = 0x8001BA70
RAWP = DZ3; MASKV = DZ3 + 4; STR_D = DZ3 + 8; CODE = DZ3 + 0x1c
TXT_D = b'MAX : 21 DESIGNS'
E = lambda k, d: int(os.environ.get(k, d))
LX, LY, W = E('BM_LX', '140'), E('BM_LY', '200'), E('BM_W', '27')       # MAX line: the "MAX" of the MAXSPEED label
TX, TY = E('BM_TX', '112'), E('BM_TY', '84')                          # DESIGN screen: next to the type label
DX, DY, DF = E('BM_DX', '10'), E('BM_DY', '236'), E('BM_DF', '1')     # DESIGN screen hint text
RGB_OFF, RGB_ON = E('BM_OFF', str(0x484848)), E('BM_ON', str(0x2080e0))
MSP = CODE                                                            # first routine of the block (fixed address)
ACT = 0x8002a030   # pad hook countdown (remix.py: ACT = DZ2)
hi = lambda a: ((a + 0x8000) >> 16) & 0xffff
lo = lambda a: a - (((a + 0x8000) >> 16) << 16)
JL = lambda t: (3 << 26) | ((t >> 2) & 0x3ffffff)


def maxb(FL, ED, hb):
    """BOARD screen hook (replaces jal func_8005CC78 in the 3 label loops): the game's call, then the MAX line
    logic for player 1 and its label. FL / ED: lo() of FLAGB / previous raw pad, relative to hb."""
    return [
        'maxb:', 'addiu sp, sp, -0x30', 'sw ra, 0x2c(sp)', 'lw t0, 0x40(sp)', 'nop', 'jal 0x8005cc78', 'sw t0, 0x10(sp)',
        'sw v0, 0x28(sp)',
        'lui at, 0x8003', 'addiu t2, zero, 8', f'sw t2, {lo(ACT)}(at)',
        f'lui at, {hi(RAWP)}', f'lw t1, {lo(RAWP)}(at)',
        f'lui at, {hb}', f'lw t3, {ED}(at)', f'sw t1, {ED}(at)', 'nor t3, t3, zero', 'and t3, t1, t3',
        f'lw t4, {FL}(at)', 'lui t5, 0x8008', 'lh t6, -0x2fc4(t5)', 'bnez t4, bm_on', 'nop',
        'andi t7, t3, 0x4000', 'beqz t7, bm_mask', 'nop',
        'lh t7, -0x2fc0(t5)', 'addiu t8, zero, 0x17', 'beq t7, t8, bm_mask', 'andi t7, t6, 3',
        'addiu t8, zero, 3', 'beq t7, t8, bm_go', 'addiu t8, zero, 2', 'bne t7, t8, bm_mask', 'sra t8, t6, 2',
        'lui t9, 0x8005', 'lhu t9, 0x7442(t9)', 'nop', 'srlv t9, t9, t8', 'andi t9, t9, 1', 'bnez t9, bm_mask', 'nop',
        'bm_go:', 'addiu t4, zero, 1', 'j bm_mask', f'sw t4, {FL}(at)',
        'bm_on:', 'andi t7, t3, 0x1000', 'beqz t7, bm_mask', 'nop', f'sw zero, {FL}(at)',
        'bm_mask:', f'lw t4, {FL}(at)', f'lui t5, {hi(MASKV)}', f'lw t7, {lo(MASKV)}(t5)', 'andi t8, t1, 0x1000',
        'bnez t4, bm_m1', 'addiu t9, zero, 0x1000', 'beqz t7, bm_m0', 'nop', 'bnez t8, bm_m1', 'nop',
        'bm_m0:', 'move t9, zero', 'bm_m1:', f'sw t9, {lo(MASKV)}(t5)',
        # y: under SPECIAL, or one line higher (under TYPE-3) while the SPECIAL of this style is locked
        'lui t5, 0x8008', 'lh t6, -0x2fc4(t5)', 'lui t9, 0x8005', 'lhu t9, 0x7442(t9)', 'sra t8, t6, 2', 'srlv t9, t9, t8', 'andi t9, t9, 1',
        f'addiu a3, zero, {LY}', 'bnez t9, bm_y', 'nop', f'addiu a3, zero, {LY - 22}',
        'bm_y:', 'move a0, s5', 'lw a1, 0x28(sp)', f'jal {MSP}', f'addiu a2, zero, {LX}',
        'lw ra, 0x2c(sp)', 'nop', 'jr ra', 'addiu sp, sp, 0x30']


def code(F):
    """design screen + label helpers, F = address of FLAGB"""
    ld = [f'lui at, {hi(F)}', f'lw at, {lo(F)}(at)', 'nop']
    # msp(a0 ot, a1 prim, a2 x, a3 y, t4 selected): the MAXSPEED label of the screen (sprite id D_8007D048[0]),
    # cut to its first W pixels ("MAX"), tinted orange when selected, grey otherwise -> v0 = next prim
    L = ['msp:', 'addiu sp, sp, -0x28', 'sw ra, 0x24(sp)', 'sw t4, 0x20(sp)', 'lui t0, 0x8008', 'lh t0, -0x2fb8(t0)', 'nop', 'jal 0x8005cc78', 'sw t0, 0x10(sp)',
         'lh t0, -0x20(v0)', 'lbu t1, -0x1c(v0)', f'addiu t0, t0, {W}', f'addiu t1, t1, {W}', 'sh t0, -0x18(v0)', 'sh t0, -0x8(v0)', 'sb t1, -0x14(v0)', 'sb t1, -0x4(v0)',
         'lw t4, 0x20(sp)', f'lui t0, {RGB_OFF >> 16}', f'ori t0, t0, {RGB_OFF & 0xffff}', 'beqz t4, ms1', 'nop', f'lui t0, {RGB_ON >> 16}', f'ori t0, t0, {RGB_ON & 0xffff}',
         'ms1:', 'sb t0, -0x24(v0)', 'srl t1, t0, 8', 'sb t1, -0x23(v0)', 'srl t1, t0, 16', 'sb t1, -0x22(v0)',
         'lw ra, 0x24(sp)', 'nop', 'jr ra', 'addiu sp, sp, 0x28']
    L += ['cbt:', *ld, 'beqz at, cb8', 'nop', 'addiu t0, zero, 10', 'cb8:', 'sll v0, t0, 3', 'jr ra', 'addu v0, v0, t0']
    L += ['cbar:', 'lh v0, 0(v0)', *ld, 'beqz at, cb9', 'nop', 'addiu v0, zero, 10', 'cb9:', 'jr ra', 'nop']
    L += ['cinc:', 'sll v1, v1, 1', 'addiu v0, v1, 5', *ld, 'beqz at, ci9', 'nop', 'move v1, zero', 'addiu v0, zero, 20', 'ci9:', 'jr ra', 'nop']
    L += ['cdec:', 'sll v1, v1, 1', *ld, 'bnez at, cd1', 'nop', 'jr ra', 'slt v0, a1, v1', 'cd1:', 'slt v0, a1, zero', 'jr ra', 'addiu v1, zero, 15']
    L += ['cin:', 'lh v0, 0(s4)', *ld, 'beqz at, cn9', 'nop', 'move v0, zero', 'cn9:', 'jr ra', 'nop']
    for r in ('s4', 's6'):
        L += [f'cld_{r}:', f'lh a0, 0({r})', *ld, 'beqz at, cl9_' + r, 'nop', 'slti at, a0, 18', 'bnez at, cl9_' + r, 'nop', 'addiu a0, a0, -6',
              'cl9_' + r + ':', 'jr ra', 'nop']
    L += ['cmod_s4:', *ld, 'beqz at, cm9', 'nop', 'j cmc', 'lh at, 0(s4)',
          'cmod_s6:', *ld, 'beqz at, cm9', 'nop', 'lh at, 0(s6)',
          'cmc:', 'sll v0, s2, 16', 'sra v0, v0, 16', 'slti a2, v0, 4', 'bnez a2, cm1', 'nop', 'addiu v0, v0, -6',
          'cm1:', 'addu v0, v0, at', 'bgez v0, cm2', 'nop', 'addiu v0, v0, 21',
          'cm2:', 'slti a2, v0, 21', 'bnez a2, cm3', 'nop', 'addiu v0, v0, -21',
          'cm3:', 'move a2, v0', 'cm9:', 'jr ra', 'sll a2, a2, 16']
    for r in ('s6', 's7'):
        L += [f'chl_{r}:', f'lh v1, 0({r})', *ld, 'beqz at, ch9_' + r, 'nop', 'addiu v1, zero, 0x17', 'ch9_' + r + ':', 'jr ra', 'nop']
    L += ['maxt:', 'addiu sp, sp, -0x30', 'sw ra, 0x2c(sp)', 'lw t0, 0x40(sp)', 'nop', 'jal 0x8005cc78', 'sw t0, 0x10(sp)',
          f'lui at, {hi(F)}', f'lw t4, {lo(F)}(at)', 'nop', 'beqz t4, mt9', 'nop',
          'move a0, s5', 'move a1, v0', f'addiu a2, zero, {TX}', 'jal msp', f'addiu a3, zero, {TY}',
          'move a0, s5', 'move a1, v0', f'lui a2, {hi(STR_D)}', f'addiu a2, a2, {lo(STR_D)}',
          f'addiu t0, zero, {DY}', 'sw t0, 0x10(sp)', 'sw zero, 0x14(sp)', f'addiu t0, zero, {DF}', 'sw t0, 0x18(sp)',
          'jal 0x8005e784', f'addiu a3, zero, {DX}',
          'mt9:', 'lw ra, 0x2c(sp)', 'nop', 'jr ra', 'addiu sp, sp, 0x30']
    return L


# MAIN_SEL sites: (address, original word, label or raw word)
def sites(l):
    J = lambda k: JL(l[k])
    return [
        (0x8006E0A8, 0x00031840, J('cinc')), (0x8006E0AC, 0x24620005, 0),
        (0x8006E120, 0x00031840, J('cdec')), (0x8006E124, 0x00A3102A, 0),
        (0x8006E1CC, 0x86820000, J('cin')),
        (0x8006D478, 0x86C40000, J('cld_s6')), (0x8006DC98, 0x86840000, J('cld_s4')), (0x8006E4B8, 0x86C40000, J('cld_s6')),
        (0x8006D614, 0x00663021, J('cmod_s6')), (0x8006D618, 0x00063400, 0x00663021),
        (0x8006DEA0, 0x00663021, J('cmod_s4')), (0x8006DEA4, 0x00063400, 0x00663021),
        (0x8006E654, 0x00663021, J('cmod_s6')), (0x8006E658, 0x00063400, 0x00663021),
        (0x8006B544, 0x86E30000, J('chl_s7')), (0x8006BCF4, 0x86C30000, J('chl_s6')), (0x8006C964, 0x86E30000, J('chl_s7')),
        (0x8006BA80, 0x84420000, J('cbar')), (0x8006C0C0, 0x84420000, J('cbar')),
        *[x for a in (0x8006D42C, 0x8006DC58, 0x8006E46C) for x in ((a, 0x000810C0, J('cbt')), (a + 4, 0x00481021, 0))],
        (0x8006D38C, 0x0C01731E, J('maxt')), (0x8006DBB8, 0x0C01731E, J('maxt')), (0x8006E3CC, 0x0C01731E, J('maxt')),
    ]


def patches(flagb, lbx, exe):
    """flagb: address of FLAGB; lbx: labels of the BZ block (unused); exe: original exe bytes"""
    c, l = asm(code(flagb), CODE)
    assert l['msp'] == MSP
    assert c[-1][0] < DZ3_END, hex(c[-1][0])
    data = bytearray(CODE - DZ3)
    data[8:8 + len(TXT_D)] = TXT_D
    words = [(DZ3 + i, struct.unpack_from('<I', data, i)[0]) for i in range(0, len(data), 4)] + list(c)
    old = lambda a: struct.unpack_from('<I', exe, a - 0x8000f800)[0]
    P = [('/SCES_009.92', a, old(a), w) for a, w in words]
    P += [('/MAIN_SEL.BIN', a, o, n) for a, o, n in sites(l)]
    return P
