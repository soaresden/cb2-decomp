# Half-pipe judges live (mod `hplive`, v26): during the run, the five judges' marks and the total are shown at the top
# right, drawn by the game's own score panel routines (the panel of the end of the run).
#
# HP.BIN: the score comes from accumulators of the run (D_8009AC48..D_8009AC6B), turned into five marks of 0..100 tenths
# by func_8006A81C (total) / func_8006A5C4 (panel): standard = AC5C / 20, rotation = (min(AC5E, 7000) + AC60) / 95,
# amplitude = AC62 / 8, landing = min(AC48 * 10, 100) - AC64, technical = min(sum / 4, 100) - 3 (AC68 + AC69 + AC6A + AC6B)
# (each one 0..100). The panel draws one line with func_80086E50 (OT, prim, line, mark, x, y) and the total with
# func_800871B8 (OT, prim, total, x + 16, y + 92); OT entry = *(*(D_8009BE4C) + 4) + 0xC, primitives at D_80058E0C.
# Hook: the main loop's per-frame call of func_800757EC (0x8005C2FC) -> hpj (dead function func_8006AFFC), which calls
# it, then draws.
import struct
from asm import asm

OVL = 0x8005AEA8
HOOK, HOOK_FN = 0x8005C2FC, 0x800757EC
CAVE, CAVE_END = 0x8006AFFC, 0x8006B3E0             # dead functions of HP.BIN (no call, jump or pointer to them)
LINE_FN, TOTAL_FN = 0x80086E50, 0x800871B8
FRAME, PRIMS = 0x8009BE4C, 0x80058E0C
OPT_FLAGS, OPT_BIT = 0x80057438, 2          # in-game options (mod options): bit set = live marks off
X, Y, DY, TY = 112, 28, 12, 70
BOX = (X - 6, Y - 5, 320 - (X - 6) - 4, TY + 22)      # translucent dark box behind (x, y, w, h)
DRAW_MODE = 0xE1000400 | (320 >> 6)                   # GetTPage(4 bits, 0, 320, 0), as func_80086A9C                       # screen: lines from (X, Y) every DY; total line TY below


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)


def code():
    S = ['hpj:', 'addiu sp, sp, -0x48', 'sw ra, 0x44(sp)', 'sw s0, 0x30(sp)', 'sw s1, 0x34(sp)', 'sw s2, 0x38(sp)', 'sw s3, 0x3c(sp)',
         f'jal {HOOK_FN}', 'nop', 'sw v0, 0x40(sp)', 'lui t0, 0x8005', f'lbu t0, {OPT_FLAGS & 0xffff:#x}(t0)', 'nop', f'andi t0, t0, {OPT_BIT}', 'bnez t0, hpx', 'nop',
         f'lui s3, {H(0x8009AC48)}']
    # marks at 0x18.. 0x28(sp): standard, amplitude, landing, rotation, technical (as the panel's lines 0..4)
    S += [f'lh t0, {L(0x8009AC5C)}(s3)', 'lui at, 0x6666', 'ori at, at, 0x6667', 'mult t0, at', 'sra t1, t0, 31', 'mfhi t2', 'sra t2, t2, 3', 'subu t2, t2, t1']
    S += ['slti at, t2, 101', 'bnez at, hs0', 'nop', 'addiu t2, zero, 100', 'hs0:', 'sw t2, 0x18(sp)']
    S += [f'lh t0, {L(0x8009AC5E)}(s3)', 'nop', 'slti at, t0, 7001', 'bnez at, ha0', 'nop', 'addiu t0, zero, 7000', 'ha0:',
          f'lh t1, {L(0x8009AC60)}(s3)', 'nop', 'addu t0, t0, t1', 'lui at, 0xac76', 'ori at, at, 0x9185', 'mult t0, at', 'sra t1, t0, 31',
          'mfhi t2', 'addu t2, t2, t0', 'sra t2, t2, 6', 'subu t2, t2, t1', 'slti at, t2, 101', 'bnez at, ha1', 'nop', 'addiu t2, zero, 100',
          'ha1:', 'sw t2, 0x24(sp)']
    S += [f'lh t0, {L(0x8009AC62)}(s3)', 'nop', 'bgez t0, hr0', 'nop', 'addiu t0, t0, 7', 'hr0:', 'sra t2, t0, 3', 'slti at, t2, 101', 'bnez at, hr1',
          'nop', 'addiu t2, zero, 100', 'hr1:', 'sw t2, 0x1c(sp)']
    S += [f'lh t0, {L(0x8009AC48)}(s3)', 'nop', 'sll t1, t0, 2', 'addu t1, t1, t0', 'sll t1, t1, 1', 'slti at, t1, 101', 'bnez at, hl0', 'nop',
          'addiu t1, zero, 100', 'hl0:', f'lh t0, {L(0x8009AC64)}(s3)', 'nop', 'subu t1, t1, t0', 'bgez t1, hl1', 'nop', 'move t1, zero',
          'hl1:', 'sw t1, 0x20(sp)']
    S += ['lw t0, 0x18(sp)', 'lw t1, 0x1c(sp)', 'lw t2, 0x20(sp)', 'lw t3, 0x24(sp)', 'addu t0, t0, t1', 'addu t0, t0, t2', 'addu t0, t0, t3',
          'bgez t0, ht0', 'nop', 'addiu t0, t0, 3', 'ht0:', 'sra t0, t0, 2', 'slti at, t0, 101', 'bnez at, ht1', 'nop', 'addiu t0, zero, 100',
          'ht1:', f'lbu t1, {L(0x8009AC68)}(s3)', f'lbu t2, {L(0x8009AC69)}(s3)', f'lbu t3, {L(0x8009AC6A)}(s3)', f'lbu t4, {L(0x8009AC6B)}(s3)',
          'addu t1, t1, t2', 'addu t1, t1, t3', 'addu t1, t1, t4', 'sll t2, t1, 1', 'addu t1, t1, t2', 'subu t0, t0, t1', 'bgez t0, ht2', 'nop',
          'move t0, zero', 'ht2:', 'sw t0, 0x28(sp)']
    # OT entry and primitives
    S += [f'lui t0, {H(FRAME)}', f'lw t0, {L(FRAME)}(t0)', 'nop', 'lw s1, 4(t0)', f'lui t0, {H(PRIMS)}', f'lw s2, {L(PRIMS)}(t0)', 'addiu s1, s1, 0xc',
          'move s0, zero',
          'hln:', 'move a0, s1', 'move a1, s2', 'move a2, s0', 'sll t0, s0, 2', 'addu t0, t0, sp', 'lw a3, 0x18(t0)', f'addiu t0, zero, {X}',
          'sw t0, 0x10(sp)', f'addiu t1, zero, {DY}', 'mult s0, t1', 'mflo t1', f'addiu t1, t1, {Y}', f'jal {LINE_FN}', 'sw t1, 0x14(sp)',
          'move s2, v0', 'addiu s0, s0, 1', 'slti at, s0, 5', 'bnez at, hln', 'nop',
          'lw t0, 0x18(sp)', 'lw t1, 0x1c(sp)', 'lw t2, 0x20(sp)', 'lw t3, 0x24(sp)', 'lw t4, 0x28(sp)', 'addu a2, t0, t1', 'addu a2, a2, t2',
          'addu a2, a2, t3', 'addu a2, a2, t4', 'move a0, s1', 'move a1, s2', f'addiu a3, zero, {X + 16}', f'addiu t0, zero, {Y + TY}',
          f'jal {TOTAL_FN}', 'sw t0, 0x10(sp)',
          # translucent dark box (TILE, half transparent with the panel's blending mode), drawn after the mode, before the text
          'lw t0, 0(s1)', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'and t0, t0, t2', 'lui t3, 0x300', 'or t0, t0, t3', 'sw t0, 0(v0)',
          'lw t0, 0(s1)', 'lui t3, 0xff00', 'and t0, t0, t3', 'and t4, v0, t2', 'or t0, t0, t4', 'sw t0, 0(s1)',
          'lui t0, 0x6200', 'sw t0, 4(v0)', f'lui t0, {(BOX[1] - 120) & 0xffff:#x}', f'ori t0, t0, {(BOX[0] - 160) & 0xffff:#x}', 'sw t0, 8(v0)',
          f'lui t0, {BOX[3]:#x}', f'ori t0, t0, {BOX[2]:#x}', 'sw t0, 0xc(v0)', 'addiu v0, v0, 16',
          # texture page of the panel (4 bits, VRAM x 320, y 0), linked last = drawn first, as the panel does
          'lui t1, 0xe100', f'ori t1, t1, {DRAW_MODE & 0xffff:#x}', 'sw t1, 4(v0)', 'lw t0, 0(s1)', 'lui t2, 0xff', 'ori t2, t2, 0xffff',
          'and t0, t0, t2', 'lui t3, 0x100', 'or t0, t0, t3', 'sw t0, 0(v0)', 'lw t0, 0(s1)', 'lui t3, 0xff00', 'and t0, t0, t3', 'and t4, v0, t2',
          'or t0, t0, t4', 'sw t0, 0(s1)', 'addiu v0, v0, 8',
          f'lui t0, {H(PRIMS)}', f'sw v0, {L(PRIMS)}(t0)',
          'hpx:', 'lw v0, 0x40(sp)', 'lw ra, 0x44(sp)', 'lw s0, 0x30(sp)', 'lw s1, 0x34(sp)', 'lw s2, 0x38(sp)', 'lw s3, 0x3c(sp)', 'jr ra', 'addiu sp, sp, 0x48']
    c, l = asm(S, CAVE)
    assert c[-1][0] < CAVE_END, hex(c[-1][0])
    return c, l


def ops(disc):
    hp = disc.read_file('/HP.BIN')
    w = lambda a: struct.unpack_from('<I', hp, a - OVL)[0]
    J = lambda t: (3 << 26) | ((t >> 2) & 0x3ffffff)
    assert w(HOOK) == J(HOOK_FN) and w(HOOK + 4) == 0x03C02021              # jal func_800757EC / addu a0, fp, zero
    c, l = code()
    P = [(a, x) for a, x in c] + [(HOOK, J(l['hpj']))]
    return [['w', '/HP.BIN', a - OVL, w(a), x] for a, x in P]
