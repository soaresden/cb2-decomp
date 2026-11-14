# In-game options (mod `options`, v26..v28): on the mode select screen, hold R1 to show the REMIX OPTIONS panel; while R1
# is held, L1 moves the cursor (the list of 18 lines scrolls, 10 shown) and R2 switches the line on or off: rear view
# (mod rear), live half-pipe marks (hplive), unlock announcements (news), air control (air), Boarder Cross ramming
# (ramming), widescreen, race radar line and ranking (radar), every other mod (remix/toggles.py), UNLOCK EVERYTHING.
#
# The switches are bits of the word 0x80057438 (bit set = off; line i = bit i), in the progress block that
# the game saves on the memory card but never reads (see docs/progression.md; INIT zeroes it): they follow the save.
#   - radar tests bit 64 (the line) and bit 128 (the ranking panel);
#   - rear, hplive, news test their bit themselves;
#   - air and ramming are switched where their code lives in the exe (always in memory): every frame of the mode
#     select screen, the words of PATCH get their "on" or "off" value (air: three branches of the exe routines md / ax /
#     rm made unconditional, as if no d-pad, no charge, no remap; ramming: the entry of kc becomes a jump to the game's
#     own collision response). A word is only written when it holds one of its two values (mod absent: untouched);
#     after a write, FlushCache.
# MODE_SEL: the TV function (func_80064200, every frame, s4 = its OT table, s1 = frame buffer index) calls
# func_80028BDC (GetClut) at 0x800643E4: that call goes through opt (dead functions of MODE_SEL), which reads the pad
# (0x800832BA), applies the switches, and draws the panel with the game's text routine (func_80012CA0, menu font)
# into a private primitive buffer (0x801F8000 + 0x2000 per frame buffer: about 400 letters of 20 bytes; 0x801F0000..0x801FF000 is free on that screen), on a dark box (TILE).
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
DATA = (0x8005C8B0, 0x8005C968)        # after crewrank's data
X0, X1, Y0, DY = -150, 70, -64, 13
LINES = ['REAR VIEW (CIRCLE)', 'LIVE HALF-PIPE MARKS', 'UNLOCK NEWS', 'AIR CONTROL', 'BOARDER CROSS RAMMING', 'WIDESCREEN 16:9',
         'RACE RADAR LINE', 'RACE RANKING',
         # the other mods (remix/toggles.py: bits 8..16, in the order of toggles.BITS)
         'SPECIAL BOARDS', 'HARD + MIRROR', 'BOSS GRAY SNOWMAN COMP.', 'HIDDEN OUTFITS', 'MAX STATS AND BOARD', 'BIG AIR MASTER',
         'PROGRESS PAGE (SELECT)', 'SKIP QUALIFYING (SELECT)', 'JICCHI NICK KELLY',
         'FALLS AS A NUMBER',                   # bit 17 (radar.py: one ball and x13 instead of the row of balls)
         'UNLOCK EVERYTHING']                   # line i = bit i of the flags word (bit set = off)
UNLOCK_LINE = len(LINES) - 1           # an action, not a switch: R2 shows the warning, R2 again unlocks (its bit = done)
INV = 32 | 1 << UNLOCK_LINE            # lines whose bit set means ON (off by default)
VIS = 10                               # lines shown at a time: the list scrolls with the cursor
WARN = ['R2 AGAIN UNLOCKS ALL RIDERS,', 'COURSES, BOARDS, MIRROR, HARD,', 'TROPHIES. SAVED. NO UNDO!']     # <= 30 letters (box)
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


def data():
    d = bytearray(); lab = {}
    def put(n, b): lab[n] = DATA[0] + len(d); d.extend(b); d.extend(bytes((-len(d)) % 4))
    put('prev', bytes(4)); put('cur', bytes(4)); put('conf', bytes(4))
    put('rgbt', bytes([255, 170, 70, 32])); put('rgbn', bytes([150, 140, 100, 32])); put('rgbon', bytes([90, 230, 120, 32])); put('rgboff', bytes([110, 110, 120, 32]))
    put('title', TITLE.encode() + b'\0'); put('on', b'ON\0'); put('off', b'OFF\0')
    assert DATA[0] + len(d) <= DATA[1], hex(DATA[0] + len(d))
    return bytes(d), lab


def routines(D):
    la = lambda r, a: [f'lui {r}, {H(a)}', f'addiu {r}, {r}, {L(a)}']
    n = len(LINES)
    S = ['opt:', 'addiu sp, sp, -0x50', 'sw ra, 0x4c(sp)', 'sw s5, 0x40(sp)', 'sw s6, 0x44(sp)', 'sw s7, 0x48(sp)',
         f'jal {HOOK_FN}', 'nop', 'sw v0, 0x34(sp)', 'jal oap', 'nop', 'jal tins', 'nop',
         f'lui t0, {H(PAD)}', f'lhu t1, {L(PAD)}(t0)', f'lui t2, {H(D["prev"])}', f'lw t3, {L(D["prev"])}(t2)', f'sw t1, {L(D["prev"])}(t2)',
         f'andi t0, t1, {R1}', 'bnez t0, op1', 'nop', 'j out', 'nop',
         'op1:', 'nor t4, t3, zero', 'and t4, t4, t1', f'lw t5, {L(D["cur"])}(t2)', f'andi t0, t4, {L1}', 'beqz t0, op2', 'addiu t5, t5, 1',
         f'slti t0, t5, {n}', 'bnez t0, op3', 'nop', 'move t5, zero', 'op3:', f'sw t5, {L(D["cur"])}(t2)', f'sw zero, {L(D["conf"])}(t2)',
         'op2:', f'lw t5, {L(D["cur"])}(t2)', f'lui t0, {H(FLAGS)}', f'lw t6, {L(FLAGS)}(t0)', f'andi t7, t4, {R2}', 'beqz t7, op4', 'addiu t7, zero, 1',
         f'addiu t8, zero, {UNLOCK_LINE}', 'bne t5, t8, op5', 'nop', 'j ounl', 'nop', 'op5:',
         'sllv t7, t7, t5', 'xor t6, t6, t7', f'sw t6, {L(FLAGS)}(t0)',
         'op4:', 'sw t6, 0x38(sp)', 'sw t5, 0x24(sp)', 'j odr', 'nop']
    # odr: the panel
    S += ['odr:', 'sll v1, s1, 2', 'addu v1, v1, s1', 'sll v1, v1, 2', 'addu v1, v1, s4', 'lw s5, 4(v1)', 'sll v0, s1, 13',
          f'lui s6, {H(PRIMS)}', 'addu s6, s6, v0', f'addiu s6, s6, {L(PRIMS)}',
          f'addiu t4, zero, {X0}', f'addiu t5, zero, {Y0}', *la('t6', D['title']), *la('t7', D['rgbt']), 'jal drw', 'nop',
          'lw s7, 0x24(sp)', 'nop', f'addiu s7, s7, -{VIS // 2}', 'bgez s7, ol0', 'nop', 'move s7, zero',
          'ol0:', f'slti t0, s7, {len(LINES) - VIS + 1}', 'bnez t0, ol2', 'nop', f'addiu s7, zero, {len(LINES) - VIS}',
          'ol2:', 'sw s7, 0x3c(sp)',
          'ol:', 'sw s7, 0x30(sp)', 'sll t0, s7, 2', *la('t1', D['tab']), 'addu t1, t1, t0', 'lw t6, 0(t1)', f'addiu t4, zero, {X0 + 8}',
          'lw t5, 0x3c(sp)', 'nop', 'subu t5, s7, t5', f'addiu t0, zero, {DY}', 'mult t5, t0', 'mflo t5', f'addiu t5, t5, {Y0 + DY}', 'sw t5, 0x28(sp)',
          *la('t7', D['rgbn']), 'lw t0, 0x24(sp)', 'nop', 'bne t0, s7, ol1', 'nop', *la('t7', D['rgbt']),
          'ol1:', 'jal drw', 'nop', 'j ost', 'nop']
    S += ['ost:', 'lw s7, 0x30(sp)', 'lw t0, 0x38(sp)', f'lui t1, {INV >> 16:#x}', f'ori t1, t1, {INV & 0xffff:#x}', 'xor t0, t0, t1', 'srlv t0, t0, s7', 'andi t0, t0, 1', *la('t6', D['on']), *la('t7', D['rgbon']),
          'beqz t0, os', 'nop', *la('t6', D['off']), *la('t7', D['rgboff']),
          'os:', f'addiu t4, zero, {X1}', 'lw t5, 0x28(sp)', 'jal drw', 'nop',
          'lw s7, 0x30(sp)', 'lw t1, 0x3c(sp)', 'addiu s7, s7, 1', f'addiu t1, t1, {VIS}', 'slt t0, s7, t1', 'beqz t0, os9', 'nop', 'j ol', 'nop', 'os9:', 'j owr', 'nop']
    # owr: the warning of the unlock line, while it waits for the second R2
    wl = lambda i: [f'addiu t4, zero, {X0 + 8}', f'addiu t5, zero, {Y0 + DY * (VIS + 1 + i)}', *la('t6', D['w%d' % i]), *la('t7', D['rgbt']), 'jal drw', 'nop']
    S += ['owr:', f'lui t0, {H(D["conf"])}', f'lw t0, {L(D["conf"])}(t0)', 'nop', 'beqz t0, owx', 'nop', *wl(0), *wl(1), 'j ow2', 'nop', 'owx:', 'j box', 'nop']
    S += ['ow2:'] + [x for i in range(2, len(WARN)) for x in wl(i)] + ['j box', 'nop']
    # ounl: R2 on the unlock line (t0 = H(FLAGS), t6 = flags, t2 = H(data)): first press = warning, second = unlock
    S += ['ounl:', f'lw t8, {L(D["conf"])}(t2)', 'addiu t9, zero, 1', 'bnez t8, oun1', 'nop', f'sw t9, {L(D["conf"])}(t2)', 'j op4', 'nop',
          'oun1:', f'sw zero, {L(D["conf"])}(t2)', 'lui t8, 0x8005']
    for o, v, k in UNLOCK:
        S += ([f'lhu t9, {o}(t8)', 'nop', f'ori t9, t9, {v}'] if k == 'o' else [f'addiu t9, zero, {v}']) + [f'sh t9, {o}(t8)']
    S += [f'lui t8, {(1 << UNLOCK_LINE) >> 16:#x}', 'or t6, t6, t8', f'sw t6, {L(FLAGS)}(t0)', 'j op4', 'nop']
    yb = Y0 + DY * (VIS + 1 + len(WARN))
    S += ['drw:', 'sw ra, 0x2c(sp)', 'sw t4, 0x10(sp)', 'sw t5, 0x14(sp)', 'sw t6, 0x18(sp)', 'sw t7, 0x1c(sp)', 'sw zero, 0x20(sp)',
          'move a0, s5', 'move a1, s6', f'lui a2, {H(FONT)}', f'addiu a2, a2, {L(FONT)}', f'jal {TEXT}', f'addiu a3, zero, {CLUT}',
          'lw ra, 0x2c(sp)', 'move s6, v0', 'jr ra', 'nop']
    S += ['box:', 'lw t0, 0(s5)', 'lui t1, 0x300', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'and t3, t0, t2', 'or t3, t3, t1', 'sw t3, 0(s6)',
          'lui t3, 0x6030', 'ori t3, t3, 0x1810', 'sw t3, 4(s6)', f'lui t3, {(Y0 - 6) & 0xffff:#x}', f'ori t3, t3, {(X0 - 10) & 0xffff:#x}', 'sw t3, 8(s6)',
          f'lui t3, {yb + 4 - (Y0 - 6)}', f'ori t3, t3, {X1 + 50 - (X0 - 10)}', 'sw t3, 12(s6)',
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


TOP = {'opt', 'odr', 'ost', 'drw', 'box', 'out', 'oap', 'owr', 'ow2', 'ounl', 'tins'}


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
    d, D = data()
    ptab = b''.join(struct.pack('<4I', a, on, off, bit) for a, on, off, bit in PATCH)
    strs = [('l%d' % i, t) for i, t in enumerate(LINES)] + [('w%d' % i, t) for i, t in enumerate(WARN)]
    blobs = lambda tabaddr: [('tab', b''.join(struct.pack('<I', tabaddr['l%d' % i]) for i in range(len(LINES)))), ('ptab', ptab)] + \
        [(k, t.encode() + bytes(4 - len(t) % 4)) for k, t in strs]
    D2 = dict(D); D2.update({k: 0 for k in ['tab', 'ptab'] + [k for k, _ in strs]})      # first pass: where the tables land
    extra = [(DATA[0] + (len(d) + 3) // 4 * 4, DATA[1])]       # what the data block leaves
    _, lab = place(routines(D2), blobs(D2), extra)
    D2.update({k: lab[k] for k in ['tab', 'ptab'] + [k for k, _ in strs]})
    words, lab = place(routines(D2), blobs(D2), extra)
    assert all(lab[k] == D2[k] for k in ['tab', 'ptab'] + [k for k, _ in strs])
    return words, lab, d


def ops(disc, pkg=None):
    """pkg: the other mods' operations (their switches, remix/toggles.py)"""
    ms = disc.read_file('/MODE_SEL.BIN'); ex = disc.read_file('/SCES_009.92')
    where = lambda a: ('/MODE_SEL.BIN', ms, OVL) if a >= OVL else ('/SCES_009.92', ex, 0x8000F800)
    assert struct.unpack_from('<I', ms, HOOK - OVL)[0] == J(3, HOOK_FN)
    c, l, d = build()
    P = [(a, x) for a, x in c] + [(DATA[0] + i, struct.unpack_from('<I', d, i)[0]) for i in range(0, len(d), 4)] + [(HOOK, J(3, l['opt']))]
    import toggles
    out = toggles.ops(pkg) if pkg is not None else [['padto', '/MODE_SEL.BIN', toggles.FILE_END]]   # padto first
    for a, x in P:
        f, b, base = where(a); o = a - base
        out.append(['w', f, o, struct.unpack_from('<I', b, o)[0] if o + 4 <= len(b) else 0, x])
    return out
