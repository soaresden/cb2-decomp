# Rear view (mod `rear`, v26): Circle held in a race = the camera looks back.
#
# The races draw everything through the libgs world-screen matrix (GsWSMATRIX, exe 0x80058E20, and its work copy at
# 0x80059220), set each frame by the race camera through GsSetView2 (exe 0x80030984). The view is relative to the
# rider: the origin of the world is the rider (translation of the matrix = where the rider is for the camera).
# While Circle (pad 0x8004FBF0, bit 0x20) is held in a race overlay (word 0 of the overlay = 8, ENDING excepted), the
# end of GsSetView2 turns both matrices by 180 degrees around the camera's own vertical axis through the rider (rows
# X and Z negated): the camera goes round the rider, in front of him, and looks back with the same angle to the slope
# (the race camera follows the slope: 0..5 degrees on flat ground, up to ~34 in the descents). v26 turned them around
# the world's vertical axis (columns negated): in the steep descents the camera, in front and still looking down,
# showed the snow instead of the rider and the slope behind him (v33).
# Hook: "addu v0, zero, zero" after the copy into GsWSMATRIX (its delay slot is the next instruction, a register
# reload: ra is kept in t3 around the calls), the code comes back right after.
import struct
from asm import asm

FN = 0x80030984; HOOK = 0x80030F6C; BACK = 0x80030F74     # GsSetView2: after the copy into GsWSMATRIX
CAVE = 0x800280B8; CAVE_END = 0x8002815C          # dead functions of the exe (never called, no pointer to them)
CAVE2 = 0x8002E7D0; CAVE2_END = 0x8002E864
WS = 0x80058E20; WORK = 0x80059220
ENDING_W1 = 0x27BDCAB0
OPT_FLAGS, OPT_BIT = 0x80057438, 1          # in-game options (mod options): bit set = rear view off


def code():
    S = ['rv:', 'lui t0, 0x8005', f'lbu t2, {OPT_FLAGS & 0xffff:#x}(t0)', 'lw t1, -0x410(t0)', f'andi t2, t2, {OPT_BIT}', 'bnez t2, rv9', 'andi t1, t1, 0x20', 'beqz t1, rv9',
         'lui t0, 0x8006', 'lw t1, -0x5158(t0)', 'addiu t2, zero, 8', 'bne t1, t2, rv9',
         'lw t1, -0x5154(t0)', f'lui t2, {ENDING_W1 >> 16:#x}', f'ori t2, t2, {ENDING_W1 & 0xffff:#x}', 'beq t1, t2, rv9',
         'move t3, ra', f'lui t0, {(WS + 0x8000) >> 16:#x}', f'addiu t0, t0, {WS - (((WS + 0x8000) >> 16) << 16)}', 'jal rvf', 'nop',
         f'lui t0, {(WORK + 0x8000) >> 16:#x}', f'addiu t0, t0, {WORK - (((WORK + 0x8000) >> 16) << 16)}', 'jal rvf', 'nop', 'move ra, t3',
         'rv9:', f'j {BACK}', 'move v0, zero']
    # rvf: negate rows 0 and 2 of the MATRIX at t0 (3x3 s16, rows of 3), t1 scratch
    F = ['rvf:']
    for o in (0, 2, 4, 0xC, 0xE, 0x10):
        F += [f'lh t1, {o}(t0)', 'nop', 'subu t1, zero, t1', f'sh t1, {o}(t0)']
    F += ['jr ra', 'nop']
    c2, l2 = asm(F, CAVE2)
    c, l = asm(S, CAVE, l2); l.update(l2)
    assert c[-1][0] < CAVE_END and c2[-1][0] < CAVE2_END
    return c + c2, l


def patches(exe):
    """-> [(address, old word, new word)] in the exe"""
    old = lambda a: struct.unpack_from('<I', exe, a - 0x8000F800)[0]
    assert old(HOOK) == 0x00001021 and old(HOOK + 4) == 0x8FBF00B0, hex(old(HOOK))   # addu v0, zero, zero / lw ra, 0xb0(sp)
    c, l = code()
    return [(a, old(a), w) for a, w in c] + [(HOOK, old(HOOK), (2 << 26) | ((l['rv'] >> 2) & 0x3ffffff))]


def ops(disc):
    exe = disc.read_file('/SCES_009.92')
    return [['w', '/SCES_009.92', a - 0x8000F800, o, n] for a, o, n in patches(exe)]
