# In-game switches of the other mods (part of the mod `options`, v28): each mod of BITS can be switched off in the
# REMIX OPTIONS panel. Its hooks (remix/toggle_sites.py: the instructions and data words of the game it changes, not
# its code in dead functions) get back their original words while it is off.
#
# Where: a block (routine `tap` + table) at the end of MODE_SEL.BIN, which grows by one more sector (padded to 82
# sectors first, so that the block has the same address with or without the progress page); MODE_SEL's heap starts
# after it (exe 0x800100B4). Every frame of the mode select screen, `tins` (in the options' code) copies the block to
# 0x801F2000 (free RAM in every scene: checked with a pattern through the menus, Free Style, 2 players, half-pipe and the
# competition) and puts `jal tap` in place of the main loop's call of the overlay (0x8001228C, exe in memory only: the
# disc keeps the original call, so nothing jumps there before the block exists). The call that was there (the game's
# `jal func_8005AEAC`, or the mod max's) is kept at NEXT and `tap` ends with it.
# tap (each scene, before the overlay runs): for each group of the table (one mod, one file):
#   overlay group: when the mod is off and the overlay just loaded still has the mod's word at the group's first site
#     (it comes patched from the disc), the original words are written back;
#   exe group: when the mod is on the disc (a word of its own code is there), every site gets its patched or original
#     word as the switch says.
#   then FlushCache; with max off, the chained call goes to the overlay directly.
import struct
from asm import asm

OVL, EXE_BASE = 0x8005AEA8, 0x8000F800
HI = 0x801F2000                      # the block in RAM
NEXTA = HI + 0x1FFC                  # the call that was at CALL (not copied over)
CALL, ENTRY = 0x8001228C, 0x8005AEAC
FLUSH = 0x8003CB2C
FLAGS = 0x80057438
SRC, SRC_END = 0x80083C00, 0x800846A8            # the block in MODE_SEL (end of its 83rd sector)
SCREEN = (SRC_END, SRC_END + 0x800)             # one more sector: the REMIX screen's code and data (remix/options.py)
FILE_END = SCREEN[1] - OVL                       # MODE_SEL padded to 84 sectors (same addresses with or without the progress page)
HEAP_WORD, HEAP = 0x800100B4, SCREEN[1]
BITS = {'special': 8, 'hardmirror': 9, 'riders': 10, 'outfits': 11, 'max': 12, 'bam': 13, 'progress': 14, 'skipq': 15, 'crew': 16}
MAX_BIT = BITS['max']


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)
def J(op, t): return (op << 26) | ((t >> 2) & 0x3ffffff)


def table(pkg):
    """group: bit, kind (0 overlay, 1 exe), count, check address, check word; entries: overlay = word index from OVL,
    original (halfwords); exe = word index from 0x80010000, original, patched"""
    import toggle_sites
    out = bytearray()
    for mod, bit in BITS.items():
        ops = {(op[1], op[2]): op for op in pkg['ops'].get(mod, []) if op[0] == 'w'}
        if not ops: continue
        by_file = {}
        for f, a in toggle_sites.SITES.get(mod, []):
            base = EXE_BASE if f == '/SCES_009.92' else OVL
            op = ops.get((f, a - base))
            if op is None or op[3] == op[4]: continue
            by_file.setdefault(f, []).append((a, op[3], op[4]))
        for f, sites in by_file.items():
            exe = f == '/SCES_009.92'
            if exe:      # presence check: a word of the mod's own code in the exe
                site_set = {a for a, _, _ in sites}
                cave = [op for (ff, o), op in ops.items() if ff == f and o + EXE_BASE not in site_set and op[3] != op[4]]
                chk = (cave[0][2] + EXE_BASE, cave[0][4])
            else:
                chk = (sites[0][0], sites[0][2])
            out += struct.pack('<BBHII', bit, int(exe), len(sites), *chk)
            for a, o, n in sites:
                if exe: out += struct.pack('<HII', (a - 0x80010000) >> 2, o, n)
                else: out += struct.pack('<HI', (a - OVL) >> 2, o)
            out += bytes((-len(out)) % 4)
    return bytes(out) + b'\xff' + bytes(3)


def tap_code(tab_at):
    S = ['tap:', 'addiu sp, sp, -0x20', 'sw ra, 0x18(sp)', 'sw a0, 0x10(sp)', 'lui t0, 0x8005', f'lw t9, {FLAGS & 0xffff:#x}(t0)',
         f'lui t0, {H(tab_at)}', f'addiu t0, t0, {L(tab_at)}',
         'tg:', 'lbu t1, 0(t0)', 'addiu at, zero, 0xff', 'beq t1, at, td', 'lbu t2, 1(t0)',
         'lhu t3, 2(t0)', 'lw t4, 4(t0)', 'lw t5, 8(t0)', 'srlv t6, t9, t1', 'andi t6, t6, 1', 'addiu t7, t0, 12',
         'lw t8, 0(t4)', 'addiu v0, zero, 6', 'beqz t2, tg1', 'nop', 'addiu v0, zero, 10',
         'tg1:', 'bne t8, t5, tsk', 'nop', 'bnez t2, tex', 'nop', 'beqz t6, tsk', 'nop',
         # overlay group, mod off: original words back
         'tov:', 'lhu a1, 0(t7)', 'lhu a2, 2(t7)', 'lhu a3, 4(t7)', 'sll a1, a1, 2', 'sll a3, a3, 16', 'or a2, a2, a3',
         f'lui at, {H(OVL)}', f'addiu at, at, {L(OVL)}', 'addu a1, a1, at', 'sw a2, 0(a1)', 'addiu t3, t3, -1', 'bnez t3, tov', 'addiu t7, t7, 6',
         'j tnx', 'nop',
         # exe group: patched or original word as the switch says
         'tex:', 'lhu a1, 0(t7)', 'lhu a2, 2(t7)', 'lhu a3, 4(t7)', 'bnez t6, te1', 'nop', 'lhu a2, 6(t7)', 'lhu a3, 8(t7)', 'nop',
         'te1:', 'sll a3, a3, 16', 'or a2, a2, a3', 'sll a1, a1, 2', 'lui at, 0x8001', 'addu a1, a1, at', 'sw a2, 0(a1)',
         'addiu t3, t3, -1', 'bnez t3, tex', 'addiu t7, t7, 10', 'j tnx', 'nop',
         'tsk:', 'mult t3, v0', 'mflo t3', 'addu t7, t7, t3',
         'tnx:', 'addiu t7, t7, 3', 'addiu at, zero, -4', 'j tg', 'and t0, t7, at',
         # the call kept at NEXT (jal target), the overlay itself with max off
         'td:', f'lui t0, {H(NEXTA)}', f'lw t1, {L(NEXTA)}(t0)', 'nop', 'sll t1, t1, 6', 'srl t1, t1, 4', 'lui at, 0x8000', 'or t1, t1, at',
         f'lui t2, {H(ENTRY)}', f'addiu t2, t2, {L(ENTRY)}', f'srl t3, t9, {MAX_BIT}', 'andi t3, t3, 1', 'beqz t3, td1', 'nop', 'move t1, t2',
         'td1:', 'lui at, 0x8000', 'bne t1, at, td2', 'nop', 'move t1, t2',
         'td2:', 'sw t1, 0x14(sp)', f'jal {FLUSH}', 'nop', 'lw t1, 0x14(sp)', 'lw a0, 0x10(sp)', 'lw ra, 0x18(sp)', 'jr t1', 'addiu sp, sp, 0x20']
    return S


def block(pkg):
    """-> bytes of the block (assembled at HI)"""
    c0, _ = asm(tap_code(0), HI)
    tab_at = c0[-1][0] + 4
    c, l = asm(tap_code(tab_at), HI)
    code = b''.join(struct.pack('<I', w) for _, w in c)
    b = code + table(pkg)
    assert len(b) <= SRC_END - SRC, len(b)
    return b + bytes((-len(b)) % 4)


def installer(la):
    """tins: copy the block to HI, put the call to tap in the exe (once), FlushCache"""
    return ['tins:', *la('t0', SRC), *la('t1', HI), *la('t2', SRC_END),
            'ti1:', 'lw t3, 0(t0)', 'addiu t0, t0, 4', 'sw t3, 0(t1)', 'bne t0, t2, ti1', 'addiu t1, t1, 4',
            f'lui t0, {H(CALL)}', f'lw t1, {L(CALL)}(t0)', f'lui t2, {J(3, HI) >> 16:#x}', f'ori t2, t2, {J(3, HI) & 0xffff:#x}',
            'beq t1, t2, ti9', 'nop', f'lui t3, {H(NEXTA)}', f'sw t1, {L(NEXTA)}(t3)', f'sw t2, {L(CALL)}(t0)', f'j {FLUSH}', 'nop',
            'ti9:', 'jr ra', 'nop']


def ops(pkg):
    """MODE_SEL padded, the block, MODE_SEL's heap start (raw: the progress page may have moved it already)"""
    b = block(pkg)
    out = [['padto', '/MODE_SEL.BIN', FILE_END]]
    out += [['w', '/MODE_SEL.BIN', SRC - OVL + i, 0, struct.unpack_from('<I', b, i)[0]] for i in range(0, len(b), 4)]
    out.append(['b', '/SCES_009.92', HEAP_WORD - EXE_BASE, struct.pack('<I', HEAP).hex()])
    return out
