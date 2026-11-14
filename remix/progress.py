# In-game progress page: hold SELECT on the mode select screen (MODE_SEL) to show a panel with the 100 % checklist
# (hidden riders, Mirror, Hard, Hard + Mirror, SPECIAL boards, Free Style trophies, percentage).
# Code + strings go after the end of MODE_SEL.BIN, which grows by one sector (the file then moves to the last
# sectors of the credits movie STAFFE.STR, cut by 0.5 s; its heap starts after it); the letters are drawn by the game's own text routine (func_80012CA0, menu font at VRAM
# (512,48), 8x12) into a private primitive buffer at 0x801F4000 / 0x801F6000 (0x801F2000: the options' switches) (free RAM below the stack, double
# buffered). Hook: the TV function of MODE_SEL calls func_8002E228 (frame buffer index) at 0x800643B4.
import struct
from asm import asm
ORG = 0x800832c8                  # end of MODE_SEL.BIN (0x8005AEA8 + 0x28420)
LIMIT = 0x80083ea8                # end of the 82nd sector (heap start of MODE_SEL)
HOOK = 0x800643b4; HOOK_OLD = 0x0c00b88a     # jal func_8002E228
TEXT, FONT, CLUT, PAD = 0x80012ca0, 0x80070648, 0x733e, 0x800832ba
SELECT = 0x100
OTOFF = 0
X0, X1, X2, Y0, DY = -152, -68, -12, -96, 13   # label / state / hint columns; (0, 0) is near the centre of the screen
# (label, address & 0xffff in 0x8005xxxx, mask, value string, hint) -- in English, like the game: mask 1 with a value = title colour
LINES = [('PROGRESS', 0, 1, 'pct', ''),
         ('BOSS', 0x7440, 0x10, None, '1ST IN MIRROR COMP.'),
         ('GRAY', 0x7440, 0x20, None, 'HALFPIPE 37.6/MASTER'),
         ('SNOWMAN', 0x7440, 0x40, None, '1ST HARD/30 TROPHIES'),
         ('MIRROR', 0x7444, 0xffff, None, 'COMPETITION PODIUM'),
         ('HARD', 0x7446, 0xffff, None, 'MIRROR COMP. PODIUM'),
         ('HARD+MIRROR', 0x7446, 0xffff, None, 'L1+R1+X (WITH HARD)'),
         ('COURSES', 0, 0, 'pis', 'COMPETITION PODIUM'),
         ('MIRROR CRS', 0, 0, 'pim', 'MIRROR COMP. PODIUM'),
         ('SPECIAL', 0, 0, 'spc', 'FREE STYLE RECORDS'),
         ('TROPHIES', 0, 0, 'tro', 'BEAT EACH RECORD')]
VALUES = [('pct', b'  0%\0'), ('pis', b'  0/10\0'), ('pim', b'  0/10\0'), ('spc', b'  0/3\0'), ('tro', b'  0/30\0')]
TOTAL = 40          # 3 riders + Mirror + Hard + all courses + all mirror courses + 3 boards + 30 trophies

def hl(a): h = (a + 0x8000) >> 16; return h, a - (h << 16)

def block():
    """-> (org, bytes, hook word)"""
    def build(L):
        def la(r, name): h, l = hl(L.get(name, 0)); return [f'lui {r}, {h}', f'addiu {r}, {r}, {l}']
        def drw(x, y, s, rgb):                    # draw string s at (x, y) with colour struct rgb (labels or regs)
            out = [f'addiu t4, zero, {x}', f'addiu t5, zero, {y}' if isinstance(y, int) else f'lw t5, {y}']
            out += la('t6', s) if not s.startswith('$') else [f'move t6, {s[1:]}']
            out += la('t7', rgb) if not rgb.startswith('$') else [f'lw t7, {rgb[1:]}']
            return out + ['jal drw', 'nop']
        fh, fl = hl(FONT); ph, pl = hl(PAD)
        c = ['prog:', 'addiu sp, sp, -0x50', 'sw ra, 0x4c(sp)', 'sw s5, 0x40(sp)', 'sw s6, 0x44(sp)', 'sw s7, 0x48(sp)',
             'jal 0x8002e228', 'nop', 'sw v0, 0x34(sp)',
             f'lui t0, {ph}', f'lhu t0, {pl}(t0)', 'nop', f'andi t0, t0, {SELECT}', 'beqz t0, out',
             'sll v1, v0, 2', 'addu v1, v1, v0', 'sll v1, v1, 2', 'addu v1, v1, s4', 'lw v1, 4(v1)', 'sll v0, v0, 13',
             f'addiu s5, v1, {OTOFF}',                                  # OT entry (front)
             'lui s6, 0x801f', 'addu s6, s6, v0', 'ori s6, s6, 0x4000',
             # counts: N (0x30) = riders + Mirror + Hard + boards + trophies (38), S (0x3c) boards, T (0x38) trophies
             'lui s7, 0x8005', 'lhu a0, 0x7440(s7)', 'nop', 'srl a0, a0, 4', 'jal pc', 'andi a0, a0, 7', 'move t3, v0',
             'lhu a0, 0x7442(s7)', 'jal pc', 'andi a0, a0, 7', 'sw v0, 0x3c(sp)', 'addu t3, t3, v0',
             'lhu a0, 0x7448(s7)', 'jal pc', 'andi a0, a0, 0x3ff', 'move t1, v0',
             'lhu a0, 0x744a(s7)', 'jal pc', 'andi a0, a0, 0x3ff', 'addu t1, t1, v0',
             'lhu a0, 0x744c(s7)', 'jal pc', 'andi a0, a0, 0x3ff', 'addu t1, t1, v0', 'sw t1, 0x38(sp)', 'addu t3, t3, t1',
             'lhu t0, 0x7444(s7)', 'lhu t2, 0x7446(s7)', 'sltu t0, zero, t0', 'sltu t2, zero, t2', 'addu t3, t3, t0', 'addu t3, t3, t2',
             'lhu t0, 0x743c(s7)', 'lhu t2, 0x743e(s7)', 'sw t0, 0x20(sp)', 'sw t2, 0x24(sp)', 'sltiu t0, t0, 10', 'sltiu t2, t2, 10',
             'addiu t3, t3, 2', 'subu t3, t3, t0', 'subu t2, t3, t2',
             'addiu t0, zero, 100', 'mult t2, t0', 'mflo t1', f'addiu t0, zero, {TOTAL}', 'nop', 'divu t1, t0', 'mflo a0']
        c += la('a1', 'pct') + ['jal n3', 'nop', 'lw a0, 0x20(sp)'] + la('a1', 'pis') + ['jal n3', 'nop', 'lw a0, 0x24(sp)'] + la('a1', 'pim') + ['jal n3', 'nop', 'lw a0, 0x3c(sp)'] + la('a1', 'spc') + ['jal n3', 'nop', 'lw a0, 0x38(sp)'] + la('a1', 'tro') + ['jal n3', 'nop']
        # one line per table entry [u16 addr, u16 mask, u32 label, u32 value]: value string (title / counts) or OK / --
        c += la('s7', 'lines') + [f'addiu t0, zero, {Y0}', 'sw t0, 0x28(sp)',
             'fl:', 'lw t6, 4(s7)', 'lhu t1, 0(s7)', 'beqz t6, fe', 'lhu t2, 2(s7)', 'lw t3, 8(s7)']
        c += la('t7', 'rgbn') + ['beqz t3, fg', 'move t6, t3', 'beqz t2, f1', 'nop', 'j f1', 'addiu t7, t7, 8',
             'fg:', 'lui t0, 0x8005', 'addu t0, t0, t1', 'lhu t0, 0(t0)'] + la('t6', 'sno') + ['and t0, t0, t2',
             'beqz t0, f1', 'nop', 'addiu t7, t7, 4', 'addiu t6, t6, 5',
             'f1:', 'sw t7, 0x30(sp)', f'addiu t4, zero, {X1}', 'lw t5, 0x28(sp)', 'jal drw', 'nop',
             'lw t7, 0x30(sp)', f'addiu t4, zero, {X0}', 'lw t5, 0x28(sp)', 'lw t6, 4(s7)', 'jal drw', 'nop',
             f'addiu t4, zero, {X2}', 'lw t5, 0x28(sp)', 'lw t6, 12(s7)'] + la('t7', 'rgbh') + ['jal drw', 'nop',
             'lw t0, 0x28(sp)', 'addiu s7, s7, 16', f'addiu t0, t0, {DY}', 'j fl', 'sw t0, 0x28(sp)', 'fe:']
        yb = Y0 + DY * len(LINES)
        # panel: TILE (dark blue) behind the text
        c += ['lw t0, 0(s5)', 'lui t1, 0x300', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'and t3, t0, t2', 'or t3, t3, t1', 'sw t3, 0(s6)',
              'lui t3, 0x6030', 'ori t3, t3, 0x1810', 'sw t3, 4(s6)',
              f'lui t3, {(Y0 - 6) & 0xffff}', f'ori t3, t3, {(X0 - 16) & 0xffff}', 'sw t3, 8(s6)',
              f'lui t3, {yb + 4 - (Y0 - 6)}', 'ori t3, t3, 320', 'sw t3, 12(s6)',
              'lui t1, 0xff00', 'and t0, t0, t1', 'and t3, s6, t2', 'or t0, t0, t3', 'sw t0, 0(s5)',
              'out:', 'lw v0, 0x34(sp)', 'lw ra, 0x4c(sp)', 'lw s5, 0x40(sp)', 'lw s6, 0x44(sp)', 'lw s7, 0x48(sp)', 'jr ra', 'addiu sp, sp, 0x50',
              # drw: t4 x, t5 y, t6 string, t7 colour -> func_80012CA0(ot, prims, font, clut, x, y, s, colour, 0)
              'drw:', 'sw ra, 0x2c(sp)', 'sw t4, 0x10(sp)', 'sw t5, 0x14(sp)', 'sw t6, 0x18(sp)', 'sw t7, 0x1c(sp)', 'sw zero, 0x20(sp)',
              'move a0, s5', 'move a1, s6', f'lui a2, {fh}', f'addiu a2, a2, {fl}', f'jal {TEXT}', f'addiu a3, zero, {CLUT}',
              'lw ra, 0x2c(sp)', 'move s6, v0', 'jr ra', 'nop',
              # pc: a0 -> v0 = number of bits set
              'pc:', 'move v0, zero', 'pl:', 'beqz a0, pd', 'andi t0, a0, 1', 'addu v0, v0, t0', 'j pl', 'srl a0, a0, 1', 'pd:', 'jr ra', 'nop',
              # n3: a0 value (0..999), a1 -> 3 characters, right-aligned
              'n3:', 'addiu t0, zero, 10', 'divu a0, t0', 'mflo t1', 'mfhi t2', 'addiu t2, t2, 0x30', 'sb t2, 2(a1)', 'divu t1, t0',
              'mflo t3', 'mfhi t4', 'addiu t5, zero, 0x20', 'sb t5, 0(a1)', 'sb t5, 1(a1)', 'beqz t1, nd', 'addiu t4, t4, 0x30', 'sb t4, 1(a1)',
              'beqz t3, nd', 'addiu t3, t3, 0x30', 'sb t3, 0(a1)', 'nd:', 'jr ra', 'nop']
        return c
    def layout(code_end):
        data = bytearray(); L = {}
        def put(name, b):
            L[name] = code_end + len(data); data.extend(b)
        put('lines', bytes(16 * (len(LINES) + 1)))
        put('rgbn', bytes([110, 110, 120, 32])); put('rgbok', bytes([90, 230, 120, 32])); put('rgbt', bytes([255, 170, 70, 32]))
        put('rgbh', bytes([150, 140, 100, 32]))
        for i, (name, a, m, v, h) in enumerate(LINES): put('l%d' % i, name.encode() + b'\0'); put('h%d' % i, h.encode() + b'\0')
        for k, t in VALUES: put(k, t)
        put('sno', b'  --\0'); put('sok', b'  OK\0'); assert L['sok'] == L['sno'] + 5
        f = L['lines'] - code_end
        for i, (name, a, m, v, h) in enumerate(LINES): struct.pack_into('<HHIII', data, f + 16 * i, a, m, L['l%d' % i], L[v] if v else 0, L['h%d' % i])
        return data, L
    code, L = asm(build({}), ORG, {k: 0 for k in ['pc', 'n3', 'drw']})
    data, L = layout(ORG + 4 * len(code))
    code, labs = asm(build(L), ORG, L)
    data, L2 = layout(ORG + 4 * len(code)); assert L2 == L
    blob = b''.join(struct.pack('<I', w) for _, w in code) + bytes(data)
    assert ORG + len(blob) <= LIMIT, hex(ORG + len(blob))
    return ORG, blob, (3 << 26) | ((labs['prog'] >> 2) & 0x3ffffff)

if __name__ == '__main__':
    o, b, h = block(); print(hex(o), len(b), 'octets, reste', LIMIT - o - len(b), 'crochet', hex(h))
