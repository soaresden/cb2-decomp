# The MAX line of the BOARD screen in the style of the game's TYPE-1 / SPECIAL labels (part of the mod `max`, v50).
#
# The game's labels are 4-bit images 64 x 16 texels (VRAM x 320..383, y 496..511 of TITLE/MAIN_SEL.FBD, palette
# (960, 455) = CLUT 0x71FC), drawn 64 x 22 as POLY_FT4 at x -32 (white 0x7F7F7F when chosen, 0x323232 otherwise).
# Here a "MAX" in the same style (white letters, orange shadow on the lower left, dark outline) is drawn at build time
# from Noto Sans Black Italic with the label palette's indices, written into MAIN_SEL.FBD at a free spot of the menu's
# VRAM (MAXV: x 1000..1015, y 330..345, next to the Remix's own heads and names), and `msp` (remix/boardmax.py: it drew
# the start of the MAXSPEED sprite) jumps to `mspl`, which links the same POLY_FT4 as the game's labels.
import os, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from asm import asm

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'NotoSans-BlackItalic.ttf')
FBD = '/TITLE/MAIN_SEL.FBD'
MAXV = (1000, 360)                        # VRAM of the 64 x 16 4-bit image (16 x 16 VRAM pixels)
TPAGE = (MAXV[0] // 64) | ((MAXV[1] // 256) << 4)
U0, V0 = (MAXV[0] % 64) * 4, MAXV[1] % 256
CLUT = 0x71FC
EXE_BASE = 0x8000F800
MSP = 0x8001B790                          # boardmax.MSP
MSPL = 0x800296E0                         # after maxanim's maxv / maxw, in the dead function 0x8002957C..0x8002979F
END = 0x800297A0
WHITE, OUTL, SHADE, SHADOW, SHADOW2 = 0, 0xE, 0xA, 0x7, 0x9   # label palette: white, dark outline, grey, orange, darker orange


def vo(x, y): return 20 + (y * 704 + x - 320) * 2


def glyph():
    """-> 16 x 64 array of palette indices (15 = transparent)"""
    f = ImageFont.truetype(FONT, 17)
    im = Image.new('L', (96, 32), 0); ImageDraw.Draw(im).text((6, -4), 'MAX', font=f, fill=255)
    m = np.array(im) > 110
    ys, xs = np.where(m); m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = m.shape
    canvas = np.zeros((16, 64), bool); oy, ox = 1, 4
    canvas[oy:oy + h, ox:ox + w] = m[:16 - oy, :64 - ox]
    M = canvas
    sh = np.zeros_like(M); sh[1:, :-2] |= M[:-1, 2:]; sh[1:, :-1] |= M[:-1, 1:]
    S = sh & ~M
    U = M | S
    D = U.copy(); D[1:] |= U[:-1]; D[:-1] |= U[1:]; D[:, 1:] |= U[:, :-1]; D[:, :-1] |= U[:, 1:]
    O = D & ~U
    out = np.full((16, 64), 15, np.uint8)
    out[O] = OUTL; out[S] = SHADOW
    deep = np.zeros_like(S); deep[1:, :-1] = S[:-1, 1:]; out[S & deep] = SHADOW2
    out[M] = WHITE
    low = np.zeros_like(M); low[:-1] = M[1:]; out[M & ~low] = SHADE        # last row of each letter in grey
    return out


def fbd_op():
    g = glyph()
    rows = b''.join(bytes(int(r[i]) | (int(r[i + 1]) << 4) for i in range(0, 64, 2)) for r in g)
    return [['b', FBD, vo(MAXV[0], MAXV[1] + y), rows[32 * y:32 * y + 32].hex()] for y in range(16)]


def code():
    # mspl(a0 ot entry, a1 prim, a2 x, a3 y (screen), t4 selected) -> v0 = next prim
    # a0 = the screen's frame structures (0x14 bytes each, by the frame buffer index D_8005AE7C): the ordering table
    # entry is *(a0 + 0x14 * index + 4) + 0x34, as in the game's sprite routine func_8005CC78
    S = ['mspl:', 'lui t0, 0x8006', 'lh t0, -0x5184(t0)', 'lui t2, 0xff', 'sll t1, t0, 2', 'addu t1, t1, t0', 'sll t1, t1, 2',
         'addu t1, t1, a0', 'lw t9, 4(t1)', 'ori t2, t2, 0xffff', 'addiu t9, t9, 0x34',
         # addPrim (the entries of the game's ordering tables have a length byte of 0)
         'lw t1, 0(t9)', 'lui t0, 0x900', 'or t3, t1, t0', 'sw t3, 0(a1)', 'and t3, a1, t2', 'sw t3, 0(t9)',
         'lui t0, 0x2c32', 'beqz t4, ml1', 'ori t0, t0, 0x3232', 'lui t0, 0x2c7f', 'ori t0, t0, 0x7f7f',
         'ml1:', 'sw t0, 4(a1)', 'addiu t5, a2, -160', 'addiu t6, a3, -134', 'andi t5, t5, 0xffff', 'sll t6, t6, 16',
         'or t7, t5, t6', 'sw t7, 8(a1)', 'addiu t8, t7, 64', 'sw t8, 16(a1)', 'lui t0, 22', 'addu t7, t7, t0', 'sw t7, 24(a1)',
         'addu t8, t8, t0', 'sw t8, 32(a1)',
         f'lui t0, {CLUT:#x}', f'ori t0, t0, {(V0 << 8) | U0:#x}', 'sw t0, 12(a1)',
         f'lui t0, {TPAGE:#x}', f'ori t0, t0, {(V0 << 8) | (U0 + 63):#x}', 'sw t0, 20(a1)',
         f'addiu t0, zero, {((V0 + 15) << 8) | U0:#x}', 'sw t0, 28(a1)', f'addiu t0, zero, {((V0 + 15) << 8) | (U0 + 63):#x}',
         'sw t0, 36(a1)', 'jr ra', 'addiu v0, a1, 40']
    return asm(S, MSPL)


def ops(disc):
    ex = disc.read_file('/SCES_009.92'); we = lambda a: struct.unpack_from('<I', ex, a - EXE_BASE)[0]
    c, l = code(); assert c[-1][0] < END, hex(c[-1][0])
    J = lambda t: (2 << 26) | ((t >> 2) & 0x3ffffff)
    out = [['w', '/SCES_009.92', a - EXE_BASE, we(a), x] for a, x in c]
    out += [['w', '/SCES_009.92', MSP - EXE_BASE, we(MSP), J(l['mspl'])], ['w', '/SCES_009.92', MSP + 4 - EXE_BASE, we(MSP + 4), 0]]
    return out + fbd_op()


def merge(disc, max_ops):
    new = ops(disc); keys = {(op[0], op[1], op[2]) for op in new}
    return [op for op in max_ops if (op[0], op[1], op[2]) not in keys] + new


if __name__ == '__main__':
    g = glyph()
    for r in g: print(''.join('.' if v == 15 else '%x' % v for v in r))
    c, l = code(); print('code end', hex(c[-1][0]))
