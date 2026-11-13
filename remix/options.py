# In-game options (mod `options`, v26): on the mode select screen, hold R1 to show the REMIX OPTIONS panel; while R1
# is held, L1 moves the cursor and R2 switches the line on or off: rear view (mod rear), live half-pipe marks
# (hplive), unlock announcements (news), air control (air), Boarder Cross ramming (ramming).
#
# The switches are bits of 0x80057438 (bit set = off), a byte of the progress block that the game saves on the
# memory card but never reads (see docs/progression.md): they follow the save.
#   - rear, hplive, news test their bit themselves;
#   - air and ramming are switched where their code lives in the exe (always in memory): every frame of the mode
#     select screen, the words of PATCH get their "on" or "off" value (air: three branches of the exe routines md / ax /
#     rm made unconditional, as if no d-pad, no charge, no remap; ramming: the entry of kc becomes a jump to the game's
#     own collision response). A word is only written when it holds one of its two values (mod absent: untouched);
#     after a write, FlushCache.
# MODE_SEL: the TV function (func_80064200, every frame, s4 = its OT table, s1 = frame buffer index) calls
# func_80028BDC (GetClut) at 0x800643E4: that call goes through opt (dead functions of MODE_SEL), which reads the pad
# (0x800832BA), applies the switches, and draws the panel with the game's text routine (func_80012CA0, menu font)
# into a private primitive buffer (0x801F8000 + 0x1000 per frame buffer: about 130 letters of 20 bytes), on a dark box (TILE).
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
         (0x80031180, 0x8003120C), (0x8003BD98, 0x8003BE10), (0x80040AA4, 0x80040B0C)]    # exe: dead functions kept for this mod (see crew.CAVES)
DATA = (0x8005C8B0, 0x8005C968)        # after crewrank's data
X0, X1, Y0, DY = -150, 70, 18, 13
LINES = [('REAR VIEW (CIRCLE)', 1), ('LIVE HALF-PIPE MARKS', 2), ('UNLOCK NEWS', 4), ('AIR CONTROL', 8), ('BOARDER CROSS RAMMING', 16),
         ('WIDESCREEN 16:9', 32)]
INV = 32                               # lines whose bit set means ON (off by default)
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
    put('prev', bytes(4)); put('cur', bytes(4))
    put('rgbt', bytes([255, 170, 70, 32])); put('rgbn', bytes([150, 140, 100, 32])); put('rgbon', bytes([90, 230, 120, 32])); put('rgboff', bytes([110, 110, 120, 32]))
    put('title', TITLE.encode() + b'\0'); put('on', b'ON\0'); put('off', b'OFF\0')
    for i, (t, b) in enumerate(LINES): put('l%d' % i, t.encode() + b'\0')
    assert DATA[0] + len(d) <= DATA[1], hex(DATA[0] + len(d))
    return bytes(d), lab


def routines(D):
    la = lambda r, a: [f'lui {r}, {H(a)}', f'addiu {r}, {r}, {L(a)}']
    n = len(LINES)
    S = ['opt:', 'addiu sp, sp, -0x50', 'sw ra, 0x4c(sp)', 'sw s5, 0x40(sp)', 'sw s6, 0x44(sp)', 'sw s7, 0x48(sp)',
         f'jal {HOOK_FN}', 'nop', 'sw v0, 0x34(sp)', 'jal oap', 'nop',
         f'lui t0, {H(PAD)}', f'lhu t1, {L(PAD)}(t0)', f'lui t2, {H(D["prev"])}', f'lw t3, {L(D["prev"])}(t2)', f'sw t1, {L(D["prev"])}(t2)',
         f'andi t0, t1, {R1}', 'bnez t0, op1', 'nop', 'j out', 'nop',
         'op1:', 'nor t4, t3, zero', 'and t4, t4, t1', f'lw t5, {L(D["cur"])}(t2)', f'andi t0, t4, {L1}', 'beqz t0, op2', 'addiu t5, t5, 1',
         f'slti t0, t5, {n}', 'bnez t0, op3', 'nop', 'move t5, zero', 'op3:', f'sw t5, {L(D["cur"])}(t2)',
         'op2:', f'lw t5, {L(D["cur"])}(t2)', f'lui t0, {H(FLAGS)}', f'lbu t6, {L(FLAGS)}(t0)', f'andi t7, t4, {R2}', 'beqz t7, op4', 'addiu t7, zero, 1',
         'sllv t7, t7, t5', 'xor t6, t6, t7', f'sb t6, {L(FLAGS)}(t0)',
         'op4:', 'sw t6, 0x38(sp)', 'sw t5, 0x24(sp)', 'j odr', 'nop']
    # odr: the panel
    S += ['odr:', 'sll v1, s1, 2', 'addu v1, v1, s1', 'sll v1, v1, 2', 'addu v1, v1, s4', 'lw s5, 4(v1)', 'sll v0, s1, 12',
          f'lui s6, {H(PRIMS)}', 'addu s6, s6, v0', f'addiu s6, s6, {L(PRIMS)}',
          f'addiu t4, zero, {X0}', f'addiu t5, zero, {Y0}', *la('t6', D['title']), *la('t7', D['rgbt']), 'jal drw', 'nop',
          'move s7, zero',
          'ol:', 'sw s7, 0x30(sp)', 'sll t0, s7, 2', *la('t1', D['tab']), 'addu t1, t1, t0', 'lw t6, 0(t1)', f'addiu t4, zero, {X0 + 8}',
          'sll t5, s7, 3', 'addu t5, t5, s7', 'sll t0, s7, 2', 'addu t5, t5, t0', f'addiu t5, t5, {Y0 + DY}', 'sw t5, 0x28(sp)',
          *la('t7', D['rgbn']), 'lw t0, 0x24(sp)', 'nop', 'bne t0, s7, ol1', 'nop', *la('t7', D['rgbt']),
          'ol1:', 'jal drw', 'nop', 'j ost', 'nop']
    S += ['ost:', 'lw s7, 0x30(sp)', 'lw t0, 0x38(sp)', 'nop', f'xori t0, t0, {INV}', 'srlv t0, t0, s7', 'andi t0, t0, 1', *la('t6', D['on']), *la('t7', D['rgbon']),
          'beqz t0, os', 'nop', *la('t6', D['off']), *la('t7', D['rgboff']),
          'os:', f'addiu t4, zero, {X1}', 'lw t5, 0x28(sp)', 'jal drw', 'nop',
          'lw s7, 0x30(sp)', 'nop', 'addiu s7, s7, 1', f'slti t0, s7, {n}', 'beqz t0, os9', 'nop', 'j ol', 'nop', 'os9:', 'j box', 'nop']
    yb = Y0 + DY * (n + 1)
    S += ['drw:', 'sw ra, 0x2c(sp)', 'sw t4, 0x10(sp)', 'sw t5, 0x14(sp)', 'sw t6, 0x18(sp)', 'sw t7, 0x1c(sp)', 'sw zero, 0x20(sp)',
          'move a0, s5', 'move a1, s6', f'lui a2, {H(FONT)}', f'addiu a2, a2, {L(FONT)}', f'jal {TEXT}', f'addiu a3, zero, {CLUT}',
          'lw ra, 0x2c(sp)', 'move s6, v0', 'jr ra', 'nop']
    S += ['box:', 'lw t0, 0(s5)', 'lui t1, 0x300', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'and t3, t0, t2', 'or t3, t3, t1', 'sw t3, 0(s6)',
          'lui t3, 0x6030', 'ori t3, t3, 0x1810', 'sw t3, 4(s6)', f'lui t3, {(Y0 - 6) & 0xffff:#x}', f'ori t3, t3, {(X0 - 10) & 0xffff:#x}', 'sw t3, 8(s6)',
          f'lui t3, {yb + 4 - (Y0 - 6)}', f'ori t3, t3, {X1 + 50 - (X0 - 10)}', 'sw t3, 12(s6)',
          'lui t1, 0xff00', 'and t0, t0, t1', 'and t3, s6, t2', 'or t0, t0, t3', 'j out', 'sw t0, 0(s5)']
    S += ['out:', 'lw v0, 0x34(sp)', 'lw ra, 0x4c(sp)', 'lw s5, 0x40(sp)', 'lw s6, 0x44(sp)', 'lw s7, 0x48(sp)', 'jr ra', 'addiu sp, sp, 0x50']
    # oap: apply the switches to the PATCH words (table ptab: address, on, off, bit), FlushCache after a write
    S += ['oap:', f'lui t0, {H(FLAGS)}', f'lbu t6, {L(FLAGS)}(t0)', *la('t0', D['ptab']), f'addiu t5, t0, {16 * len(PATCH)}', 'move t9, zero',
          'oa1:', 'lw t1, 0(t0)', 'lw t2, 4(t0)', 'lw t3, 8(t0)', 'lw t4, 12(t0)', 'lw t7, 0(t1)', 'and t4, t4, t6', 'beqz t4, oa2', 'move t8, t2',
          'move t8, t3', 'oa2:', 'beq t7, t8, oa3', 'nop', 'beq t7, t2, oa4', 'nop', 'bne t7, t3, oa3', 'nop',
          'oa4:', 'sw t8, 0(t1)', 'addiu t9, zero, 1',
          'oa3:', 'addiu t0, t0, 16', 'bne t0, t5, oa1', 'nop', 'beqz t9, oa9', 'nop', f'j {FLUSH}', 'nop', 'oa9:', 'jr ra', 'nop']
    return S


TOP = {'opt', 'odr', 'ost', 'drw', 'box', 'out', 'oap'}


def place(S, tables):
    """blocks (split at TOP labels) placed best fit, then the tables (bytes) in what is left -> words, labels"""
    blocks = []; cur = []
    for l in S:
        if l.endswith(':') and cur and l[:-1] in TOP: blocks.append(cur); cur = []
        cur.append(l)
    blocks.append(cur)
    size = lambda b: 4 * sum(1 for l in b if not l.endswith(':'))
    caves = [[lo, lo, hi, []] for lo, hi in CAVES]
    for b in sorted(blocks, key=lambda b: -size(b)):
        fit = [c for c in caves if c[1] + size(b) <= c[2]]
        assert fit, 'plus de place pour ' + b[0]
        c = min(fit, key=lambda c: c[2] - c[1]); c[3].append(b); c[1] += size(b)
    tab_at = {}
    for name, t in tables:
        fit = [c for c in caves if c[1] + len(t) <= c[2]]
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
    tab = b''.join(struct.pack('<I', D['l%d' % i]) for i in range(len(LINES)))
    D2 = dict(D); D2['tab'] = 0; D2['ptab'] = 0           # first pass: where the tables land
    _, lab = place(routines(D2), [('tab', tab), ('ptab', ptab)])
    D2['tab'] = lab['tab']; D2['ptab'] = lab['ptab']
    words, lab = place(routines(D2), [('tab', tab), ('ptab', ptab)])
    assert lab['tab'] == D2['tab'] and lab['ptab'] == D2['ptab']
    return words, lab, d


def ops(disc):
    ms = disc.read_file('/MODE_SEL.BIN'); ex = disc.read_file('/SCES_009.92')
    where = lambda a: ('/MODE_SEL.BIN', ms, OVL) if a >= OVL else ('/SCES_009.92', ex, 0x8000F800)
    assert struct.unpack_from('<I', ms, HOOK - OVL)[0] == J(3, HOOK_FN)
    c, l, d = build()
    P = [(a, x) for a, x in c] + [(DATA[0] + i, struct.unpack_from('<I', d, i)[0]) for i in range(0, len(d), 4)] + [(HOOK, J(3, l['opt']))]
    out = []
    for a, x in P:
        f, b, base = where(a); out.append(['w', f, a - base, struct.unpack_from('<I', b, a - base)[0], x])
    return out
