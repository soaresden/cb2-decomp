# Jicchi, Nick and Kelly in the rankings (part of the mod `crew`, v26): their records keep their own rider number (7, 8,
# 9) and the ranking screens show their heads.
#
# The ranking screens of FREE, HP, BP and OMT (same code in each overlay) draw, per record, the head of its rider with
# a 16x16 sprite (func_80012B58) whose u, v, palette come from a table of 7 words copied on the stack (sp + 0x38 + 4 r)
# and whose texture page comes from a DR_MODE (func_80012BDC) with a value from another table (sp + 0x58 + 2 r: 0x17 =
# 4 bits, VRAM (448, 256)). That page is full; VRAM (448, 0) is empty on these screens. Rider 7..9:
#   ia (in place of "sll v1, v1, 2 / addu v0, v0, v1"): the icon word comes from TAB, after the three heads (12 x 16
#      halfwords) and their palettes (3 rows of 16) are sent to VRAM (448, 0) / (480, 0) by LoadImage;
#   tb (in place of "addu v1, sp, v1", its delay slot reads the table): texture page 7 = VRAM (448, 0).
# The records: the record function of each mode copies its rider argument into a register at its start ("addu sX, aY,
# zero"); that instruction jumps to rr, which puts 6 + ALIAS there when the alias is chosen for that base rider in an
# allowed mode, then jumps back.
# The heads are the BOARDER screen's (crew icons in TITLE/MAIN_SEL.FBD), copied by the patcher ('fcopy').
import struct
from asm import asm

OVL = 0x8005AEA8
LOADIMAGE = 0x80029B7C
# file: kind, data block (upload) or None, code cave, ranking sites (icon site; page = + 0x1C; board test = + 0x2C),
# record site (address, sX, aY) or None
SITES = {
    '/FREE.BIN': ('upload', 0x8007F528, (0x8007F728, 0x8007FB94), [0x800897A8], (0x80089F34, 's7', 'a1')),
    '/HP.BIN': ('upload', 0x80079DBC, (0x80079FBC, 0x8007A1EC), [0x80089174], (0x80089754, 's4', 'a0')),
    '/BP.BIN': ('upload', 0x8006A448, (0x8006A648, 0x8006A840), [0x80088F20], None),
    '/OMT.BIN': ('upload', 0x8007D6F4, (0x8007D8F4, 0x8007DD60), [0x80086FA4], (0x80087450, 's5', 'a1')),
    '/MODE_SEL.BIN': ('upload', 0x8005C6B0, (0x800653E4, 0x8006562C), [0x8006B680, 0x8006CEC4, 0x8006DED0], None),
    '/MAIN_SEL.BIN': ('menu', None, (0x80077EC0, 0x80077FA8), [0x800776C0, 0x80078ABC, 0x8007996C], None),   # after news' table
}
MENU_PAGE = 0x1F                                # MAIN_SEL: the BOARDER row's heads, VRAM (960, 324), palettes (928.., 340..)
ICON_VRAM, CLUT_VRAM = (448, 0), (480, 0)
PAGE = ICON_VRAM[0] >> 6                       # GetTPage(4 bits, 0, 448, 0)
PIX, CLUTS, RECT1, RECT2, TAB = 0, 384, 480, 488, 496      # offsets in the data block (end 508)
DATA_SIZE = 508
REGS = {r: i for i, r in enumerate('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7'.split())}


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)


def data_words():
    """rects and table (the pixels and palettes are copied by the patcher)"""
    d = struct.pack('<4h', ICON_VRAM[0], ICON_VRAM[1], 12, 16) + struct.pack('<4h', CLUT_VRAM[0], CLUT_VRAM[1], 16, 3)
    d += b''.join(struct.pack('<I', (((CLUT_VRAM[1] + k) << 6 | CLUT_VRAM[0] >> 4) << 16) | 16 * k) for k in range(3))
    return d


def code(f, aliasv, basev, modesv, menu_tab):
    kind, data, (lo, hi), sites, rec = SITES[f]
    S = ['ia:', 'slti at, v1, 7', 'beqz at, ia1', 'sll v1, v1, 2', 'jr ra', 'addu v0, v0, v1', 'ia1:']
    if kind == 'upload':
        S += ['addiu sp, sp, -0x30', 'sw ra, 0x28(sp)', 'sw a0, 0x10(sp)', 'sw a1, 0x14(sp)', 'sw a2, 0x18(sp)', 'sw a3, 0x1c(sp)', 'sw v1, 0x20(sp)',
              f'lui a0, {H(data + RECT1)}', f'addiu a0, a0, {L(data + RECT1)}', f'lui a1, {H(data + PIX)}', f'jal {LOADIMAGE}', f'addiu a1, a1, {L(data + PIX)}',
              f'lui a0, {H(data + RECT2)}', f'addiu a0, a0, {L(data + RECT2)}', f'lui a1, {H(data + CLUTS)}', f'jal {LOADIMAGE}', f'addiu a1, a1, {L(data + CLUTS)}',
              'lw v1, 0x20(sp)', 'lw a0, 0x10(sp)', 'lw a1, 0x14(sp)', 'lw a2, 0x18(sp)', 'lw a3, 0x1c(sp)', 'lw ra, 0x28(sp)',
              f'lui v0, {H(data + TAB - 28)}', f'addiu v0, v0, {L(data + TAB - 28)}', 'addu v0, v0, v1', 'jr ra', 'addiu sp, sp, 0x30']
        page = PAGE
    else:
        S += ['lui v0, TABH', 'addiu v0, v0, TABL', 'addu v0, v0, v1', 'jr ra', 'nop']      # TAB: right after the code
        page = MENU_PAGE
    S += ['tb:', 'slti at, v1, 14', 'beqz at, tb1', 'addu v1, sp, v1', 'jr ra', 'lhu a2, 0x58(v1)', 'tb1:', 'jr ra', f'addiu a2, zero, {page}']
    # board test ("rider < 5": Boss, Gray, Snowman have no board label): the aliases count as 0..2
    S += ['bc:', 'lbu v1, 0x8(s3)', 'nop', 'slti at, v1, 7', 'bnez at, bc1', 'nop', 'addiu v1, v1, -7', 'bc1:', 'jr ra', 'nop']
    if rec:
        ra, sx, ay = rec
        S += ['rr:', f'move {sx}, {ay}', f'lui at, {H(aliasv)}', f'lw t0, {L(aliasv)}(at)', 'nop', 'beqz t0, rr9', f'lui at, {H(basev)}',
              'addu at, at, t0', f'lbu t1, {L(basev)}(at)', 'nop', f'bne t1, {ay}, rr9', 'lui at, 0x8005', 'lw t2, 0x7420(at)', f'lui at, {H(modesv)}',
              f'lw at, {L(modesv)}(at)', 'nop', 'srlv at, at, t2', 'andi at, at, 1', 'beqz at, rr9', 'nop', f'addiu {sx}, t0, 6',
              'rr9:', f'j {ra + 8}', 'nop']
    if kind == 'menu':     # table of the three heads right after the code
        c0, _ = asm([x.replace('TABH', '0').replace('TABL', '0') for x in S], lo)
        tab = c0[-1][0] + 4
        S = [x.replace('TABH', str(H(tab - 28))).replace('TABL', str(L(tab - 28))) for x in S]
    c, l = asm(S, lo)
    if kind == 'menu':
        end = c[-1][0] + 4; l['tab'] = end
        c += [(end + 4 * k, w) for k, w in enumerate(menu_tab)]
    assert c[-1][0] < hi, (f, hex(c[-1][0]))
    return c, l


def ops(disc, aliasv, basev, modesv, fbd, icon_x, icon_y, clut_x, clut_y, strip_idx):
    """-> ops for the overlays ('w' words, then 'fcopy' of the heads and palettes from the FBD)"""
    J = lambda op, t: (op << 26) | ((t >> 2) & 0x3ffffff)
    vo = lambda x, y: 20 + (y * 704 + x - 320) * 2               # TITLE/MAIN_SEL.FBD (x 320.., 704 wide)
    menu_tab = [((((clut_y + i // 6) << 6) | ((clut_x + 16 * (i % 6)) >> 4)) << 16) | ((icon_y - 256) << 8) | 16 * i for i in strip_idx]
    out = []
    for f, (kind, data, cave, sites, rec) in SITES.items():
        d = disc.read_file(f); w = lambda a: struct.unpack_from('<I', d, a - OVL)[0]
        c, l = code(f, aliasv, basev, modesv, menu_tab)
        P = [(a, x) for a, x in c]
        for s_ in sites:
            assert w(s_) == 0x00031880 and w(s_ + 4) == 0x00431021, f        # sll v1, v1, 2 / addu v0, v0, v1
            assert w(s_ + 0x1C) == 0x03A31821 and w(s_ + 0x20) == 0x94660058, f    # addu v1, sp, v1 / lhu a2, 0x58(v1)
            assert w(s_ + 0x2C) == 0x92630008 and w(s_ + 0x30) == 0 and w(s_ + 0x34) == 0x2C630005, f   # lbu v1, 8(s3) / nop / sltiu v1, v1, 5
            P += [(s_, J(3, l['ia'])), (s_ + 4, 0), (s_ + 0x1C, J(3, l['tb'])), (s_ + 0x2C, J(3, l['bc']))]
        if rec:
            ra, sx, ay = rec
            assert w(ra) == (REGS[ay] << 21) | (REGS[sx] << 11) | 0x21, (f, hex(w(ra)))
            P.append((ra, J(2, l['rr'])))
        if kind == 'upload':
            dw = data_words()
            P += [(data + RECT1 + i, struct.unpack_from('<I', dw, i)[0]) for i in range(0, len(dw), 4)]
        out += [['w', f, a - OVL, w(a), x] for a, x in P]
        if kind == 'upload':
            segs = [[vo(icon_x + 4 * strip_idx[0], icon_y + y), data - OVL + PIX + 24 * y, 24] for y in range(16)]
            segs += [[vo(clut_x + 16 * (i % 6), clut_y + i // 6), data - OVL + CLUTS + 32 * k, 32] for k, i in enumerate(strip_idx)]
            out.append(['fcopy', fbd, f, segs])
    return out
