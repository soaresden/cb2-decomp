# Race radar with heads (mod `radar`, v27): in the Boarder Cross of the competition (SBC2.BIN), the progress bar at the
# top left (S ... F) shows each rider's 16x16 head instead of a 4x4 coloured square.
#
# SBC2: func_8006D2A4 (called by the race loop with the racer array D_8009146C, 8 x 0x1288 bytes) draws the bar: a
# translucent TILE (x -0x90, y -0x78, 0x70 x 0xD, rect at sp + 0x18), then per racer (loop 0x8006D418..0x8006D53C,
# s3 = index, s5 = racer) a 4x4 TILE at x = -0x90 + (0x70 - 4) * func_8007E4B0(course, racer->0) / 255, y = -0x78 + 1 +
# slot, colour = table D_8008DD88[slot] (slot = racer + 3: the rider's place in the competition roster, YAGGI JIN CINDY
# IRIN JICCHI NICK KELLY BOSS; the player has the place g_rider), each tile in its own ordering-table entry (s6 = 3..10,
# the lower entries drawn last), the player's tile blinking (flag sp + 0x70); then the bar (entry s6) and the letters.
# Hook: 0x8006D410 ("addu s3, zero, zero") -> j rad (delay slot kept). rad: with the option off, back to the loop as
# before. Otherwise the bar is made 0x16 high from y -0x7E (top of the screen, TIME is under it), the heads (BOARDER strip of the menu: YAGGI JIN CINDY IRIN
# JICCHI NICK KELLY BOSS GRAY SNOWMAN, made by the mod crew's 'icons' operation in TITLE/MAIN_SEL.FBD, copied here by
# 'fcopy') are sent to free VRAM of the race (x 768.., y 472, palettes y 490) every frame, and each racer gets a SPRT
# 16x16 (CPU: head of its place; player: head of g_rider, or of the crew alias), odd places of the race (racer + 0x58)
# on the upper row and even ones 4 pixels lower (a pack stays readable), the player with a yellow outline that
# blinks like the original square, and a DR_TPAGE for the heads' page (the HUD text in the same entries changes it); then back to 0x8006D540 with s2 (primitives) and s6 (next entry) as the loop leaves
# them. Code and data in two dead functions of SBC2 (no call, jump or pointer to them).
import struct
from asm import asm

OVL = 0x8005AEA8
FILE = '/SBC2.BIN'
HOOK, BACK_LOOP, BACK_END = 0x8006D410, 0x8006D418, 0x8006D540
PROGRESS = 0x8007E4B0                       # (course, position) -> 0..255
LOADIMAGE = 0x80029B7C
CODE, CODE_END = 0x8007D614, 0x8007DF54     # dead function func_8007D614 (0x940 bytes)
DATA, DATA_END = 0x8007BEB8, 0x8007C81C     # dead function func_8007BEB8 (0x964 bytes)
OPT_FLAGS, OPT_BIT = 0x80057438, 64         # in-game options (mod options): bit set = radar off
G_RIDER, MODE = 0x80057408, 0x80057420
HEADS_VRAM, CLUT_VRAM = (768, 472), (768, 490)   # empty in the race (bottom of the HUD texture page)
N = 10                                      # heads, in the order of crew.STRIP_ORDER
PIX, CLUTS, RECT1, RECT2 = 0, 1280, 1600, 1608
BAR_Y, BAR_H, HEAD_Y, ROW_DY = -0x7E, 0x16, -0x7D, 4    # two rows of heads: odd places at HEAD_Y, even ones ROW_DY lower
TPAGE = 0xE1000400 | (1 << 4) | (HEADS_VRAM[0] >> 6)    # 4 bits, VRAM (768, 256)
FRAME_RGB = 0x0000FFFF                       # yellow (r, g, b = ff, ff, 00)


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)


def data_words():
    return struct.pack('<4h', HEADS_VRAM[0], HEADS_VRAM[1], 4 * N, 16) + struct.pack('<4h', CLUT_VRAM[0], CLUT_VRAM[1], 16 * N, 1)


def code(aliasv, basev, modesv):
    la = lambda r, a: [f'lui {r}, {H(a)}', f'addiu {r}, {r}, {L(a)}']
    S = ['rad:', 'lui t0, 0x8005', f'lbu t0, {OPT_FLAGS & 0xffff:#x}(t0)', 'nop', f'andi t0, t0, {OPT_BIT}', 'beqz t0, ra0', 'nop',
         f'j {BACK_LOOP}', 'move s3, zero',
         'ra0:', f'addiu t0, zero, {BAR_Y}', 'sh t0, 0x1a(sp)', f'addiu t0, zero, {BAR_H}', 'sh t0, 0x22(sp)',
         # heads and palettes to VRAM
         *la('a0', DATA + RECT1), *la('a1', DATA + PIX), f'jal {LOADIMAGE}', 'nop',
         *la('a0', DATA + RECT2), *la('a1', DATA + CLUTS), f'jal {LOADIMAGE}', 'nop',
         # player's head (s7): crew alias of g_rider if chosen for this mode, else g_rider (Boss, Gray, Snowman = 7..9)
         'lui t0, 0x8005', f'lh s4, {G_RIDER & 0xffff:#x}(t0)', 'nop', 'move s7, s4', 'slti at, s4, 4', 'bnez at, rp1', 'nop', 'addiu s7, s4, 3',
         'rp1:', f'lui at, {H(aliasv)}', f'lw t1, {L(aliasv)}(at)', 'nop', 'addiu t2, t1, -1', 'sltiu at, t2, 3', 'beqz at, rp2', 'nop',
         f'lui at, {H(basev)}', 'addu at, at, t1', f'lbu t2, {L(basev)}(at)', 'nop', 'bne t2, s4, rp2', 'nop',
         'lui at, 0x8005', f'lw t3, {MODE & 0xffff:#x}(at)', f'lui at, {H(modesv)}', f'lw at, {L(modesv)}(at)', 'nop', 'srlv at, at, t3',
         'andi at, at, 1', 'beqz at, rp2', 'nop', 'addiu s7, t1, 3',
         'rp2:', 'move s3, zero', 'move s1, s5']
    # per racer (s3 = index, s1 = racer, s4 = g_rider, s7 = player's head): x = -0x90 + (0x70 - 16) * progress / 255
    S += ['rl:', 'lw a0, 0x60(sp)', 'jal {}'.format(PROGRESS), 'lh a1, 0(s1)', 'addiu t0, zero, 0x60', 'mult v0, t0', 'mflo t0',
          'addiu t1, zero, 255', 'divu t0, t1', 'mflo t0', 'lh t1, 0x18(sp)', 'nop', 'addu s0, t1, t0',
          'lh t2, 0x58(s1)', f'addiu s5, zero, {HEAD_Y}', 'andi t2, t2, 1', 'bnez t2, rl0', 'nop', f'addiu s5, s5, {ROW_DY}',
          'rl0:', 'lbu t2, 3(s1)', 'nop', 'move t3, t2', 'bne t2, s4, rl1', 'nop', 'move t3, s7',
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


def ops(disc, aliasv, basev, modesv, fbd, icon_x, icon_y, clut_x, clut_y, pre):
    """pre: the crew operations that make the heads in the FBD ('face', 'icons'), applied again before the copy"""
    d = disc.read_file(FILE); w = lambda a: struct.unpack_from('<I', d, a - OVL)[0]
    J = lambda op, t: (op << 26) | ((t >> 2) & 0x3ffffff)
    assert w(HOOK) == 0x00009821 and w(HOOK + 4) == 0xAFA20070                 # addu s3, zero, zero / sw v0, 0x70(sp)
    assert w(BACK_LOOP) == 0x16600005 and w(BACK_END) == 0x3C0800FF             # bnez s3 / lui t0, 0xff
    c, l = code(aliasv, basev, modesv)
    P = [(a, x) for a, x in c] + [(HOOK, J(2, l['rad']))]
    dw = data_words(); P += [(DATA + RECT1 + i, struct.unpack_from('<I', dw, i)[0]) for i in range(0, len(dw), 4)]
    out = list(pre) + [['w', FILE, a - OVL, w(a), x] for a, x in P]
    vo = lambda x, y: 20 + (y * 704 + x - 320) * 2               # TITLE/MAIN_SEL.FBD (x 320.., 704 wide)
    segs = [[vo(icon_x, icon_y + y), DATA - OVL + PIX + 8 * N * y, 8 * N] for y in range(16)]
    segs += [[vo(clut_x + 16 * (i % 6), clut_y + i // 6), DATA - OVL + CLUTS + 32 * i, 32] for i in range(N)]
    out.append(['fcopy', fbd, FILE, segs])
    return out
