# Competition: skip the qualifying stage (mod `skipq`, v25).
#
# Each round of the Tour Competition is "1st STAGE" (the qualifying trick event, overlay SBC1, mode 0x80057420 = 0)
# then "2nd STAGE" Boarder Cross (SBC2, mode 1). The Boarder Cross starts as a handicap race: every rider of the
# roster (8 entries of 0xA8 bytes at 0x80057464, indexed by rider) has a start gap at +0x8E (halfword, 1/100 s)
# and the same x10 at +0x90 (word), written by SBC1 from the qualifying ranking (best = 0, last = about 22 s).
#
# Here, SBC1 runs its stage through func_80062804 (the event, the results) and then handles the end of the stage by
# mode. The choice is the player's, on the "1st STAGE" screen: START = play the qualifying as usual, SELECT held
# while pressing START = skip it. When the mode is 0 (competition qualifying) and SELECT is held (pad 0x8004FBF0,
# bit 0x100), that call is replaced: the gaps are written
# directly (the player gets the 4th one, the CPU riders the others, rotated each round), the qualifying scores are set
# to 0, the stage counter (0x8005745C) goes up by one and the course of the stage (0x8005741C) becomes the round's
# course (0x80057458), as after a played stage, and the call "returns" exit code 3: SBC1's own end-of-stage code then
# goes to the Boarder Cross (mode 1, its files queued by the game). See docs/competition.md.
# Code in func_800291CC of the exe (never referenced).
from asm import asm

SK = 0x800291CC; SK_END = 0x8002934C
HOOK = 0x8005B058; HOOK_OLD = 0x0C018A01          # SBC1: jal func_80062804 (the stage), exit code in v0
GAPS = [0, 400, 790, 1150, 1370, 1580, 1820, 2220]  # 1/100 s, as the game's own gaps for ranks 1..8
PLAYER_SLOT = 3                                      # 4th
CPU_SLOTS = [s for s in range(8) if s != PLAYER_SLOT]
JL = lambda t: (3 << 26) | ((t >> 2) & 0x3ffffff)


def code():
    data = SK_END - 0x20     # 16 bytes of gaps (halfwords) + 7 slots
    hi = (data + 0x8000) >> 16; lo = data - (hi << 16)
    L = ['skq:', 'lui t1, 0x8005', 'lw t2, 0x7420(t1)', 'lw t9, -0x410(t1)', 'bnez t2, run', 'andi t9, t9, 0x100',
         'beqz t9, run', 'nop',
         'lh t3, 0x7408(t1)', 'lw t4, 0x7458(t1)', 'addiu t5, t1, 0x7464', 'move t6, zero', 'move t7, zero',
         'lp:', 'beq t6, t3, pl', 'nop',
         'addu t8, t7, t4', 'm7:', 'slti t9, t8, 7', 'bnez t9, m7d', 'nop', 'j m7', 'addiu t8, t8, -7',
         'm7d:', f'lui t9, {hi}', 'addu t9, t9, t8', f'lbu t8, {lo + 16}(t9)', 'j sg', 'addiu t7, t7, 1',
         'pl:', f'addiu t8, zero, {PLAYER_SLOT}',
         'sg:', 'sll t8, t8, 1', f'lui t9, {hi}', 'addu t9, t9, t8', f'lhu t9, {lo}(t9)', 'nop',
         'sh t9, 0x8e(t5)', 'sll t8, t9, 2', 'addu t8, t8, t9', 'sll t8, t8, 1', 'sw t8, 0x90(t5)', 'sh zero, 2(t5)', 'sh zero, 4(t5)',
         'addiu t6, t6, 1', 'slti t9, t6, 8', 'bnez t9, lp', 'addiu t5, t5, 0xa8',
         'lw t0, 0x745c(t1)', 'sh t4, 0x741c(t1)', 'addiu t0, t0, 1', 'sw t0, 0x745c(t1)',
         'jr ra', 'addiu v0, zero, 3',
         'run:', 'j 0x80062804', 'nop']
    c, l = asm(L, SK)
    assert c[-1][0] < data, hex(c[-1][0])
    import struct
    blob = b''.join(struct.pack('<H', g) for g in GAPS) + bytes(CPU_SLOTS) + bytes(16 - len(CPU_SLOTS))
    c += [(data + i, struct.unpack_from('<I', blob, i)[0]) for i in range(0, len(blob), 4)]
    return c, l


def patches(exe, sbc1):
    import struct
    c, l = code()
    old = lambda a: struct.unpack_from('<I', exe, a - 0x8000f800)[0]
    assert struct.unpack_from('<I', sbc1, HOOK - 0x8005AEA8)[0] == HOOK_OLD
    return [('/SCES_009.92', a, old(a), w) for a, w in c] + [('/SBC1.BIN', HOOK, HOOK_OLD, JL(l['skq']))]
