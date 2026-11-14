# R-E-M-I-X letters in the Board Park (part of the mod `crew`, v60), as the S-K-A-T-E letters of Tony Hawk's: five
# letters float along the course (on the snow, and at the top of the two big jumps and in the bowl); riding through a
# letter collects it; the five in one run unlock Jicchi, Nick and Kelly for good (bit 31 of the saved word 0x80057438,
# which crew's `acomp` reads instead of the 100 % of the progress page).
#
# BP.BIN: the main loop calls func_80074344 (an empty function) every frame at 0x8005C31C (as HP's, which hplive uses):
# it goes through `rlx` (two dead functions of BP, 0x8006EA48..0x8006EE54), which calls it, then:
#   - the player's racer: D_8009FE24[0]; position + 0x2C / 0x30 / 0x34 (32-bit world units: a rider is about 265 high,
#     y down); camera + 0x6D8, its projection distance H at + 0xA (150);
#   - a new run (the position jumps by more than JUMP) clears the letters taken;
#   - each letter not taken: taken when the rider is within R on the three axes (a sound); else, within FAR, drawn as a
#     textured quad: camera point = (GsWSMATRIX 0x80058E20 (letter - rider)) >> 12 + translation 0x80058E34 (the rider
#     is the world's origin, as boost.py found in the Boarder Cross), screen = x H / z, y H / z, half size SZ H / z;
#   - the five letters at the top left, the taken ones bright; all five: the unlock bit is set, the row blinks a while;
#   - the letters' images: the REMIX logo's font (remix/fonts, not a game file), 24 x 22, 4 bits, one 15-colour
#     palette, sent to free VRAM (x 384.., y 0; palette x 448, y 192) every frame, from three other dead functions.
# Primitives: D_80058E0C, ordering table entry *(*(D_800A001C) + 4) + 0xC (the HUD's, as hplive).
import struct
import numpy as np
from asm import asm

OVL = 0x8005AEA8
HOOK, HOOK_FN = 0x8005C31C, 0x80074344
CODE, CODE_END = 0x8006EA48, 0x8006EE54          # dead functions of BP.BIN (no call, jump or pointer to any of their words)
DATA_CAVES = [(0x8008ECAC, 0x8008EFF0), (0x80093FDC, 0x8009414C), (0x80070A64, 0x80070BC8)]
TAB, TAB_END = 0x8007CF1C, 0x8007D02C
RACERS, WS, WST, PRIMS, FRAME = 0x8009FE24, 0x80058E20, 0x80058E34, 0x80058E0C, 0x800A001C
FLAGS, DONE_BIT = 0x80057438, 0x80000000          # saved word (mod options' switches use bits 0..20)
LOADIMAGE, SOUND = 0x80029B7C, 0x80015BFC
NEWS_MASK = 0x8001E634                            # mod news: its MASK (remix/news.py NEWS + 4)
LW, LH = 24, 22                                   # letter image (pixels)
VX, VY, CX, CY = 384, 0, 448, 192                 # VRAM: images, palette
TPAGE = VX // 64
CLUT = (CX >> 4) | (CY << 6)
R, FAR, SZ, ZMIN, JUMP = 450, 14000, 220, 100, 3000
UP = 150                                          # letters this much above the recorded position (the rider's feet)
# from a run recorded in the emulator (positions of the rider, `bp_traj`): on the snow at the start, the top of the
# first jump, on the snow, the top of the second jump, in the bowl at the end
POS = [(-22977, 12085, -45325), (-69382, 39531, -82123), (-89030, 46727, -88421), (-94384, 55986, -119112), (-88362, 68445, -149616)]
HUD_X, HUD_Y, HUD_S, HUD_DX = -148, -100, 9, 18


def H(a): return ((a + 0x8000) >> 16) & 0xffff
def L(a): return a - (((a + 0x8000) >> 16) << 16)
def la(r, a): return [f'lui {r}, {H(a)}', f'addiu {r}, {r}, {L(a)}']


def images():
    """-> 5 x (LH rows of LW / 2 bytes), 16 palette words"""
    import title
    from PIL import Image
    cells = []
    for ch in 'REMIX':
        a = title.word(ch, 22, 8); al = a[..., 3] > 0; ys, xs = np.where(al)
        a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        im = Image.fromarray(a, 'RGBA'); s = min(LW / im.width, LH / im.height, 1.0)
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.NEAREST)
        c = Image.new('RGBA', (LW, LH)); c.paste(im, ((LW - im.width) // 2, (LH - im.height) // 2)); cells.append(np.array(c))
    strip = np.concatenate(cells, 1); al = strip[..., 3] > 0
    q = Image.fromarray(strip[..., :3].copy()).quantize(15, method=Image.MEDIANCUT, dither=Image.NONE)
    idx = np.array(q) + 1; idx[~al] = 0
    pal = np.array(q.getpalette()[:45]).reshape(15, 3)
    clut = [0] + [0x8000 | (b >> 3) << 10 | (g >> 3) << 5 | (r >> 3) for r, g, b in pal]
    out = []
    for k in range(5):
        px = idx[:, k * LW:(k + 1) * LW].astype(np.uint8)
        out.append(bytes((px[:, 0::2] | (px[:, 1::2] << 4)).flatten()))
    return out, clut


def layout():
    """data addresses: images, palette, tables, variables"""
    imgs, clut = images(); n = len(imgs[0]); A = {}
    a = DATA_CAVES[0][0]
    for k in range(3): A[f'img{k}'] = a + n * k
    A['clut'] = a + 3 * n; assert A['clut'] + 32 <= DATA_CAVES[0][1]
    A['img3'] = DATA_CAVES[1][0]; assert A['img3'] + n <= DATA_CAVES[1][1]
    A['img4'] = DATA_CAVES[2][0]; assert A['img4'] + n <= DATA_CAVES[2][1]
    t = TAB
    for name, size in (('lpos', 60), ('rects', 48), ('ptrs', 24), ('vars', 24)): A[name] = t; t += size
    assert t <= TAB_END
    return A, imgs, clut


MASK, LX, LY, LZ, OLD, DONE = 0, 4, 8, 12, 16, 20     # vars
PROJ_AT, PROJ_END = 0x8006AB74, 0x8006AC78        # two more dead functions of BP
QUAD_AT, QUAD_END = 0x800943B8, 0x80094480


def PROJ():
    # rproj: t0..t2 = letter - rider -> t0 = sx, t1 = sy, t2 = z (camera); rows of GsWSMATRIX (3 halfwords) + translation
    return ['rproj:', *la('t9', WS), 'move t8, zero', 'addiu t7, sp, 0x18',
            'rpr:', 'lh t3, 0(t9)', 'lh t4, 2(t9)', 'lh t5, 4(t9)', 'nop', 'mult t3, t0', 'mflo t6', 'nop', 'nop', 'mult t4, t1', 'mflo t3',
            'nop', 'nop', 'mult t5, t2', 'mflo t4', 'addu t6, t6, t3', 'addu t6, t6, t4', 'sra t6, t6, 12', 'sll t3, t8, 2', 'addu t3, t3, t7',
            f'lui t4, {H(WST)}', 'sll t5, t8, 2', 'addu t4, t4, t5', f'lw t4, {L(WST)}(t4)', 'nop', 'addu t6, t6, t4', 'sw t6, 0(t3)',
            'addiu t8, t8, 1', 'slti at, t8, 3', 'bnez at, rpr', 'addiu t9, t9, 6',
            'lw t2, 0x20(sp)', 'nop', 'blez t2, rp9', 'nop', 'lw t0, 0x18(sp)', 'lw t1, 0x1c(sp)', 'mult t0, s6', 'mflo t0', 'nop', 'nop',
            'div t0, t2', 'mflo t0', 'nop', 'nop', 'mult t1, s6', 'mflo t1', 'nop', 'nop', 'div t1, t2', 'mflo t1', 'rp9:', 'jr ra', 'nop']


def QUAD():
    # rq: a0 = x, a1 = y (screen, from its centre), a2 = half size, a3 = letter, t9 = code + colour; s4 = OT entry, s5 = prims
    return ['rq:', 'subu t0, a0, a2', 'addu t1, a0, a2', 'subu t2, a1, a2', 'addu t3, a1, a2', 'andi t0, t0, 0xffff', 'andi t1, t1, 0xffff',
            'sll t2, t2, 16', 'sll t3, t3, 16', 'sll t4, a3, 3', 'sll t5, a3, 4', 'addu t4, t4, t5',      # u = 24 letter
            'sw t9, 4(s5)', 'or t5, t2, t0', 'sw t5, 8(s5)', 'or t5, t2, t1', 'sw t5, 0x10(s5)', 'or t5, t3, t0', 'sw t5, 0x18(s5)', 'or t5, t3, t1', 'sw t5, 0x20(s5)',
            f'lui t5, {CLUT}', 'or t5, t5, t4', 'sw t5, 0xc(s5)', f'lui t5, {TPAGE}', f'addiu t6, t4, {LW - 1}', 'or t5, t5, t6', 'sw t5, 0x14(s5)',
            f'addiu t5, t4, {(LH - 1) << 8}', 'sw t5, 0x1c(s5)', f'addiu t5, t6, {(LH - 1) << 8}', 'sw t5, 0x24(s5)',
            'lw t0, 0(s4)', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'and t1, t0, t2', 'lui t3, 0x900', 'or t1, t1, t3', 'sw t1, 0(s5)',
            'lui t3, 0xff00', 'and t0, t0, t3', 'and t1, s5, t2', 'or t0, t0, t1', 'sw t0, 0(s4)', 'jr ra', 'addiu s5, s5, 40']


def code(A):
    V = A['vars']
    S = ['rlx:', 'addiu sp, sp, -0x58', 'sw ra, 0x50(sp)', 'sw s0, 0x30(sp)', 'sw s1, 0x34(sp)', 'sw s2, 0x38(sp)', 'sw s3, 0x3c(sp)',
         'sw s4, 0x40(sp)', 'sw s5, 0x44(sp)', 'sw s6, 0x48(sp)', 'sw s7, 0x4c(sp)',
         f'jal {HOOK_FN:#x}', 'nop', 'sw v0, 0x2c(sp)',
         f'lui t0, {H(RACERS)}', f'lw s0, {L(RACERS)}(t0)', 'nop', 'beqz s0, rx9', 'nop', *la('s7', V),
         # images and palette to VRAM
         'move s1, zero',
         'rl1:', 'sll t0, s1, 3', *la('a0', A['rects']), 'addu a0, a0, t0', 'sll t0, s1, 2', *la('a1', A['ptrs']), 'addu a1, a1, t0',
         f'jal {LOADIMAGE:#x}', 'lw a1, 0(a1)', 'addiu s1, s1, 1', 'slti at, s1, 6', 'bnez at, rl1', 'nop',
         # new run: the position jumped
         'lw t0, 0x2c(s0)', 'lw t1, 0x30(s0)', 'lw t2, 0x34(s0)', f'lw t3, {LX}(s7)', f'lw t4, {LY}(s7)', f'lw t5, {LZ}(s7)',
         f'sw t0, {LX}(s7)', f'sw t1, {LY}(s7)', f'sw t2, {LZ}(s7)', 'subu t3, t0, t3', 'subu t4, t1, t4', 'subu t5, t2, t5']
    for r in ('t3', 't4', 't5'):
        S += [f'bgez {r}, ra_{r}', 'nop', f'subu {r}, zero, {r}', f'ra_{r}:', f'slti at, {r}, {JUMP}', 'beqz at, rnew', 'nop']
    S += ['j rgo', 'nop', 'rnew:', f'sw zero, {MASK}(s7)', f'sw zero, {OLD}(s7)', f'sw zero, {DONE}(s7)',
          # OT entry, primitives, camera H
          'rgo:', f'lui t0, {H(FRAME)}', f'lw t0, {L(FRAME)}(t0)', 'nop', 'lw s4, 4(t0)', f'lui t0, {H(PRIMS)}', f'lw s5, {L(PRIMS)}(t0)',
          'addiu s4, s4, 0xc', 'lw t0, 0x6d8(s0)', 'nop', 'lh s6, 0xa(t0)',
          # the letters in the world
          'move s2, zero', *la('s3', A['lpos']),
          'rlp:', f'lw t9, {MASK}(s7)', 'addiu t8, zero, 1', 'sllv t8, t8, s2', 'and t7, t9, t8', 'bnez t7, rln', 'nop',
          'lw t0, 0(s3)', 'lw t1, 4(s3)', 'lw t2, 8(s3)', 'lw t3, 0x2c(s0)', 'lw t4, 0x30(s0)', 'lw t5, 0x34(s0)',
          'subu t0, t0, t3', 'subu t1, t1, t4', 'subu t2, t2, t5', 'move t3, t0', 'move t4, t1', 'move t5, t2']
    for r in ('t3', 't4', 't5'):
        S += [f'bgez {r}, rb_{r}', 'nop', f'subu {r}, zero, {r}', f'rb_{r}:']
    S += [f'slti at, t3, {R}', 'beqz at, rfar', f'slti at, t4, {R}', 'beqz at, rfar', f'slti at, t5, {R}', 'beqz at, rfar', 'nop',
          # taken
          'or t9, t9, t8', f'sw t9, {MASK}(s7)', 'addiu a0, zero, 3', f'jal {SOUND:#x}', 'addiu a1, zero, 0x7f', 'j rln', 'nop',
          'rfar:', f'slti at, t3, {FAR}', 'beqz at, rln', f'slti at, t4, {FAR}', 'beqz at, rln', f'slti at, t5, {FAR}', 'beqz at, rln', 'nop',
          'jal rproj', 'nop', f'slti at, t2, {ZMIN}', 'bnez at, rln', 'nop',
          # half size SZ H / z, at least 2
          f'addiu t3, zero, {SZ}', 'mult t3, s6', 'mflo t3', 'nop', 'nop', 'div t3, t2', 'mflo a2', 'nop', 'nop',
          'slti at, a2, 2', 'beqz at, rsz', 'nop', 'addiu a2, zero, 2', 'rsz:',
          'move a0, t0', 'move a1, t1', 'move a3, s2', 'lui t9, 0x2c80', 'jal rq', 'ori t9, t9, 0x8080',
          'rln:', 'addiu s2, s2, 1', 'slti at, s2, 5', 'bnez at, rlp', 'addiu s3, s3, 12',
          # all five: unlock (saved word), the row blinks
          f'lw t0, {MASK}(s7)', f'lw t1, {OLD}(s7)', f'sw t0, {OLD}(s7)', 'addiu t2, zero, 31', 'bne t0, t2, rhud', 'nop', 'beq t1, t2, rhud', 'nop',
          f'lui t3, {H(FLAGS)}', f'lw t4, {L(FLAGS)}(t3)', f'lui t5, {DONE_BIT >> 16:#x}', 'or t4, t4, t5', f'sw t4, {L(FLAGS)}(t3)',
          'addiu t4, zero, 200', f'sw t4, {DONE}(s7)',
          # the banner of the mod news back in the menu: JICCHI NICK KELLY UNLOCKED (its MASK, bit 0x10000)
          f'lui t3, {H(NEWS_MASK)}', f'lw t4, {L(NEWS_MASK)}(t3)', 'lui t5, 1', 'or t4, t4, t5', f'sw t4, {L(NEWS_MASK)}(t3)',
          'addiu a0, zero, 3', f'jal {SOUND:#x}', 'addiu a1, zero, 0x7f',
          # the row at the top left
          'rhud:', f'lw t0, {DONE}(s7)', 'nop', 'blez t0, rh0', 'addiu t0, t0, -1', f'sw t0, {DONE}(s7)', 'rh0:', 'move s2, zero',
          'rhl:', f'lw t9, {MASK}(s7)', 'addiu t8, zero, 1', 'sllv t8, t8, s2', 'and t7, t9, t8', 'lui t9, 0x2c28', 'beqz t7, rh1', 'ori t9, t9, 0x2828',
          'lui t9, 0x2c80', 'ori t9, t9, 0x8080', f'lw t0, {DONE}(s7)', 'nop', 'andi t0, t0, 8', 'beqz t0, rh1', 'nop', 'lui t9, 0x2cff', 'ori t9, t9, 0xffff',
          'rh1:', f'addiu t0, zero, {HUD_DX}', 'mult t0, s2', 'mflo a0', f'addiu a0, a0, {HUD_X}', f'addiu a1, zero, {HUD_Y}', f'addiu a2, zero, {HUD_S}',
          'jal rq', 'move a3, s2', 'addiu s2, s2, 1', 'slti at, s2, 5', 'bnez at, rhl', 'nop',
          f'lui t0, {H(PRIMS)}', f'sw s5, {L(PRIMS)}(t0)',
          'rx9:', 'lw v0, 0x2c(sp)', 'lw ra, 0x50(sp)', 'lw s0, 0x30(sp)', 'lw s1, 0x34(sp)', 'lw s2, 0x38(sp)', 'lw s3, 0x3c(sp)',
          'lw s4, 0x40(sp)', 'lw s5, 0x44(sp)', 'lw s6, 0x48(sp)', 'lw s7, 0x4c(sp)', 'jr ra', 'addiu sp, sp, 0x58']
    P, lp = asm(PROJ(), PROJ_AT); assert P[-1][0] < PROJ_END, hex(P[-1][0])
    Q, lq = asm(QUAD(), QUAD_AT); assert Q[-1][0] < QUAD_END, hex(Q[-1][0])
    c, lb = asm(S, CODE, {**lp, **lq})
    assert c[-1][0] < CODE_END, hex(c[-1][0])
    return c + P + Q, {**lb, **lp, **lq}


def data(A, imgs, clut):
    """{address: bytes}"""
    D = {A[f'img{k}']: imgs[k] for k in range(5)}
    D[A['clut']] = struct.pack('<16H', *clut)
    D[A['lpos']] = b''.join(struct.pack('<3i', x, y - UP, z) for x, y, z in POS)
    D[A['rects']] = b''.join(struct.pack('<4h', VX + LW // 4 * k, VY, LW // 4, LH) for k in range(5)) + struct.pack('<4h', CX, CY, 16, 1)
    D[A['ptrs']] = struct.pack('<6I', *[A[f'img{k}'] for k in range(5)], A['clut'])
    D[A['vars']] = bytes(24)
    return D


def ops(disc):
    bp = disc.read_file('/BP.BIN'); wb = lambda a: struct.unpack_from('<I', bp, a - OVL)[0]
    A, imgs, clut = layout(); c, lb = code(A)
    out = [['w', '/BP.BIN', a - OVL, wb(a), w] for a, w in c]
    for a, b in data(A, imgs, clut).items():
        b = b + bytes((-len(b)) % 4)
        out += [['w', '/BP.BIN', a + i - OVL, wb(a + i), struct.unpack_from('<I', b, i)[0]] for i in range(0, len(b), 4)]
    assert wb(HOOK) == (3 << 26) | ((HOOK_FN >> 2) & 0x3ffffff)
    out.append(['w', '/BP.BIN', HOOK - OVL, wb(HOOK), (3 << 26) | ((lb['rlx'] >> 2) & 0x3ffffff)])
    return out


def sites():
    return [('/BP.BIN', HOOK)]
