# Race radar with heads (mod `radar`, v27): in the Boarder Cross of the competition (SBC2.BIN), the progress bar (S ... F,
# at the top left) becomes a long line at the bottom of the screen with each rider's 16x16 head instead of a 4x4 square.
#
# SBC2: func_8006D2A4 (called by the race loop with the racer array D_8009146C, 8 x 0x1288 bytes) draws the bar: a
# translucent TILE (x -0x90, y -0x78, 0x70 x 0xD, rect at sp + 0x18), then per racer (loop 0x8006D418..0x8006D53C,
# s3 = index, s5 = racer) a 4x4 TILE at x = -0x90 + (0x70 - 4) * func_8007E4B0(course, racer->0) / 255, y = -0x78 + 1 +
# slot, colour = table D_8008DD88[slot] (slot = racer + 3: the rider's place in the competition roster, YAGGI JIN CINDY
# IRIN JICCHI NICK KELLY BOSS; the player has the place g_rider), each tile in its own ordering-table entry (s6 = 3..10,
# the lower entries drawn last), the player's tile blinking (flag sp + 0x70); then the bar (entry s6) and the letters.
# Hook: 0x8006D410 ("addu s3, zero, zero") -> j rad (delay slot kept). rad: with the option off, back to the loop as
# before. Otherwise the bar becomes a long thin dark line at the bottom of the screen (x -0x8C, y 112, 0x110 x 6: the
# position and the speed end at y 108, the screen at 123; the letters S and F follow it at its ends; its grey comes
# from sp + 0x7C, an unused word of the frame, 0xFF with the option off), the heads (BOARDER
# strip of the menu: YAGGI JIN CINDY IRIN JICCHI NICK KELLY BOSS GRAY SNOWMAN, made by the mod crew's 'icons' operation
# in TITLE/MAIN_SEL.FBD, copied here by 'fcopy') are sent to free VRAM of the race (x 768.., y 472, palettes y 490)
# every frame, and each racer gets a SPRT 16x16 on the line (CPU: head of its place; player: head of g_rider, or of the
# crew alias), the player with a yellow outline that blinks like the original square, and a DR_TPAGE for the heads'
# page (the HUD text in the same entries changes it); then back to 0x8006D540 with s2 (primitives) and s6 (next entry)
# as the loop leaves them. Code and data in two dead functions of SBC2 (no call, jump or pointer to them).
# Falls (v35): the row of balls of the bottom left (func_80078E58 from 0x8006D12C, x -0x98, y 0x68: tens as big balls,
# units as small ones, of the rider's + 0xCDE) went under the line; with the line on, `rfall` gives it y -0x7C: at the
# top left, where the original bar was (above TIME). v36: with FALLS AS A NUMBER (options, bit 17), one ball and "x13".
# Ranking panel (bit 128 of the options off): before that, `rank` draws on the right three rows (the place ahead of the
# player, the player's, the one behind), each with the place in SBC2's HUD font (gold, silver, bronze shimmering for
# the first three), the head and the gap to the player in seconds, timed at the course's segments (see docs/modular.md).
import struct
from asm import asm

OVL = 0x8005AEA8
FILE = '/SBC2.BIN'
HOOK, BACK_LOOP, BACK_END = 0x8006D410, 0x8006D418, 0x8006D540
PROGRESS = 0x8007E4B0                       # (course, position) -> 0..255
LOADIMAGE, PRIMS = 0x80029B7C, 0x80058E0C
CODE, CODE_END = 0x8007D614, 0x8007DF54     # dead function func_8007D614 (0x940 bytes)
DATA, DATA_END = 0x8007BEB8, 0x8007C81C     # dead function func_8007BEB8 (0x964 bytes)
OPT_FLAGS, LINE_BIT, RANK_BIT = 0x80057438, 64, 128    # in-game options (mod options): bit set = line / panel off
VSYNC, TEXT, TEXT_RGB, FONT = 0x8003BE30, 0x8008AFC8, 0x8008B354, 0x8009BBC0   # VSync(-1); SBC2's HUD text (the S and F)
G_RIDER, MODE = 0x80057408, 0x80057420
HEADS_VRAM, CLUT_VRAM = (768, 472), (768, 490)   # empty in the race (bottom of the HUD texture page)
N = 10                                      # heads, in the order of crew.STRIP_ORDER
PIX, CLUTS, RECT1, RECT2, POSS, PCT, COLS = 0, 1280, 1600, 1608, 1616, 1652, 1660   # data block (end 1684)
LAST, PIDX, PPL, PRAC, RIDX = 1684, 1688, 1692, 1696, 1700     # work words (LAST = 0 in the file, the others not)
FALL_SITE = 0x8006D114                     # addiu a1, zero, -0x98 / addiu a2, zero, 0x68 (x, y of the falls' balls)
FALL_STR = DATA + 0x6F0                     # "x13" (rfall), after the data block and its work words
FALL_CODE = DATA + 0x700                    # `rfall`
FALL_NUM_BIT = 17                           # options: FALLS AS A NUMBER (bit set = off)
RINGS = (0x8006C488, 0x80074F48)            # dead functions of SBC2 used as RAM: gates of racers 0..3 and 4..7
PX, PY, ROW = 66, -24, 18                   # ranking panel: places, heads, gaps (right side, mid height)
# text colours (the font is white, 0x80 = as is): gold, silver, bronze, others; value = base + step * t, t = 0..15..0
COLORS = [(128, 84, 0, 0, 2, 1), (88, 88, 96, 2, 2, 2), (104, 56, 20, 2, 2, 1), (128, 128, 128, 0, 0, 0)]
BOX_RGB = 0x00181818
BAR_X, BAR_W, BAR_Y, BAR_H, HEAD_Y = -0x8C, 0x110, 112, 6, 107    # a long thin line at the bottom, the heads on it
LINE_RGB = 0x30                             # grey level of the line (translucent: a white one disappears on the snow)
COLOR_SITE = 0x8006D58C                     # "lhu t1, 0x22(sp) / addiu v0, zero, 0xFF" (bar colour) -> "lw v0, 0x7c(sp) / lhu t1, ..."

TPAGE = 0xE1000400 | (1 << 4) | (HEADS_VRAM[0] >> 6)    # 4 bits, VRAM (768, 256)
FRAME_RGB = 0x0000FFFF                       # yellow (r, g, b = ff, ff, 00)


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)


def data_words():
    d = struct.pack('<4h', HEADS_VRAM[0], HEADS_VRAM[1], 4 * N, 16) + struct.pack('<4h', CLUT_VRAM[0], CLUT_VRAM[1], 16 * N, 1)
    d += b''.join(('%d%s' % (k, 'ST' if k == 1 else 'ND' if k == 2 else 'RD' if k == 3 else 'TH')).encode() + b'\0' for k in range(1, 10))[:36]
    d += bytes(8) + b''.join(bytes(c) for c in COLORS) + bytes(4)        # + LAST
    assert len(d) == LAST + 4 - RECT1 and len(d) % 4 == 0
    return d


def code(aliasv, basev, modesv):
    la = lambda r, a: [f'lui {r}, {H(a)}', f'addiu {r}, {r}, {L(a)}']
    S = ['rad:', 'addiu t1, zero, 0xff', 'sw t1, 0x7c(sp)', 'lui t0, 0x8005', f'lhu t0, {OPT_FLAGS & 0xffff:#x}(t0)', 'nop',
         f'andi t0, t0, {LINE_BIT | RANK_BIT}', f'addiu t1, zero, {LINE_BIT | RANK_BIT}', 'bne t0, t1, ra0', 'nop',
         f'j {BACK_LOOP}', 'move s3, zero',
         # heads and palettes to VRAM
         'ra0:', *la('a0', DATA + RECT1), *la('a1', DATA + PIX), f'jal {LOADIMAGE}', 'nop',
         *la('a0', DATA + RECT2), *la('a1', DATA + CLUTS), f'jal {LOADIMAGE}', 'nop',
         # player's head (s7): crew alias of g_rider if chosen for this mode, else g_rider (Boss, Gray, Snowman = 7..9)
         'lui t0, 0x8005', f'lh s4, {G_RIDER & 0xffff:#x}(t0)', 'nop', 'move s7, s4', 'slti at, s4, 4', 'bnez at, rp1', 'nop', 'addiu s7, s4, 3',
         'rp1:', f'lui at, {H(aliasv)}', f'lw t1, {L(aliasv)}(at)', 'nop', 'addiu t2, t1, -1', 'sltiu at, t2, 3', 'beqz at, rp2', 'nop',
         f'lui at, {H(basev)}', 'addu at, at, t1', f'lbu t2, {L(basev)}(at)', 'nop', 'bne t2, s4, rp2', 'nop',
         'lui at, 0x8005', f'lw t3, {MODE & 0xffff:#x}(at)', f'lui at, {H(modesv)}', f'lw at, {L(modesv)}(at)', 'nop', 'srlv at, at, t3',
         'andi at, at, 1', 'beqz at, rp2', 'nop', 'addiu s7, t1, 3',
         'rp2:', 'lui t0, 0x8005', f'lhu t0, {OPT_FLAGS & 0xffff:#x}(t0)', 'nop', f'andi t0, t0, {RANK_BIT}', 'bnez t0, rp3', 'nop',
         'jal rank', 'nop',
         'rp3:', 'lui t0, 0x8005', f'lhu t0, {OPT_FLAGS & 0xffff:#x}(t0)', 'nop', f'andi t0, t0, {LINE_BIT}', 'beqz t0, rp4', 'nop',
         # line off: the original loop, with its registers (s1 = primitive + 0xA, a2 = 0xFF000000, s7 = 0xFFFFFF)
         'addiu s1, s2, 0xa', 'lui a2, 0xff00', 'lui s7, 0xff', 'ori s7, s7, 0xffff', f'j {BACK_LOOP}', 'move s3, zero',
         'rp4:', f'addiu t1, zero, {LINE_RGB}', 'sw t1, 0x7c(sp)', f'addiu t0, zero, {BAR_X}', 'sh t0, 0x18(sp)', f'addiu t0, zero, {BAR_Y}', 'sh t0, 0x1a(sp)',
         f'addiu t0, zero, {BAR_W}', 'sh t0, 0x20(sp)', f'addiu t0, zero, {BAR_H}', 'sh t0, 0x22(sp)',
         'move s3, zero', 'move s1, s5']
    # per racer (s3 = index, s1 = racer, s4 = g_rider, s7 = player's head, s5 = y): x = BAR_X + (BAR_W - 16) * progress / 255
    S += ['rl:', 'lw a0, 0x60(sp)', 'jal {}'.format(PROGRESS), 'lh a1, 0(s1)', f'addiu t0, zero, {BAR_W - 16}', 'mult v0, t0', 'mflo t0',
          'addiu t1, zero, 255', 'divu t0, t1', 'mflo t0', 'lh t1, 0x18(sp)', 'nop', 'addu s0, t1, t0',
          f'addiu s5, zero, {HEAD_Y}', 'lbu t2, 3(s1)', 'nop', 'move t3, t2', 'bne t2, s4, rl1', 'nop', 'move t3, s7',
          # SPRT 16x16: tag (len 3), 0x7C808080, y << 16 | x, clut << 16 | v << 8 | u
          'rl1:', 'lui t4, 0x300', 'sw t4, 0(s2)', 'lui t4, 0x7c80', 'ori t4, t4, 0x8080', 'sw t4, 4(s2)',
          'sll t5, s5, 16', 'andi t6, s0, 0xffff', 'or t5, t5, t6', 'sw t5, 8(s2)',
          f'addiu t6, t3, {(CLUT_VRAM[1] << 6) | (CLUT_VRAM[0] >> 4)}', 'sll t6, t6, 16', f'ori t6, t6, {(HEADS_VRAM[1] - 256) << 8}',
          'sll t7, t3, 4', 'or t6, t6, t7', 'sw t6, 12(s2)',
          'move a0, s2', 'jal radd', 'addiu s2, s2, 16',
          # the player's frame (behind the head: linked after it), when the blink flag is on
          'lbu t2, 3(s1)', 'nop', 'bne t2, s4, rl2', 'nop', 'lw t0, 0x70(sp)', 'nop', 'beqz t0, rl2', 'nop',
          'addiu t5, s5, -1', 'sll t5, t5, 16', 'addiu t6, s0, -1', 'andi t6, t6, 0xffff', 'or a1, t5, t6',
          'lui a2, 1', 'jal rtile', 'ori a2, a2, 18',                                  # top
          'lui t0, 17', 'addu a1, a1, t0', 'lui a2, 1', 'jal rtile', 'ori a2, a2, 18',   # bottom
          'sll t5, s5, 16', 'addiu t6, s0, -1', 'andi t6, t6, 0xffff', 'or a1, t5, t6',
          'lui a2, 16', 'jal rtile', 'ori a2, a2, 1',                                   # left
          'addiu a1, a1, 17', 'lui a2, 16', 'jal rtile', 'ori a2, a2, 1',               # right
          # texture page of the heads, drawn just before them (head of the entry's list: the HUD text changes it)
          'rl2:', 'lui t4, 0x100', 'sw t4, 0(s2)', f'lui t4, {TPAGE >> 16:#x}', f'ori t4, t4, {TPAGE & 0xffff:#x}', 'sw t4, 4(s2)',
          'move a0, s2', 'jal radd', 'addiu s2, s2, 8',
          'addiu s6, s6, 1', 'addiu s3, s3, 1', 'slti at, s3, 8', 'bnez at, rl', 'addiu s1, s1, 0x1288',
          f'j {BACK_END}', 'nop']
    # rank: the panel (rows: the place ahead of the player, the player's, the one behind; 1st..3rd when leading,
    # 6th..8th when last), in ordering-table entry 3 like the HUD text; s0, s1, s3 used, s6 kept; free words of the
    # frame: 0x24 (place of the row), 0x2C (rtext's return), 0x5C (s6), 0x64 (shimmer), 0x6C (first row), 0x74 (return)
    S += ['rank:', 'sw ra, 0x74(sp)', 'sw s6, 0x5c(sp)', 'addiu s6, zero, 3',
          # the player's place p (racer whose slot is g_rider) -> first row w = clamp(p - 1, 1, 6) at 0x6c(sp)
          'move t0, s5', 'addiu t1, zero, 8', 'addiu t3, zero, 1', *la('t6', DATA),
          'rk0:', 'lbu t2, 3(t0)', 'nop', 'bne t2, s4, rk1', 'nop', 'lh t3, 0x58(t0)', 'addiu t2, zero, 8', 'subu t2, t2, t1',
          f'sw t2, {PIDX}(t6)', f'sw t3, {PPL}(t6)', f'sw t0, {PRAC}(t6)',
          'rk1:', 'addiu t1, t1, -1', 'bnez t1, rk0', 'addiu t0, t0, 0x1288',
          'addiu t3, t3, -1', 'slti at, t3, 1', 'beqz at, rk2', 'nop', 'addiu t3, zero, 1', 'rk2:', 'slti at, t3, 7', 'bnez at, rk3', 'nop',
          'addiu t3, zero, 6', 'rk3:', 'sw t3, 0x6c(sp)',
          # shimmer t = 0..15..0 (VSync count / 2) at 0x64(sp)
          f'jal {VSYNC}', 'addiu a0, zero, -1', 'jal rgate', 'nop', 'srl v0, v0, 1', 'andi v0, v0, 31', 'slti at, v0, 16', 'bnez at, rk4', 'nop',
          'addiu t0, zero, 31', 'subu v0, t0, v0', 'rk4:', 'sw v0, 0x64(sp)',
          'move s3, zero',
          'rr0:', 'lw t3, 0x6c(sp)', 'nop', 'addu t3, t3, s3', 'move s1, s5', 'addiu t1, zero, 8',
          'rr1:', 'lh t2, 0x58(s1)', 'addiu t4, zero, 8', 'subu t4, t4, t1', 'beq t2, t3, rr2', 'nop', 'addiu t1, t1, -1', 'bnez t1, rr1', 'addiu s1, s1, 0x1288',
          'j rr9', 'nop',
          # s1 = racer of the row, t3 = its place; s0 = y
          'rr2:', f'lui at, {H(DATA + RIDX)}', f'sw t4, {L(DATA + RIDX)}(at)', 'sw t3, 0x24(sp)', f'addiu t0, zero, {ROW}', 'mult s3, t0', 'mflo s0', f'addiu s0, s0, {PY}',
          # colour of the place (1st gold, 2nd silver, 3rd bronze, others white), shimmering
          'addiu t0, t3, -1', 'slti at, t0, 3', 'bnez at, rr3', 'nop', 'addiu t0, zero, 3',
          'rr3:', 'sll t1, t0, 1', 'addu t0, t1, t0', 'sll t0, t0, 1', *la('t1', DATA + COLS), 'addu t0, t0, t1', 'lw t9, 0x64(sp)',
          'lbu a1, 0(t0)', 'lbu t1, 3(t0)', 'nop', 'mult t1, t9', 'mflo t1', 'addu a1, a1, t1',
          'lbu a2, 1(t0)', 'lbu t1, 4(t0)', 'nop', 'mult t1, t9', 'mflo t1', 'addu a2, a2, t1',
          'lbu a3, 2(t0)', 'lbu t1, 5(t0)', 'nop', 'mult t1, t9', 'mflo t1', 'addu a3, a3, t1',
          f'lui a0, {H(FONT)}', f'jal {TEXT_RGB}', f'lw a0, {L(FONT)}(a0)',
          'lw t3, 0x24(sp)', 'nop', 'addiu t3, t3, -1', 'sll t3, t3, 2', *la('a2', DATA + POSS), 'addu a2, a2, t3',
          f'addiu a3, zero, {PX}', 'jal rtext', 'addiu t0, s0, 4',
          # head (the player's with the yellow outline), then its texture page
          'lbu t2, 3(s1)', 'nop', 'move t3, t2', 'bne t2, s4, rr4', 'nop', 'move t3, s7',
          'rr4:', 'move a1, s0', 'jal rhead', f'addiu a0, zero, {PX + 26}',
          'lbu t2, 3(s1)', 'nop', 'bne t2, s4, rr5', 'nop', f'addiu a0, zero, {PX + 26}', 'jal rbox', 'move a1, s0',
          'rr5:', 'jal rtp', 'nop',
          # gap to the player in seconds (gates: see rgate): ahead "-1.2", behind "+0.8", nothing on the player's row
          'lbu t2, 3(s1)', 'nop', 'beq t2, s4, rr9', 'nop', *la('t6', DATA), 'lw t3, 0x24(sp)', f'lw t4, {PPL}(t6)', 'nop',
          'slt at, t3, t4', 'beqz at, rg1', 'nop',
          f'lw t0, {PRAC}(t6)', 'nop', 'lh a1, 0(t0)', f'lw a0, {PIDX}(t6)', 'jal rent', 'nop', 'move t8, v0',
          f'lw a0, {RIDX}(t6)', 'jal rent', 'nop', 'move t9, v0', 'j rg2', 'addiu t7, zero, 0x2d',          # '-'
          'rg1:', 'lh a1, 0(s1)', f'lw a0, {RIDX}(t6)', 'jal rent', 'nop', 'move t8, v0',
          f'lw a0, {PIDX}(t6)', 'jal rent', 'nop', 'move t9, v0', 'addiu t7, zero, 0x2b',                  # '+'
          'rg2:', *la('a2', DATA + PCT), 'move t2, a2', 'bltz t8, rg9', 'nop', 'bltz t9, rg9', 'nop',
          'subu t0, t8, t9', 'andi t0, t0, 0xffff', 'slti at, t0, 5000', 'beqz at, rg9', 'nop',
          'addiu t1, zero, 5', 'divu t0, t1', 'mflo t0', 'addiu t1, zero, 10', 'divu t0, t1', 'mflo t0', 'mfhi t5',   # t0 s, t5 tenths
          'sb t7, 0(t2)', 'addiu t2, t2, 1', 'slti at, t0, 10', 'bnez at, rg3', 'nop', 'divu t0, t1', 'mflo t4', 'mfhi t0',
          'addiu t4, t4, 0x30', 'sb t4, 0(t2)', 'addiu t2, t2, 1',
          'rg3:', 'addiu t0, t0, 0x30', 'sb t0, 0(t2)', 'addiu t0, zero, 0x2e', 'sb t0, 1(t2)', 'addiu t5, t5, 0x30', 'sb t5, 2(t2)',
          'j rg8', 'sb zero, 3(t2)',
          'rg9:', 'addiu t0, zero, 0x2d', 'sb t0, 0(t2)', 'sb t0, 1(t2)', 'sb zero, 2(t2)',                     # "--"
          'rg8:', f'lui a0, {H(FONT)}', f'lw a0, {L(FONT)}(a0)', 'addiu a1, zero, 0x80', 'addiu a2, zero, 0x80', f'jal {TEXT_RGB}', 'addiu a3, zero, 0x80',
          *la('a2', DATA + PCT), f'addiu a3, zero, {PX + 45}', 'jal rtext', 'addiu t0, s0, 4',
          'rr9:', 'addiu s3, s3, 1', 'slti at, s3, 3', 'bnez at, rr0', 'nop',
          # dark translucent box behind the panel (linked last: drawn first), after a page with the half-and-half blending
          'lui t4, 0x300', 'sw t4, 0(s2)', f'lui t4, {0x6200 | (BOX_RGB >> 16)}', f'ori t4, t4, {BOX_RGB & 0xffff}', 'sw t4, 4(s2)',
          f'lui t4, {(PY - 3) & 0xffff:#x}', f'ori t4, t4, {(PX - 4) & 0xffff:#x}', 'sw t4, 8(s2)', f'lui t4, {3 * ROW + 4}', 'ori t4, t4, 92', 'sw t4, 12(s2)',
          'move a0, s2', 'jal radd', 'addiu s2, s2, 16', 'jal rtp', 'nop',
          'lw s6, 0x5c(sp)', 'lw ra, 0x74(sp)', 'nop', 'jr ra', 'nop']
    # rgate (v0 = VSync count, kept): for each racer, the VSync count (16 bits) at which it entered its current segment
    # (racer + 0), in a ring of 32 words (segment + 1) << 16 | count; the rings are cleared when the panel has not been
    # drawn for 30 frames (a new race, a retry). rent: a0 = racer index, a1 = segment -> v0 = count, or -1 if not there
    S += ['rgate:', *la('t6', DATA), 'andi t7, v0, 0xffff', f'lw t0, {LAST}(t6)', f'sw t7, {LAST}(t6)', 'subu t0, t7, t0', 'andi t0, t0, 0xffff',
          'slti at, t0, 30', 'bnez at, rg5', 'nop',
          *la('t0', RINGS[0]), 'addiu t1, t0, 512', 'rg4:', 'sw zero, 0(t0)', 'addiu t0, t0, 4', 'bne t0, t1, rg4', 'nop',
          *la('t0', RINGS[1]), 'addiu t1, t0, 512', 'rg6:', 'sw zero, 0(t0)', 'addiu t0, t0, 4', 'bne t0, t1, rg6', 'nop',
          'rg5:', 'move t5, s5', 'move t4, zero',
          'rg7:', 'lh t1, 0(t5)', 'nop', 'addiu t2, t1, 1', 'andi t1, t1, 31', 'sll t1, t1, 2', *la('t0', RINGS[0]), 'slti at, t4, 4', 'bnez at, rgA', 'sll t3, t4, 7',
          *la('t0', RINGS[1] - 512), 'rgA:', 'addu t0, t0, t3', 'addu t0, t0, t1', 'lw t3, 0(t0)', 'nop', 'srl t3, t3, 16', 'beq t3, t2, rgB', 'sll t3, t2, 16',
          'or t3, t3, t7', 'sw t3, 0(t0)',
          'rgB:', 'addiu t4, t4, 1', 'slti at, t4, 8', 'bnez at, rg7', 'addiu t5, t5, 0x1288', 'jr ra', 'nop']
    S += ['rent:', 'addiu t2, a1, 1', 'andi t1, a1, 31', 'sll t1, t1, 2', *la('t0', RINGS[0]), 'slti at, a0, 4', 'bnez at, reA', 'sll t3, a0, 7',
          *la('t0', RINGS[1] - 512), 'reA:', 'addu t0, t0, t3', 'addu t0, t0, t1', 'lw v0, 0(t0)', 'nop', 'srl t3, v0, 16', 'bne t3, t2, reB', 'nop',
          'jr ra', 'andi v0, v0, 0xffff', 'reB:', 'jr ra', 'addiu v0, zero, -1']
    # rtext: string a2 at x a3, y t0, font FONT, into entry s6
    # (the text takes its primitives at D_80058E0C, which the bar function keeps in s2 and writes back at its end)
    S += ['rtext:', 'sw ra, 0x2c(sp)', 'sw t0, 0x10(sp)', 'sw zero, 0x14(sp)', 'lw a0, 4(fp)', 'sll t1, s6, 2', 'addu a0, a0, t1',
          f'lui at, {H(PRIMS)}', f'sw s2, {L(PRIMS)}(at)',
          f'lui a1, {H(FONT)}', f'jal {TEXT}', f'lw a1, {L(FONT)}(a1)', f'lui at, {H(PRIMS)}', f'lw s2, {L(PRIMS)}(at)',
          'lw ra, 0x2c(sp)', 'nop', 'jr ra', 'nop']
    # rhead: SPRT 16x16 of head t3 at (a0, a1); rtp: DR_TPAGE of the heads; rbox: yellow outline around (a0, a1)
    S += ['rhead:', 'move t9, ra', 'lui t4, 0x300', 'sw t4, 0(s2)', 'lui t4, 0x7c80', 'ori t4, t4, 0x8080', 'sw t4, 4(s2)',
          'sll t5, a1, 16', 'andi t6, a0, 0xffff', 'or t5, t5, t6', 'sw t5, 8(s2)',
          f'addiu t6, t3, {(CLUT_VRAM[1] << 6) | (CLUT_VRAM[0] >> 4)}', 'sll t6, t6, 16', f'ori t6, t6, {(HEADS_VRAM[1] - 256) << 8}',
          'sll t7, t3, 4', 'or t6, t6, t7', 'sw t6, 12(s2)', 'move a0, s2', 'jal radd', 'addiu s2, s2, 16', 'jr t9', 'nop']
    S += ['rtp:', 'move t9, ra', 'lui t4, 0x100', 'sw t4, 0(s2)', f'lui t4, {TPAGE >> 16:#x}', f'ori t4, t4, {TPAGE & 0xffff:#x}', 'sw t4, 4(s2)',
          'move a0, s2', 'jal radd', 'addiu s2, s2, 8', 'jr t9', 'nop']
    S += ['rbox:', 'move t9, ra', 'addiu t5, a1, -1', 'sll t5, t5, 16', 'addiu t6, a0, -1', 'andi t6, t6, 0xffff', 'or a1, t5, t6',
          'lui a2, 1', 'jal rtile', 'ori a2, a2, 18', 'lui t0, 17', 'addu a1, a1, t0', 'lui a2, 1', 'jal rtile', 'ori a2, a2, 18',
          'lui t0, 0xfff0', 'addu a1, a1, t0',                                                # back to y (- 16)
          'lui a2, 16', 'jal rtile', 'ori a2, a2, 1', 'addiu a1, a1, 17', 'lui a2, 16', 'jal rtile', 'ori a2, a2, 1', 'jr t9', 'nop']
    # rtile: a yellow TILE at a1 (y << 16 | x), size a2 (h << 16 | w), linked into entry s6
    S += ['rtile:', 'move t8, ra', 'lui t4, 0x300', 'sw t4, 0(s2)', f'lui t4, {0x6000 | (FRAME_RGB >> 16)}', f'ori t4, t4, {FRAME_RGB & 0xffff}',
          'sw t4, 4(s2)', 'sw a1, 8(s2)', 'sw a2, 12(s2)', 'move a0, s2', 'jal radd', 'addiu s2, s2, 16', 'jr t8', 'nop']
    # radd: link the primitive a0 into the ordering-table entry s6 (OT = fp->4)
    S += ['radd:', 'lw t0, 4(fp)', 'sll t1, s6, 2', 'addu t0, t0, t1', 'lw t1, 0(t0)', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'lw t3, 0(a0)',
          'and t4, t1, t2', 'lui t5, 0xff00', 'and t3, t3, t5', 'or t3, t3, t4', 'sw t3, 0(a0)', 'and t1, t1, t5', 'and t4, a0, t2',
          'or t1, t1, t4', 'jr ra', 'sw t1, 0(t0)']
    c, l = asm(S, CODE)
    assert c[-1][0] < CODE_END, hex(c[-1][0])
    return c, l


def fall_code():
    """rfall (jal from FALL_SITE, in func_8006D0C0, before func_80078E58(t0, x, y, count a3, phase)): x -0x98; y 0x68 with
    the line off, -0x7C (top left) with it on; with FALLS AS A NUMBER and count > 0: count = 1 (one ball) and "x<count>"
    in SBC2's HUD font after it. The caller's mult is pending (its mfhi after the call): HI and LO are kept."""
    H_ = lambda a: (a + 0x8000) >> 16
    L_ = lambda a: a - (H_(a) << 16)
    return ['rfall:', 'addiu sp, sp, -0x40', 'sw ra, 0x38(sp)', 'sw t0, 0x34(sp)', 'mfhi t1', 'sw t1, 0x30(sp)', 'mflo t1', 'sw t1, 0x2c(sp)',
            f'lui t9, {H_(OPT_FLAGS)}', f'lw t9, {L_(OPT_FLAGS)}(t9)', 'addiu a1, zero, -0x98', f'andi t8, t9, {LINE_BIT}',
            'bnez t8, rf1', 'addiu a2, zero, 0x68', 'addiu a2, zero, -0x7c',
            'rf1:', f'srl t8, t9, {FALL_NUM_BIT}', 'andi t8, t8, 1', 'bnez t8, rf9', 'nop', 'blez a3, rf9', 'nop',
            'sw a2, 0x28(sp)',
            # "x" + the count's digits, at FALL_STR
            f'lui t1, {H_(FALL_STR + 8)}', f'addiu t1, t1, {L_(FALL_STR + 8)}', 'sb zero, 0(t1)', 'move t2, a3', 'addiu t3, zero, 10',
            'rd1:', 'divu t2, t3', 'mfhi t4', 'mflo t2', 'addiu t4, t4, 0x30', 'addiu t1, t1, -1', 'bnez t2, rd1', 'sb t4, 0(t1)',
            'addiu t1, t1, -1', 'addiu t4, zero, 0x78', 'sb t4, 0(t1)', 'sw t1, 0x24(sp)',
            f'lui a0, {H_(FONT)}', f'lw a0, {L_(FONT)}(a0)', 'addiu a1, zero, 0x80', 'addiu a2, zero, 0x80', f'jal {TEXT_RGB}', 'addiu a3, zero, 0x80',
            'lw t0, 0x34(sp)', 'lw a2, 0x24(sp)', 'lw a0, 4(t0)', f'lui a1, {H_(FONT)}', f'lw a1, {L_(FONT)}(a1)', 'addiu a0, a0, 0xc',
            'lw t1, 0x28(sp)', 'addiu a3, zero, -0x86', 'addiu t1, t1, 8', 'sw t1, 0x10(sp)', f'jal {TEXT}', 'sw zero, 0x14(sp)',
            'lw a2, 0x28(sp)', 'addiu a1, zero, -0x98', 'addiu a3, zero, 1',
            'rf9:', 'lw t1, 0x30(sp)', 'nop', 'mthi t1', 'lw t1, 0x2c(sp)', 'nop', 'mtlo t1', 'lw t0, 0x34(sp)', 'lw ra, 0x38(sp)',
            'nop', 'jr ra', 'addiu sp, sp, 0x40']


def ops(disc, aliasv, basev, modesv, fbd, icon_x, icon_y, clut_x, clut_y, pre):
    """pre: the crew operations that make the heads in the FBD ('face', 'icons'), applied again before the copy"""
    d = disc.read_file(FILE); w = lambda a: struct.unpack_from('<I', d, a - OVL)[0]
    J = lambda op, t: (op << 26) | ((t >> 2) & 0x3ffffff)
    assert w(HOOK) == 0x00009821 and w(HOOK + 4) == 0xAFA20070                 # addu s3, zero, zero / sw v0, 0x70(sp)
    assert w(BACK_LOOP) == 0x16600005 and w(BACK_END) == 0x3C0800FF             # bnez s3 / lui t0, 0xff
    c, l = code(aliasv, basev, modesv)
    assert w(COLOR_SITE) == 0x97A90022 and w(COLOR_SITE + 4) == 0x240200FF
    P = [(a, x) for a, x in c] + [(HOOK, J(2, l['rad'])), (COLOR_SITE, 0x8FA2007C), (COLOR_SITE + 4, 0x97A90022)]
    dw = data_words(); P += [(DATA + RECT1 + i, struct.unpack_from('<I', dw, i)[0]) for i in range(0, len(dw), 4)]
    # the falls' balls: y from the line's switch, one ball and "x13" with FALLS AS A NUMBER (rfall)
    assert w(FALL_SITE) == 0x2405FF68 and w(FALL_SITE + 4) == 0x24060068 and DATA + LAST + 24 <= FALL_STR
    cf, lf = asm(fall_code(), FALL_CODE)
    assert cf[-1][0] < DATA_END
    P += cf + [(FALL_SITE, J(3, lf['rfall'])), (FALL_SITE + 4, 0)]
    out = list(pre) + [['w', FILE, a - OVL, w(a), x] for a, x in P]
    vo = lambda x, y: 20 + (y * 704 + x - 320) * 2               # TITLE/MAIN_SEL.FBD (x 320.., 704 wide)
    segs = [[vo(icon_x, icon_y + y), DATA - OVL + PIX + 8 * N * y, 8 * N] for y in range(16)]
    segs += [[vo(clut_x + 16 * (i % 6), clut_y + i // 6), DATA - OVL + CLUTS + 32 * i, 32] for i in range(N)]
    out.append(['fcopy', fbd, FILE, segs])
    import boost                                                 # trick boost (v43): SBC1 installer, SBC2 hook
    return out + boost.ops(disc)
