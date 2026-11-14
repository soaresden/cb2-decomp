# Big Air Master: STOP in the pause menu (part of the mod `bam`, v52).
#
# The session lasts 60 s: TM counts its game frames in D_8009B954 (25 a second, -1 while the session has not started:
# the practice run) and ends it at 0x5DC (1500 frames): "YOUR GRADE IS ...", then the TRICK MASTER ranking. The pause
# menu (Continue / Restart / Exit) writes its choice to D_8009B950 (Exit = 3) through `bx` (exe 0x8002934C, remix.py:
# until v51 it answered 5, the finish code, in the Master mode). Now, with the session running, `bx`
# sets the counter to 0x5DC and returns to the menu's Continue (the pause closes): the game ends the session itself, as when the time is up. In the
# practice run (counter -1) it exits as before (3). (Only TM calls bx.) The pause label "Exit" becomes "Stop".
# `bx` runs in the delay of the pause handler's `lui at, 0x800A`: `at` is left alone.
import struct
from asm import asm

EXE_BASE, OVL = 0x8000F800, 0x8005AEA8
BX, BX_END = 0x8002934C, 0x80029370            # 9 words: the mod air's code follows
TIMER, LIMIT = 0x8009B954, 0x5DC
EXIT_STR = 0x8009225C
CONTINUE = 0x8005CCE8


def ops(disc):
    ex = disc.read_file('/SCES_009.92'); tm = disc.read_file('/TM.BIN')
    we = lambda a: struct.unpack_from('<I', ex, a - EXE_BASE)[0]
    # STOP: back to the menu's Continue path (0x8005CCE8: the pause closes) instead of the store of the choice
    c, _ = asm(['bx:', 'lui t0, 0x800a', f'lw t1, {TIMER - 0x800A0000}(t0)', 'lui t2, 0x8006', 'bltz t1, bx9',
                f'addiu t1, zero, {LIMIT}', f'sw t1, {TIMER - 0x800A0000}(t0)', f'addiu ra, t2, {CONTINUE - 0x80060000}',
                'bx9:', 'jr ra', 'addiu v0, zero, 3'], BX)
    assert c[-1][0] < BX_END
    assert tm[EXIT_STR - OVL:EXIT_STR - OVL + 5] == b'Exit\0'
    out = [['w', '/SCES_009.92', a - EXE_BASE, we(a), x] for a, x in c]
    o = EXIT_STR - OVL
    out.append(['w', '/TM.BIN', o, struct.unpack_from('<I', tm, o)[0], struct.unpack('<I', b'Stop')[0]])
    return out


def merge(disc, bam_ops):
    new = ops(disc); keys = {(op[1], op[2]) for op in new}
    return [op for op in bam_ops if not (op[0] == 'w' and (op[1], op[2]) in keys)] + new
