# Big Air Master: JUMP AT MAX (part of the mod `bam`, v82; REMIX screen, tab AIR, on by default).
#
# The Big Air Master (TM.BIN) has no BOARDER screen: the player is always Yaggi, with his own stats (the rider MAX of
# the mod max is not applied there since v81). This switch gives him the best jump of the game instead: the first word
# of the rider's parameter row (16 bytes per rider, TM's table D_80094300, the same as the other overlays') is the jump
# power (4096 Yaggi, 3072 Jin / Cindy / Snowman, 3584 Irin, 5120 Boss / Gray: exactly the JUMP bars of the BOARDER
# screen; in the emulator 8192 instead of 4096 gave 105 frames in the air instead of 58, the other fields changed
# nothing). TM's racer setup (0x80063C38: addu v0, v0, v1 = the row's address, then sw v0, 0x54(s0)) goes through `jmx`,
# which writes JUMP_MAX into the row while bit 0 of the saved switches word is clear (bit set =
# off, as the other switches; bit 0 was until v80 a working copy of the REAR VIEW, now in the unsaved byte 0x8005744E).
# TM is read from the disc each time the mode starts, so the row is the original one again with the switch off.
# Code in the dead function func_8007EDA4 of TM, after bamlive's.
import struct
from asm import asm

OVL = 0x8005AEA8
SITE = 0x80063C38
JMX = 0x8007F3C0                     # (bamlive's code ends at 0x8007EF68; the dead function at 0x8007F410)
FLAGS, BIT = 0x80057438, 0
JUMP_MAX = 8192                      # twice Yaggi's: 5120 (Boss's, the game's best) gave little more air (56 / 30 / 32 frames
                                     # in the air against 62 / 50 / 42 with 8192, same falls), not the time for a trick


def ops(disc):
    tm = disc.read_file('/TM.BIN'); w = lambda a: struct.unpack_from('<I', tm, a - OVL)[0]
    assert w(SITE) == 0x00431021 and w(SITE + 4) == 0xAE020054, (hex(w(SITE)), hex(w(SITE + 4)))
    c, _ = asm(['jmx:', 'addu v0, v0, v1', 'lui at, 0x8005', f'lbu at, {FLAGS & 0xffff:#x}(at)', 'nop', f'andi at, at, {1 << BIT}',
                'bnez at, jm9', f'addiu at, zero, {JUMP_MAX}', 'sw at, 0(v0)', 'jm9:', 'jr ra', 'sw v0, 0x54(s0)'], JMX)
    assert c[-1][0] < 0x8007F410
    out = [['w', '/TM.BIN', a - OVL, w(a), x] for a, x in c]
    out.append(['w', '/TM.BIN', SITE - OVL, w(SITE), (3 << 26) | ((JMX >> 2) & 0x3ffffff)])
    return out


def merge(disc, bam_ops):
    new = ops(disc); keys = {(op[1], op[2]) for op in new}
    return [op for op in bam_ops if not (op[0] == 'w' and (op[1], op[2]) in keys)] + new
