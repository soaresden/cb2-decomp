# In-game REMIX screen (mod `options`, v26..v37): on the mode select screen, a REMIX entry under the OPTIONS sign (Down
# from OPTIONS, Up back, X opens it): a black screen in the game's style, title REMIX, three tabs (TABS: RACE, RIDERS,
# GAME; Left / Right), Up / Down picks a line, X switches it (UNLOCK EVERYTHING: a warning, then X again), Triangle or
# Circle goes back. (v26..v36: a panel shown while R1 was held.)
#
# The switches are bits of the word 0x80057438 (bit set = off; line i = bit i), in the progress block that
# the game saves on the memory card but never reads (see docs/progression.md; INIT zeroes it): they follow the save.
#   - radar tests bit 64 (the line), bit 128 (the ranking panel), bit 17 (falls as a number);
#   - rear, hplive, news test their bit themselves;
#   - air and ramming are switched where their code lives in the exe (always in memory): every frame of the mode
#     select screen, the words of PATCH get their "on" or "off" value (air: three branches of the exe routines md / ax /
#     rm made unconditional, as if no d-pad, no charge, no remap; ramming: the entry of kc becomes a jump to the game's
#     own collision response). A word is only written when it holds one of its two values (mod absent: untouched);
#     after a write, FlushCache.
# MODE_SEL:
#   - input: the mode select's pad routine (func_8005CCE4, called at 0x8005CB94) goes through `pw`: the game's pad words
#     (0x800832BA..0x800832C5), then, while the mode select screen is drawn (`alive`, set by opt every frame), the REMIX
#     entry (game cursor 0x80070B2C on OPTIONS = 5, Down) and the screen; while they have the input, the game's pad
#     words are cleared (its cursor stays on OPTIONS, the game's own OPTIONS screen is not affected).
#   - drawing: the TV function (func_80064200, every frame, s4 = its OT table, s1 = frame buffer index) calls
#     func_80028BDC (GetClut) at 0x800643E4: that call goes through opt, which applies the switches, installs the
#     switches' block (toggles.py), and draws the REMIX label or the screen with the game's text routine
#     (func_80012CA0, menu font) into a private primitive buffer (0x801F8000 + 0x2000 per frame buffer), on a black TILE.
#   - code and data: MODE_SEL's 84th sector (toggles.SCREEN) and dead functions of MODE_SEL and the exe (CAVES).
import struct
from asm import asm

OVL = 0x8005AEA8
HOOK, HOOK_FN = 0x800643E4, 0x80028BDC
TEXT, FONT, CLUT, PAD = 0x80012CA0, 0x80070648, 0x733E, 0x800832BA
FLUSH = 0x8003CB2C
FLAGS = 0x80057438
R1, L1, R2 = 0x8, 0x4, 0x2
PRIMS = 0x801F8000
CAVES = [(0x800654A8, 0x8006562C), (0x8006F680, 0x8006F71C), (0x8006F7C4, 0x8006F83C),   # MODE_SEL (after crewrank's code in the first)
         (0x80031180, 0x8003120C), (0x8003BD98, 0x8003BE10), (0x80040AA4, 0x80040B0C),     # exe: dead functions kept for this mod
         (0x8001829C, 0x80018320), (0x8003EAC4, 0x8003EB30), (0x800123C8, 0x80012448),   # (0x8003EB30.. : snowtod)     # (see crew.CAVES)
         (0x80083844, 0x80083C00)]    # end of MODE_SEL's 82nd sector (after the progress page; padded when it is absent)
DATA = (0x8005C8B0, 0x8005C968)        # after crewrank's data (code since v37)
import toggles
SCR_DATA = toggles.SCREEN[0]           # the screen's data: start of MODE_SEL's 84th sector
X0, X1, Y0, DY = -150, 70, -64, 13
LINES = ['REAR VIEW (O)', 'LIVE HALF-PIPE MARKS', 'NOTICE WITH UNLOCK SCREEN', 'AIR CONTROL', 'MAKE RIDERS FALL AGAINST THEM', 'WIDESCREEN 16:9',
         'RACE RADAR LINE', 'RACE RANKING',
         # the other mods (remix/toggles.py: bits 8..16, in the order of toggles.BITS)
         'SPECIAL BOARDS ALWAYS', 'NEW HARD+MIRROR CUP', 'BOSS GRAY SNOWMAN IN COMP', 'HIDDEN OUTFITS FOR GIRLS', 'CAN MAX RIDERS AND BOARD',
         'BIG AIR MASTER KEYS SHOWN',
         'PROGRESS PAGE (SELECT)', 'SKIP QUALIFYING (SELECT)', 'JICCHI NICK KELLY PLAYABLE',
         'FALLS AS A NUMBER',                   # bit 17 (radar.py: one ball and x13 instead of the row of balls)
         'UNLOCK EVERYTHING',                   # line i = bit i of the flags word (bit set = off)
         'SSX STYLE BOOST',                    # bit 19 (remix/boost.py, with the mod radar)
         'RETRY ROUND (3 PER CUP)']            # bit 20 (remix/boost.py: RETRY on GAME OVER replays the Boarder Cross)
UNLOCK_LINE = 18                                # an action, not a switch: R2 shows the warning, R2 again unlocks (its bit = done)
INV = 32 | 1 << UNLOCK_LINE            # lines whose bit set means ON (off by default)
VIS = 10                               # lines shown at a time: the list scrolls with the cursor
WARN = ['X AGAIN UNLOCKS ALL RIDERS,', 'COURSES, BOARDS, MIRROR, HARD,', 'TROPHIES. SAVED. NO UNDO!']     # <= 30 letters (box)
# the progress block as a 100 % game (remix/progress.py): courses, riders (Boss, Gray, Snowman), SPECIAL boards,
# Mirror, Hard, the 30 Free Style trophies; the save keeps it
UNLOCK = [(0x743C, 10, 'h'), (0x743E, 10, 'h'), (0x7440, 0x7F, 'o'), (0x7442, 7, 'o'), (0x7444, 1, 'h'), (0x7446, 1, 'h'),
          (0x7448, 0x3FF, 'h'), (0x744A, 0x3FF, 'h'), (0x744C, 0x3FF, 'h')]
TITLE = 'REMIX OPTIONS'
RESP = 0x80073714                      # SBC2: the game's racer collision response (kc's own target)
J = lambda op, t: (op << 26) | ((t >> 2) & 0x3ffffff)
# (address, word on, word off, bit)
PATCH = [(0x8004FA44, 0x10600012, 0x10000012, 8),     # md: beqz v1 -> b (no modulation)
         (0x8004FAC8, 0x15E00013, 0x10000013, 8),     # ax: bnez t7 -> b (no charge)
         (0x8004FB28, 0x1480001D, 0x1000001D, 8),     # rm: bnez a0 -> b (no remap)
         (0x80028BF4, 0x27BDFFE0, J(2, RESP), 16),    # kc: -> j response
         (0x80028BF8, 0xAFBF001C, 0, 16),
         # widescreen: X scale of the matrix 0x80059288 (identity copied by the libgs init func_8002DE88, then only
         # read by the view functions): 0.75 = the game itself renders a 16:9 field (to show stretched to 16:9, with
         # the emulator's own widescreen hack off), as PeterDelta's DuckStation cheat for this disc (A7059288 10000C00)
         (0x80059288, 0x00001000, 0x00000C00, 32)]


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)


# the REMIX screen: three tabs of switches (line numbers = bits), in the game's style (black, title at the top left)
TABS = [('RACE', [0, 19, 20, 6, 7, 17, 1, 3, 4, 13]),
        ('RIDERS', [10, 16, 11, 12, 8]),
        ('GAME', [9, 15, 14, 2, 5, 18])]
UP, RIGHT, DOWN, LEFT, TRI, CIRC, CROSS = 0x1000, 0x2000, 0x4000, 0x8000, 0x10, 0x20, 0x40
PADV = 0x800832BA                      # MODE_SEL's pad words (held, ...: 0x800832BA..0x800832C5), set by func_8005CCE4
PAD_CALL, PAD_FN = 0x8005CB94, 0x8005CCE4
CURSOR, OPTIONS_ITEM = 0x80070B2C, 5   # the mode select cursor (COMPETITION 0 .. BOARD PARK 4, OPTIONS 5)
LABEL_XY = (78, 92)                    # "REMIX" under the OPTIONS sign (menu font, before v45)
# v45: the label and the screen's title are the title screen's REMIX (title.word: Noto Sans Black Italic, gold gradient,
# outline, tilted), made small at build time, 16 colours, sent to free VRAM of the mode select (x 448.., y 0; palette
# y 64) every frame and drawn as a SPRT (+ DR_TPAGE); the label is dim, and pulses when the cursor is on it
LOGO_SIZE, LOGO_VRAM, LOGO_CLUT = 16, (448, 0), (448, 64)
LOGO_XY, LOGO_TITLE_XY = (76, 80), (-152, -116)
LOADIMAGE = 0x80029B7C


def logo():
    """-> (width, height, 4-bit pixels (rows of width / 2 bytes), 16 colours (15-bit, 0 = transparent))"""
    import title, numpy as np
    from PIL import Image
    a = title.word('REMIX', LOGO_SIZE, 8); al = a[..., 3] > 0; ys, xs = np.where(al)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; al = a[..., 3] > 0
    h, w = al.shape; W = (w + 3) // 4 * 4
    assert W <= 64 and h <= 60, (w, h)
    q = Image.fromarray(a[..., :3].copy()).quantize(15, method=Image.MEDIANCUT, dither=Image.NONE)
    idx = np.array(q) + 1; idx[~al] = 0
    pal = np.array(q.getpalette()[:45]).reshape(15, 3)
    cl = [0] + [0x8000 | (b >> 3) << 10 | (g >> 3) << 5 | (r >> 3) for r, g, b in pal]
    px = np.zeros((h, W), np.uint8); px[:, :w] = idx
    pix = bytes((px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).flatten())
    return W, h, pix, cl
HELP = '  ON/OFF       TAB     BACK'          # drawn signs in the gaps (dtri; the menu font has none): Left / Right arrows, Triangle
TRI_X, TRI_Y = -132 + 21 * 8 + 2, 102          # the Triangle's left edge and top (8 pixels a letter)
ARROW_X = -132 + 11 * 8 + 1                    # the Left arrow (Right: + 12)


def data():
    d = bytearray(); lab = {}
    def put(n, b): lab[n] = SCR_DATA + len(d); d.extend(b); d.extend(bytes((-len(d)) % 4))
    for n in ('prev', 'sel', 'open', 'tab', 'item', 'conf', 'alive'): put(n, bytes(4))
    put('rgbt', bytes([255, 200, 40, 32])); put('rgbn', bytes([90, 100, 120, 32])); put('rgbs', bytes([90, 210, 255, 32]))
    put('rgbon', bytes([90, 230, 120, 32])); put('rgboff', bytes([110, 110, 120, 32])); put('rgbh', bytes([150, 150, 150, 32]))
    W, Hh, pix, cl = logo()
    put('lrect', struct.pack('<4h', LOGO_VRAM[0], LOGO_VRAM[1], W // 4, Hh)); put('crect', struct.pack('<4h', LOGO_CLUT[0], LOGO_CLUT[1], 16, 1))
    put('lclut', struct.pack('<16H', *cl)); put('lpix', pix); put('blink', bytes(4))
    X, Y = TRI_X, TRI_Y; xy = lambda x, y: (y & 0xffff) << 16 | (x & 0xffff)
    A, G = ARROW_X, 0x20E0E0E0                    # as light as the help's letters
    put('tri', struct.pack('<16I', 0x20000000, xy(X + 5, Y + 4), xy(X + 2, Y + 9), xy(X + 8, Y + 9),
                                   0x2050D080, xy(X + 5, Y - 1), xy(X - 1, Y + 11), xy(X + 11, Y + 11),
                                   G, xy(A, Y + 5), xy(A + 8, Y), xy(A + 8, Y + 10),
                                   G, xy(A + 20, Y + 5), xy(A + 12, Y), xy(A + 12, Y + 10)))
    # the Cross button: a blue X in the first gap of HELP (two bars, each two triangles)
    x0, B = -132 + 1, 0x20FF9664
    put('crx', struct.pack('<16I', B, xy(x0, Y), xy(x0 + 2, Y), xy(x0 + 9, Y + 9), B, xy(x0, Y), xy(x0 + 9, Y + 9), xy(x0 + 7, Y + 9),
                                   B, xy(x0 + 7, Y), xy(x0 + 9, Y), xy(x0 + 2, Y + 9), B, xy(x0 + 7, Y), xy(x0 + 2, Y + 9), xy(x0, Y + 9)))
    put('on', b'ON\0'); put('off', b'OFF\0'); put('help', HELP.encode() + b'\0')
    for i, (name, _) in enumerate(TABS): put('t%d' % i, name.encode() + b'\0')
    put('cnts', bytes(len(l) for _, l in TABS))
    put('tabl', b''.join(bytes(l) + bytes(16 - len(l)) for _, l in TABS))
    for i, t in enumerate(LINES): put('l%d' % i, t.encode() + b'\0')
    for i, t in enumerate(WARN): put('w%d' % i, t.encode() + b'\0')
    put('ltab', b''.join(struct.pack('<I', lab['l%d' % i]) for i in range(len(LINES))))
    put('ttab', b''.join(struct.pack('<I', lab['t%d' % i]) for i in range(len(TABS))))
    put('ptab', b''.join(struct.pack('<4I', a, on, off, bit) for a, on, off, bit in PATCH))
    return bytes(d), lab


def routines(D):
    la = lambda r, a: [f'lui {r}, {H(a)}', f'addiu {r}, {r}, {L(a)}']
    lw = lambda r, k: [f'lui {r}, {H(D[k])}', f'lw {r}, {L(D[k])}({r})', 'nop']
    sw = lambda r, k, t='at': [f'lui {t}, {H(D[k])}', f'sw {r}, {L(D[k])}({t})']
    NT = len(TABS)
    # pw: in place of the mode select's pad routine: the game's pad words, then (only while the mode select screen is
    # drawn: alive) the REMIX entry and screen; while they have the input, the game's pad words are cleared
    S = ['pw:', 'addiu sp, sp, -0x20', 'sw ra, 0x18(sp)', f'jal {PAD_FN}', 'nop',
         *lw('t0', 'alive'), 'blez t0, pw9', 'addiu t0, t0, -1', *sw('t0', 'alive'),
         f'lui t1, {H(PADV)}', f'lhu t1, {L(PADV)}(t1)', *lw('t2', 'prev'), *sw('t1', 'prev'), 'nor t2, t2, zero', 'and t2, t2, t1',
         *lw('t3', 'open'), 'bnez t3, pwo', 'nop', *lw('t3', 'sel'), 'bnez t3, pws', 'nop',
         f'lui t4, {H(CURSOR)}', f'lw t4, {L(CURSOR)}(t4)', f'addiu t5, zero, {OPTIONS_ITEM}', 'bne t4, t5, pw9', f'andi t5, t2, {DOWN}',
         'beqz t5, pw9', 'addiu t5, zero, 1', *sw('t5', 'sel'), 'j pwz', 'nop',
         'pws:', f'andi t5, t2, {UP}', 'beqz t5, ps1', 'nop', *sw('zero', 'sel'), 'j pwz', 'nop',
         'ps1:', f'andi t5, t2, {CROSS}', 'beqz t5, pwz', 'addiu t5, zero, 1', *sw('t5', 'open'), *sw('zero', 'tab'), *sw('zero', 'item'),
         *sw('zero', 'conf'), 'j pwz', 'nop',
         'pwo:', f'andi t5, t2, {TRI | CIRC}', 'beqz t5, po1', 'nop', *sw('zero', 'open'), *sw('zero', 'conf'), 'j pwz', 'nop',
         'po1:', *lw('t6', 'tab'), *lw('t7', 'item'),
         f'andi t5, t2, {LEFT}', 'beqz t5, po2', 'nop', 'addiu t6, t6, -1', 'bgez t6, po1b', 'nop', f'addiu t6, zero, {NT - 1}',
         'po1b:', 'move t7, zero', *sw('zero', 'conf'),
         'po2:', f'andi t5, t2, {RIGHT}', 'beqz t5, po3', 'nop', 'addiu t6, t6, 1', f'slti t5, t6, {NT}', 'bnez t5, po2b', 'nop', 'move t6, zero',
         'po2b:', 'move t7, zero', *sw('zero', 'conf'),
         'po3:', *la('t8', D['cnts']), 'addu t8, t8, t6', 'lbu t8, 0(t8)',
         f'andi t5, t2, {UP}', 'beqz t5, po4', 'nop', 'addiu t7, t7, -1', 'bgez t7, po3b', 'nop', 'addiu t7, t8, -1',
         'po3b:', *sw('zero', 'conf'),
         'po4:', f'andi t5, t2, {DOWN}', 'beqz t5, po5', 'nop', 'addiu t7, t7, 1', 'slt t5, t7, t8', 'bnez t5, po4b', 'nop', 'move t7, zero',
         'po4b:', *sw('zero', 'conf'),
         'po5:', *sw('t6', 'tab'), *sw('t7', 'item'), f'andi t5, t2, {CROSS}', 'beqz t5, pwz', 'nop',
         'sll t5, t6, 4', 'addu t5, t5, t7', *la('t8', D['tabl']), 'addu t8, t8, t5', 'lbu t5, 0(t8)',
         f'lui t0, {H(FLAGS)}', f'lw t9, {L(FLAGS)}(t0)', f'addiu t8, zero, {UNLOCK_LINE}', 'bne t5, t8, po6', 'nop', 'j ounl', 'nop',
         'po6:', 'addiu t8, zero, 1', 'sllv t8, t8, t5', 'xor t9, t9, t8', f'sw t9, {L(FLAGS)}(t0)',
         'pwz:', f'lui t1, {H(PADV)}'] + [f'sh zero, {L(PADV) + k}(t1)' for k in range(0, 12, 2)] + \
        ['pw9:', 'lw ra, 0x18(sp)', 'nop', 'jr ra', 'addiu sp, sp, 0x20']
    # ounl: X on UNLOCK EVERYTHING (t0 = H(FLAGS), t9 = flags): first press = warning, second = unlock
    S += ['ounl:', *lw('t8', 'conf'), 'bnez t8, oun1', 'addiu t8, zero, 1', *sw('t8', 'conf'), 'j pwz', 'nop',
          'oun1:', *sw('zero', 'conf'), 'lui t8, 0x8005']
    for o, v, k in UNLOCK:
        S += ([f'lhu t7, {o}(t8)', 'nop', f'ori t7, t7, {v}'] if k == 'o' else [f'addiu t7, zero, {v}']) + [f'sh t7, {o}(t8)']
    S += [f'lui t8, {(1 << UNLOCK_LINE) >> 16:#x}', 'or t9, t9, t8', f'lui t0, {H(FLAGS)}', f'sw t9, {L(FLAGS)}(t0)', 'j pwz', 'nop']
    # opt (the TV function's GetClut call, every frame of the mode select screen): switches applied, the switches'
    # block installed, then the REMIX label (or the screen)
    S += ['opt:', 'addiu sp, sp, -0x50', 'sw ra, 0x4c(sp)', 'sw s5, 0x40(sp)', 'sw s6, 0x44(sp)', 'sw s7, 0x48(sp)',
          f'jal {HOOK_FN}', 'nop', 'sw v0, 0x34(sp)', 'jal oap', 'nop', 'jal tins', 'nop',
          'addiu t0, zero, 2', *sw('t0', 'alive'),
          'sll v1, s1, 2', 'addu v1, v1, s1', 'sll v1, v1, 2', 'addu v1, v1, s4', 'lw s5, 4(v1)', 'sll v0, s1, 13',
          f'lui s6, {H(PRIMS)}', 'addu s6, s6, v0', f'addiu s6, s6, {L(PRIMS)}',
          *lw('t0', 'open'), 'beqz t0, opl', 'nop', 'j drs', 'nop', 'opl:',
          *lw('t1', 'blink'), 'addiu t1, t1, 1', *sw('t1', 'blink'),
          'lui t7, 0x60', 'ori t7, t7, 0x6060', *lw('t0', 'sel'), 'beqz t0, dl1', 'andi t1, t1, 16',
          'lui t7, 0x80', 'beqz t1, dl1', 'ori t7, t7, 0x8080', 'lui t7, 0xb0', 'ori t7, t7, 0xb0b0',
          'dl1:', f'addiu t4, zero, {LOGO_XY[0]}', f'addiu t5, zero, {LOGO_XY[1]}', 'jal dlogo', 'nop', 'j out', 'nop']
    # dlogo: the logo at (t4, t5), modulation t7 (0x808080 = as is): sent to VRAM, SPRT + DR_TPAGE linked into s5
    W, Hh, _, _ = logo()
    TP = 0xE1000400 | (LOGO_VRAM[0] >> 6) | ((LOGO_VRAM[1] >> 8) << 4)
    CW = (LOGO_CLUT[1] << 6) | (LOGO_CLUT[0] >> 4)
    S += ['dlogo:', 'sw ra, 0x2c(sp)', 'sw t4, 0x10(sp)', 'sw t5, 0x14(sp)', 'sw t7, 0x18(sp)',
          *la('a0', D['lrect']), *la('a1', D['lpix']), f'jal {LOADIMAGE}', 'nop',
          *la('a0', D['crect']), *la('a1', D['lclut']), f'jal {LOADIMAGE}', 'nop',
          'lui t0, 0x400', 'sw t0, 0(s6)', 'lw t7, 0x18(sp)', 'lui t1, 0x6400', 'or t7, t7, t1', 'sw t7, 4(s6)',
          'lw t4, 0x10(sp)', 'lw t5, 0x14(sp)', 'andi t4, t4, 0xffff', 'sll t5, t5, 16', 'or t4, t4, t5', 'sw t4, 8(s6)',
          f'lui t0, {CW}', f'ori t0, t0, {(LOGO_VRAM[1] & 255) << 8}', 'sw t0, 12(s6)', f'lui t0, {Hh}', f'ori t0, t0, {W}', 'sw t0, 16(s6)',
          'move a0, s6', 'jal dlnk', 'addiu s6, s6, 20',
          'lui t0, 0x100', 'sw t0, 0(s6)', f'lui t0, {TP >> 16:#x}', f'ori t0, t0, {TP & 0xffff:#x}', 'sw t0, 4(s6)',
          'move a0, s6', 'jal dlnk', 'addiu s6, s6, 8', 'lw ra, 0x2c(sp)', 'nop', 'jr ra', 'nop']
    S += ['dlnk:', 'lw t1, 0(s5)', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'lw t3, 0(a0)', 'and t4, t1, t2', 'lui t5, 0xff00', 'and t3, t3, t5',
          'or t3, t3, t4', 'sw t3, 0(a0)', 'and t1, t1, t5', 'and t4, a0, t2', 'or t1, t1, t4', 'jr ra', 'sw t1, 0(s5)']
    # drs: the screen
    S += ['drs:', f'addiu t4, zero, {LOGO_TITLE_XY[0]}', f'addiu t5, zero, {LOGO_TITLE_XY[1]}', 'lui t7, 0x80', 'ori t7, t7, 0x8080', 'jal dlogo', 'nop',
          'move s7, zero',
          'dt1:', 'sw s7, 0x30(sp)', 'sll t0, s7, 2', *la('t1', D['ttab']), 'addu t1, t1, t0', 'lw t6, 0(t1)',
          'addiu t0, zero, 88', 'mult s7, t0', 'mflo t4', 'addiu t4, t4, -132', 'addiu t5, zero, -80',
          *la('t7', D['rgbh']), *lw('t0', 'tab'), 'bne t0, s7, dt2', 'nop', *la('t7', D['rgbt']),
          'dt2:', 'jal drw', 'nop', 'lw s7, 0x30(sp)', 'nop', 'addiu s7, s7, 1', f'slti t0, s7, {NT}', 'bnez t0, dt1', 'nop',
          'move s7, zero', 'j di1', 'nop']
    S += ['di1:', *lw('t0', 'tab'), *la('t1', D['cnts']), 'addu t1, t1, t0', 'lbu t1, 0(t1)', 'nop', 'slt t2, s7, t1', 'bnez t2, dic', 'nop', 'j dh', 'nop', 'dic:',
          'sw s7, 0x30(sp)', 'sll t0, t0, 4', 'addu t0, t0, s7', *la('t1', D['tabl']), 'addu t1, t1, t0', 'lbu t3, 0(t1)', 'nop', 'sw t3, 0x24(sp)',
          'sll t0, t3, 2', *la('t1', D['ltab']), 'addu t1, t1, t0', 'lw t6, 0(t1)',
          'addiu t0, zero, 14', 'mult s7, t0', 'mflo t5', 'addiu t5, t5, -56', 'sw t5, 0x28(sp)', 'addiu t4, zero, -132',
          *la('t7', D['rgbn']), *lw('t0', 'item'), 'bne t0, s7, di2', 'nop', *la('t7', D['rgbs']),
          'di2:', 'jal drw', 'nop',
          'lw t3, 0x24(sp)', f'lui t1, {H(FLAGS)}', f'lw t0, {L(FLAGS)}(t1)', f'lui t1, {INV >> 16:#x}', f'ori t1, t1, {INV & 0xffff:#x}',
          'xor t0, t0, t1', 'srlv t0, t0, t3', 'andi t0, t0, 1', *la('t6', D['on']), *la('t7', D['rgbon']), 'beqz t0, di3', 'nop',
          *la('t6', D['off']), *la('t7', D['rgboff']),
          'di3:', 'addiu t4, zero, 112', 'lw t5, 0x28(sp)', 'jal drw', 'nop',
          'lw s7, 0x30(sp)', 'nop', 'addiu s7, s7, 1', 'j di1', 'nop']
    wl = lambda i: ['addiu t4, zero, -132', f'addiu t5, zero, {64 + 12 * i}', *la('t6', D['w%d' % i]), *la('t7', D['rgbt']), 'jal drw', 'nop']
    S += ['dh:', *lw('t0', 'conf'), 'beqz t0, dh1', 'nop'] + [x for i in range(len(WARN)) for x in wl(i)] + \
         ['dh1:', 'addiu t4, zero, -132', 'addiu t5, zero, 102', *la('t6', D['help']), *la('t7', D['rgbh']), 'jal drw', 'nop',
          'jal dtri', 'nop', 'j box', 'nop']
    # dtri: the Triangle button (outline in the PlayStation's green: a black POLY_F3 inside a green one; table tri)
    S += ['dtri:', 'move t9, ra', *la('t8', D['tri']), 'addiu t7, t8, 128',
          'dtr1:', 'lui t0, 0x400', 'sw t0, 0(s6)', 'lw t0, 0(t8)', 'lw t1, 4(t8)', 'lw t2, 8(t8)', 'lw t3, 12(t8)',
          'sw t0, 4(s6)', 'sw t1, 8(s6)', 'sw t2, 12(s6)', 'sw t3, 16(s6)', 'move a0, s6', 'jal dlnk', 'addiu s6, s6, 20',
          'addiu t8, t8, 16', 'bne t8, t7, dtr1', 'nop', 'jr t9', 'nop']
    S += ['drw:', 'sw ra, 0x2c(sp)', 'sw t4, 0x10(sp)', 'sw t5, 0x14(sp)', 'sw t6, 0x18(sp)', 'sw t7, 0x1c(sp)', 'sw zero, 0x20(sp)',
          'move a0, s5', 'move a1, s6', f'lui a2, {H(FONT)}', f'addiu a2, a2, {L(FONT)}', f'jal {TEXT}', f'addiu a3, zero, {CLUT}',
          'lw ra, 0x2c(sp)', 'move s6, v0', 'jr ra', 'nop']
    # box: the black background of the screen (TILE 320 x 240), linked last = drawn first
    S += ['box:', 'lw t0, 0(s5)', 'lui t1, 0x300', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'and t3, t0, t2', 'or t3, t3, t1', 'sw t3, 0(s6)',
          'lui t3, 0x6000', 'sw t3, 4(s6)', 'lui t3, 0xff88', 'ori t3, t3, 0xff60', 'sw t3, 8(s6)', 'lui t3, 240', 'ori t3, t3, 320', 'sw t3, 12(s6)',
          'lui t1, 0xff00', 'and t0, t0, t1', 'and t3, s6, t2', 'or t0, t0, t3', 'j out', 'sw t0, 0(s5)']
    S += ['out:', 'lw v0, 0x34(sp)', 'lw ra, 0x4c(sp)', 'lw s5, 0x40(sp)', 'lw s6, 0x44(sp)', 'lw s7, 0x48(sp)', 'jr ra', 'addiu sp, sp, 0x50']
    # oap: apply the switches to the PATCH words (table ptab: address, on, off, bit), FlushCache after a write
    import toggles
    S += toggles.installer(la)
    S += ['oap:', f'lui t0, {H(FLAGS)}', f'lbu t6, {L(FLAGS)}(t0)', *la('t0', D['ptab']), f'addiu t5, t0, {16 * len(PATCH)}', 'move t9, zero',
          'oa1:', 'lw t1, 0(t0)', 'lw t2, 4(t0)', 'lw t3, 8(t0)', 'lw t4, 12(t0)', 'lw t7, 0(t1)', 'and t4, t4, t6', 'beqz t4, oa2', 'move t8, t2',
          'move t8, t3', 'oa2:', 'beq t7, t8, oa3', 'nop', 'beq t7, t2, oa4', 'nop', 'bne t7, t3, oa3', 'nop',
          'oa4:', 'sw t8, 0(t1)', 'addiu t9, zero, 1',
          'oa3:', 'addiu t0, t0, 16', 'bne t0, t5, oa1', 'nop', 'beqz t9, oa9', 'nop', f'j {FLUSH}', 'nop', 'oa9:', 'jr ra', 'nop']
    return S


TOP = {'pw', 'ounl', 'opt', 'drs', 'di1', 'dh', 'drw', 'box', 'out', 'oap', 'tins', 'dlogo', 'dlnk', 'dtri'}


def place(S, tables, extra=()):
    """blocks (split at TOP labels) placed best fit, then the tables (bytes) in what is left -> words, labels"""
    blocks = []; cur = []
    for l in S:
        if l.endswith(':') and cur and l[:-1] in TOP: blocks.append(cur); cur = []
        cur.append(l)
    blocks.append(cur)
    size = lambda b: 4 * sum(1 for l in b if not l.endswith(':'))
    caves = [[lo, lo, hi, []] for lo, hi in CAVES]
    tcaves = [[lo, lo, hi, []] for lo, hi in extra]          # for the tables only
    for b in sorted(blocks, key=lambda b: -size(b)):
        fit = [c for c in caves if c[1] + size(b) <= c[2]]
        assert fit, 'plus de place pour ' + b[0]
        c = min(fit, key=lambda c: c[2] - c[1]); c[3].append(b); c[1] += size(b)
    tab_at = {}
    for name, t in tables:
        fit = [c for c in caves + tcaves if c[1] + len(t) <= c[2]]
        assert fit, 'plus de place pour ' + name
        c = min(fit, key=lambda c: c[2] - c[1]); tab_at[name] = c[1]; c[1] += len(t)
    cave_of = {}
    for lo, _, _, bl in caves:
        for l in (l for b in bl for l in b):
            if l.endswith(':'): cave_of[l[:-1]] = lo
    for lo, _, _, bl in caves:
        for l in (l for b in bl for l in b):
            if not l.endswith(':') and l.split()[0] in ('beq', 'bne', 'beqz', 'bnez', 'bltz', 'bgez', 'blez', 'bgtz'):
                assert cave_of.get(l.split(',')[-1].strip(), lo) == lo, 'branche hors de sa zone : ' + l
    labels = dict(tab_at)
    for lo, _, _, bl in caves:
        pc = lo
        for l in (l for b in bl for l in b):
            if l.endswith(':'): labels[l[:-1]] = pc
            else: pc += 4
    words = []
    for lo, _, _, bl in caves:
        if bl:
            c, _ = asm([l for b in bl for l in b], lo, labels); words += c
    for name, t in tables: words += [(tab_at[name] + i, struct.unpack_from('<I', t, i)[0]) for i in range(0, len(t), 4)]
    return words, labels


def build():
    """data at the start of the screen's sector (toggles.SCREEN), the code in the rest of it and the other caves"""
    d, D = data()
    end = (SCR_DATA + len(d) + 3) // 4 * 4
    caves = CAVES + [(end, toggles.SCREEN[1]), DATA]
    global_caves = CAVES[:]
    CAVES[:] = caves
    try:
        words, lab = place(routines(D), [], ())
    finally:
        CAVES[:] = global_caves
    return words, lab, d


def ops(disc, pkg=None):
    """pkg: the other mods' operations (their switches, remix/toggles.py)"""
    ms = disc.read_file('/MODE_SEL.BIN'); ex = disc.read_file('/SCES_009.92')
    where = lambda a: ('/MODE_SEL.BIN', ms, OVL) if a >= OVL else ('/SCES_009.92', ex, 0x8000F800)
    assert struct.unpack_from('<I', ms, HOOK - OVL)[0] == J(3, HOOK_FN)
    assert struct.unpack_from('<I', ms, PAD_CALL - OVL)[0] == J(3, PAD_FN)
    c, l, d = build()
    d = d + bytes((-len(d)) % 4)
    P = [(a, x) for a, x in c] + [(SCR_DATA + i, struct.unpack_from('<I', d, i)[0]) for i in range(0, len(d), 4)] + \
        [(HOOK, J(3, l['opt'])), (PAD_CALL, J(3, l['pw']))]
    out = toggles.ops(pkg) if pkg is not None else [['padto', '/MODE_SEL.BIN', toggles.FILE_END]]   # padto first
    for a, x in P:
        f, b, base = where(a); o = a - base
        out.append(['w', f, o, struct.unpack_from('<I', b, o)[0] if o + 4 <= len(b) else 0, x])
    return out
