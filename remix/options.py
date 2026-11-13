# In-game options (mod `options`, v26): on the mode select screen, hold R1 to show the REMIX OPTIONS panel; while R1
# is held, L1 / L2 / R2 switch the rear view (mod rear), the live half-pipe marks (mod hplive) and the unlock
# announcements (mod news) on or off.
#
# The switches are bits of 0x80057438 (bit set = off), a byte of the progress block that the game saves on the
# memory card but never reads (see docs/progression.md): they follow the save. Each of those mods tests its bit.
# MODE_SEL: the TV function (func_80064200, every frame, s4 = its OT table, s1 = frame buffer index) calls
# func_80028BDC (GetClut) at 0x800643E4: that call goes through opt (dead functions of MODE_SEL), which then reads the
# pad (0x800832BA, as the progress page), switches on the new presses, and draws the panel with the game's text
# routine (func_80012CA0, menu font) into a private primitive buffer (0x801F8000 + 0x800 per frame buffer), on a
# dark box (TILE), like the progress page.
import struct
from asm import asm

OVL = 0x8005AEA8
HOOK, HOOK_FN = 0x800643E4, 0x80028BDC
TEXT, FONT, CLUT, PAD = 0x80012CA0, 0x80070648, 0x733E, 0x800832BA
FLAGS = 0x80057438
R1, L1, L2, R2 = 0x8, 0x4, 0x1, 0x2
PRIMS = 0x801F8000
CODE = (0x800654A8, 0x8006562C)        # after crewrank's code (same dead function)
CODE2 = (0x8006F680, 0x8006F71C)       # drw, box
CODE3 = (0x8006F800, 0x8006F83C)       # out
DATA = (0x8005C8B0, 0x8005C968)        # after crewrank's data
X0, X1, Y0, DY = -150, 70, 30, 13
# (label, bit, pad bit)
LINES = [('L1  REAR VIEW (CIRCLE)', 1, L1), ('L2  LIVE HALF-PIPE MARKS', 2, L2), ('R2  UNLOCK ANNOUNCEMENTS', 4, R2)]
TITLE = 'REMIX OPTIONS'


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)


def data():
    d = bytearray(); lab = {}
    def put(n, b): lab[n] = DATA[0] + len(d); d.extend(b); d.extend(bytes((-len(d)) % 4))
    put('prev', bytes(4)); put('rgbt', bytes([255, 170, 70, 32])); put('rgbn', bytes([150, 140, 100, 32]))
    put('rgbon', bytes([90, 230, 120, 32])); put('rgboff', bytes([110, 110, 120, 32]))
    put('title', TITLE.encode() + b'\0'); put('on', b'ON\0'); put('off', b'OFF\0')
    for i, (t, b, p) in enumerate(LINES): put('l%d' % i, t.encode() + b'\0')
    assert DATA[0] + len(d) <= DATA[1], hex(DATA[0] + len(d))
    return bytes(d), lab


def build():
    d, D = data()
    # pointer table for the three labels (after the data)
    tab = DATA[0] + len(d); d = d + b''.join(struct.pack('<I', D['l%d' % i]) for i in range(len(LINES)))
    assert DATA[0] + len(d) <= DATA[1]
    la = lambda r, a: [f'lui {r}, {H(a)}', f'addiu {r}, {r}, {L(a)}']
    S = ['opt:', 'addiu sp, sp, -0x50', 'sw ra, 0x4c(sp)', 'sw s5, 0x40(sp)', 'sw s6, 0x44(sp)', 'sw s7, 0x48(sp)',
         f'jal {HOOK_FN}', 'nop', 'sw v0, 0x34(sp)',
         f'lui t0, {H(PAD)}', f'lhu t1, {L(PAD)}(t0)', f'lui t2, {H(D["prev"])}', f'lw t3, {L(D["prev"])}(t2)', f'sw t1, {L(D["prev"])}(t2)',
         f'andi t0, t1, {R1}', 'beqz t0, out', 'nor t4, t3, zero', 'and t4, t4, t1',            # t4 = new presses
         f'lui t5, {H(FLAGS)}', f'lbu t6, {L(FLAGS)}(t5)']
    for t, bit, pb in LINES:
        S += [f'andi t7, t4, {pb}', f'beqz t7, sk{bit}', 'nop', f'xori t6, t6, {bit}', f'sk{bit}:']
    S += ([f'sb t6, {L(FLAGS)}(t5)', 'sw t6, 0x38(sp)',
          'sll v1, s1, 2', 'addu v1, v1, s1', 'sll v1, v1, 2', 'addu v1, v1, s4', 'lw s5, 4(v1)', 'sll v0, s1, 11',
          f'lui s6, {H(PRIMS)}', 'addu s6, s6, v0', f'addiu s6, s6, {L(PRIMS)}',
          f'addiu t4, zero, {X0}', f'addiu t5, zero, {Y0}'] + la('t6', D['title']) + la('t7', D['rgbt']) + ['jal drw', 'nop',
          'move s7, zero',
          'ol:', 'sw s7, 0x30(sp)', 'sll t0, s7, 2'] + la('t1', tab) + ['addu t1, t1, t0', 'lw t6, 0(t1)', f'addiu t4, zero, {X0}', 'sll t5, s7, 3', 'addu t5, t5, s7',
          'sll t0, s7, 2', 'addu t5, t5, t0', f'addiu t5, t5, {Y0 + DY}'] + la('t7', D['rgbn']) + ['sw t5, 0x28(sp)', 'jal drw', 'nop',
          # state: bit of this line (1 << s7) set = OFF
          'lw s7, 0x30(sp)', 'lw t0, 0x38(sp)', 'nop', 'srlv t0, t0, s7', 'andi t0, t0, 1'] + la('t6', D['on']) + la('t7', D['rgbon']) + ['beqz t0, os', 'nop'] +
          la('t6', D['off']) + la('t7', D['rgboff']) + ['os:', f'addiu t4, zero, {X1}', 'lw t5, 0x28(sp)', 'jal drw', 'nop',
          'lw s7, 0x30(sp)', 'nop', 'addiu s7, s7, 1', f'slti t0, s7, {len(LINES)}', 'bnez t0, ol', 'nop',
          'j box', 'nop'])
    yb = Y0 + DY * (len(LINES) + 1)
    S2 = ['drw:', 'sw ra, 0x2c(sp)', 'sw t4, 0x10(sp)', 'sw t5, 0x14(sp)', 'sw t6, 0x18(sp)', 'sw t7, 0x1c(sp)', 'sw zero, 0x20(sp)',
          'move a0, s5', 'move a1, s6', f'lui a2, {H(FONT)}', f'addiu a2, a2, {L(FONT)}', f'jal {TEXT}', f'addiu a3, zero, {CLUT}',
          'lw ra, 0x2c(sp)', 'move s6, v0', 'jr ra', 'nop',
          # box: TILE (dark blue) behind the text, linked last (drawn first)
          'box:', 'lw t0, 0(s5)', 'lui t1, 0x300', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'and t3, t0, t2', 'or t3, t3, t1', 'sw t3, 0(s6)',
          'lui t3, 0x6030', 'ori t3, t3, 0x1810', 'sw t3, 4(s6)', f'lui t3, {(Y0 - 6) & 0xffff:#x}', f'ori t3, t3, {(X0 - 10) & 0xffff:#x}', 'sw t3, 8(s6)',
          f'lui t3, {yb + 4 - (Y0 - 6)}', f'ori t3, t3, {X1 + 50 - (X0 - 10)}', 'sw t3, 12(s6)',
          'lui t1, 0xff00', 'and t0, t0, t1', 'and t3, s6, t2', 'or t0, t0, t3', 'j out', 'sw t0, 0(s5)']
    S3 = ['out:', 'lw v0, 0x34(sp)', 'lw ra, 0x4c(sp)', 'lw s5, 0x40(sp)', 'lw s6, 0x44(sp)', 'lw s7, 0x48(sp)', 'jr ra', 'addiu sp, sp, 0x50']
    lab = {'drw': 0, 'box': 0, 'out': 0}
    for _ in range(2):
        c2, l2 = asm(S2, CODE2[0], lab); lab.update(l2)
        c3, l3 = asm(S3, CODE3[0], lab); lab.update(l3)
        c, l = asm(S, CODE[0], lab); lab.update(l)
    assert c[-1][0] < CODE[1] and c2[-1][0] < CODE2[1] and c3[-1][0] < CODE3[1], (hex(c[-1][0]), hex(c2[-1][0]))
    return c + c2 + c3, lab, d


def ops(disc):
    ms = disc.read_file('/MODE_SEL.BIN'); w = lambda a: struct.unpack_from('<I', ms, a - OVL)[0]
    J = lambda t: (3 << 26) | ((t >> 2) & 0x3ffffff)
    assert w(HOOK) == J(HOOK_FN)
    c, l, d = build()
    P = [(a, x) for a, x in c] + [(DATA[0] + i, struct.unpack_from('<I', d, i)[0]) for i in range(0, len(d), 4)] + [(HOOK, J(l['opt']))]
    return [['w', '/MODE_SEL.BIN', a - OVL, w(a), x] for a, x in P]
