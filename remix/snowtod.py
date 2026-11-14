# Snowman in the competition (part of the mod `riders`, v27): his own animations (TOD_SM) instead of the human ones.
#
# The competition loads one human TOD (TOD_MANx, 100 motions) at the 1st stage, at 0x80195394, for every rider; the
# Snowman model (7 objects) then got the first bones of a human ("badly assembled", leaning). Free Style loads TOD_SM
# (46 motions) too and gives the player a motion table (rider + 0x204, 100 words: motion start + 8) whose human motion
# numbers are mapped onto Snowman's (MAP, read in the emulator from a Free Style race with Snowman).
#   exe: the competition loader func_8001CCE0 queues its files with func_80013BD0 (file, dest, &ptr, flags); its call at
#        0x8001D014 goes to `tsm`, which also queues TOD_SM (file 237) into the heap (dest 0) when g_rider = 6, its
#        address into TSM_PTR (every stage: each overlay has its own heap; ~200 KB stay free in the Boarder Cross).
#   SBC2: the race loop's call of the bar function (0x8005F56C) goes to `snw` first: when g_rider = 6 and TOD_SM is
#        there, it is converted once with the overlay's own routines (header: offsets -> addresses, then every motion:
#        func_8008655C / func_8008CC7C, as FREE.BIN's func_8008F878 / func_80095F98 do for its TODs), and the player's
#        three motion tables (D_8009B9A8[0] + 0x204: motion + 8, + 0x39C: its frame count, + 0x530: its first frame's
#        number, as the racer init func_80064674 makes them) are written from MAP every frame. (With the first table
#        only, the TOD player ran off the end of Snowman's shorter motions: address error at 0x8008C278.)
import struct
from asm import asm

EXE_BASE, OVL = 0x8000F800, 0x8005AEA8
QUEUE, LOAD_SITE = 0x80013BD0, 0x8001D014
TOD_SM_FILE = 237
EXE_CAVE, EXE_CAVE_END = 0x8003EB30, 0x8003EB80          # end of the dead function func_8003EAC4 (its start: options)
TSM_PTR = EXE_CAVE_END - 4
G_RIDER = 0x80057408
SBC2_SITE, BAR_FN = 0x8005F56C, 0x8006D2A4
HDR_RELOC, MOT_RELOC = 0x8008655C, 0x8008CC7C
RIDERS = 0x8009B9A8                                     # detailed riders: [0] = the player
SBC2_CAVE, SBC2_CAVE_END = 0x80062DB4, 0x8006304C        # dead function func_80062DB4
MAP = [0, 1, 2, 3, 4, 5, 6, 7, 6, 8, 9, 8, 9, 6, 7, 8, 9, 3, 4, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
       26, 27, 28, 29, 30, 31, 3, 3, 1, 2, 3, 4, 5, 32, 33, 32, 8, 9, 8, 9, 32, 33, 8, 9, 3, 4, 43, 44, 45, 13, 14, 15, 16, 17,
       18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 28, 31, 30, 3, 3, 39, 40, 41, 42, 37, 38, 37, 38, 37, 38, 34, 35, 36, 35, 36]
assert len(MAP) == 100


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)
def J(op, t): return (op << 26) | ((t >> 2) & 0x3ffffff)


def exe_code():
    S = ['tsm:', 'addiu sp, sp, -0x18', 'sw ra, 0x10(sp)', f'jal {QUEUE}', 'nop',
         'lui t0, 0x8005', f'lh t0, {G_RIDER & 0xffff:#x}(t0)', 'addiu t1, zero, 6', 'bne t0, t1, ts9', 'nop',
         f'addiu a0, zero, {TOD_SM_FILE}', 'move a1, zero', f'lui a2, {H(TSM_PTR)}', f'addiu a2, a2, {L(TSM_PTR)}', f'jal {QUEUE}', 'addiu a3, zero, 1',
         'ts9:', 'lw ra, 0x10(sp)', 'nop', 'jr ra', 'addiu sp, sp, 0x18']
    c, l = asm(S, EXE_CAVE)
    assert c[-1][0] < TSM_PTR, hex(c[-1][0])
    return c, l


def sbc2_code():
    S = ['snw:', 'addiu sp, sp, -0x28', 'sw ra, 0x20(sp)', 'sw s0, 0x18(sp)', 'sw s1, 0x1c(sp)', 'sw a0, 0x10(sp)', 'sw a1, 0x14(sp)',
         'lui t0, 0x8005', f'lh t0, {G_RIDER & 0xffff:#x}(t0)', 'addiu t1, zero, 6', 'bne t0, t1, sn9', 'nop',
         f'lui t0, {H(TSM_PTR)}', f'lw s0, {L(TSM_PTR)}(t0)', 'nop', 'beqz s0, sn9', 'nop',
         'lhu t0, 0(s0)', 'addiu t1, zero, 0x4f54', 'bne t0, t1, sn9', 'nop',                 # "TO"
         'lbu t0, 2(s0)', 'nop', 'beqz t0, sn2', 'nop',                                       # not converted yet
         f'jal {HDR_RELOC}', 'move a0, s0', 'lbu s1, 3(s0)', 'nop',
         'sn1:', 'sll t0, s1, 2', 'addu t0, t0, s0', 'lw a0, 0(t0)', f'jal {MOT_RELOC}', 'nop', 'addiu s1, s1, -1', 'bnez s1, sn1', 'nop',
         # the player's motion table from MAP
         'sn2:', f'lui t0, {H(RIDERS)}', f'lw t0, {L(RIDERS)}(t0)', 'nop', 'beqz t0, sn9', 'addiu t0, t0, 0x204',
         'lui t1, MAPH', 'addiu t1, t1, MAPL', 'addiu t2, t1, 100',
         'sn3:', 'lbu t3, 0(t1)', 'addiu t1, t1, 1', 'sll t3, t3, 2', 'addu t3, t3, s0', 'lw t3, 4(t3)', 'nop',
         'lw t4, 4(t3)', 'lw t5, 8(t3)', 'addiu t3, t3, 8', 'lw t5, 4(t5)', 'sw t3, 0(t0)', 'sw t4, 0x198(t0)', 'sw t5, 0x32c(t0)',
         'bne t1, t2, sn3', 'addiu t0, t0, 4',
         'sn9:', 'lw a0, 0x10(sp)', 'lw a1, 0x14(sp)', 'lw s0, 0x18(sp)', 'lw s1, 0x1c(sp)', 'lw ra, 0x20(sp)', f'j {BAR_FN}', 'addiu sp, sp, 0x28']
    c0, _ = asm([x.replace('MAPH', '0').replace('MAPL', '0') for x in S], SBC2_CAVE)
    mp = c0[-1][0] + 4
    S = [x.replace('MAPH', str(H(mp))).replace('MAPL', str(L(mp))) for x in S]
    c, l = asm(S, SBC2_CAVE)
    m = bytes(MAP) + bytes((-len(MAP)) % 4)
    c += [(mp + i, struct.unpack_from('<I', m, i)[0]) for i in range(0, len(m), 4)]
    assert c[-1][0] < SBC2_CAVE_END, hex(c[-1][0])
    return c, l


def ops(disc):
    exe = disc.read_file('/SCES_009.92'); sb = disc.read_file('/SBC2.BIN')
    we = lambda a: struct.unpack_from('<I', exe, a - EXE_BASE)[0]
    ws = lambda a: struct.unpack_from('<I', sb, a - OVL)[0]
    assert we(LOAD_SITE) == J(3, QUEUE) and ws(SBC2_SITE) == J(3, BAR_FN)
    assert sb[HDR_RELOC - OVL:HDR_RELOC - OVL + 8] == bytes.fromhex('0200829003008790') and ws(MOT_RELOC + 8) == 0x24020002
    ce, le = exe_code(); cs, ls = sbc2_code()
    out = [['w', '/SCES_009.92', a - EXE_BASE, we(a), x] for a, x in ce + [(LOAD_SITE, J(3, le['tsm'])), (TSM_PTR, 0)]]
    out += [['w', '/SBC2.BIN', a - OVL, ws(a), x] for a, x in cs + [(SBC2_SITE, J(3, ls['snw']))]]
    return out
