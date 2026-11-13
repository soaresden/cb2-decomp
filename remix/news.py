# Unlock announcements (mod `news`, v26): back in the menus after a race, a shining banner says what was just won
# (Boss / Gray / Snowman, SPECIAL boards, Mirror, Hard, new courses, Free Style trophies, and the 100 %:
# CONGRATULATIONS, with Jicchi, Nick and Kelly when the mod `crew` is on).
#
# The exe's main loop (0x80012260..) loads each overlay, then calls func_8001B668, the overlay entry, func_8001B718.
# Those two calls become npre / npost (exe, in the dead function 0x8001E630 and the one after it):
#   npost: leaving a menu overlay (word 0 of the overlay: 5 = MODE_SEL, 6 = MAIN_SEL), SNAP = the progress words
#          0x8005743C..0x8005744F (as saved on the memory card), VALID = 1;
#   npre:  entering a menu overlay, what appeared since SNAP (bits that went from 0 to 1) is added to MASK.
# So whatever happens during the races (overlays 8) is announced, and a memory card loaded in a menu is not (SNAP
# is taken when the menu is left). The banner is drawn by the BOARDER / COURSE / BOARD hub of MAIN_SEL (its per
# frame call of func_8005BFD0 becomes nhub, code in dead functions of MAIN_SEL), for FRAMES frames, then MASK = 0:
# one line per item, the game's own text (func_8005E784, as "R1 : MAX"), colour pulsing between gold and white,
# on a dark box (TILE) put at the text's place in the drawing order (see crew.py: the last letter moves).
import struct
from asm import asm

EXE_BASE = 0x8000F800; OVL = 0x8005AEA8
NEWS = 0x8001E630; NEWS_END = 0x8001E7C4            # dead functions of the exe: state (32 bytes) + npre / npost
VALID, MASK, CNT, SNAP = 0, 4, 8, 0xC               # offsets in NEWS; SNAP = 5 words from 0x8005743C
CODE = NEWS + 0x20
PRE, PRE_FN = 0x80012284, 0x8001B668                 # jal func_8001B668 (before the overlay entry)
POST, POST_FN = 0x80012294, 0x8001B718               # jal func_8001B718 (after it)
MENUS = (5, 6)
# MAIN_SEL
HUB, HUB_FN = 0x8005B280, 0x8005BFD0                 # hub loop: jal func_8005BFD0 (delay slot: addiu a0, sp, 0x20)
MS_CODE = (0x8007586C, 0x80075A28)                  # dead functions of MAIN_SEL (no call, jump or pointer to them)
MS_TABLE = (0x80077E2C, 0x80077FA8)
MS_STR = (0x80078F54, 0x800790B8)
MS_CODE2 = (0x80079F3C, 0x8007A074)                # ncomp
MS_CODE3 = (0x80075118, 0x800751C0)                # nbox
TEXTFN, TEXT_LAST, PRIMS = 0x8005E784, 0x8007B2F8, 0x80058E0C
OPT_FLAGS, OPT_BIT = 0x80057438, 4          # in-game options (mod options): bit set = announcements off
FRAMES = 210                                        # hub frames (the hub runs at 30 per second): 7 s
LINE_H, BOX_X, BOX_W = 14, 32, 256
CREW_WORD = (0x8001FBD4, 0x020100FF)                # mod crew: its BASE table (0xff, Yaggi, Jin, Cindy)
UNLOCK_ALL = (0x80063EA8, 0x2403007F)                # mod unlock
# (MASK bits, text): 0x10000 / 0x20000 = complete with / without crew (set by nhub)
LINES = [(0x8000, 'CONGRATULATIONS !'), (0x10000, 'JICCHI NICK KELLY UNLOCKED'), (0x20000, 'GAME COMPLETED !'),
         (0x10, 'BOSS UNLOCKED'), (0x20, 'GRAY UNLOCKED'), (0x40, 'SNOWMAN UNLOCKED'), (0x700, 'SPECIAL BOARD UNLOCKED'),
         (0x800, 'MIRROR MODE UNLOCKED'), (0x1000, 'HARD MODE UNLOCKED'), (0x2000, 'NEW COURSES UNLOCKED'),
         (0x4000, 'NEW TROPHY !')]


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)
def J(op, a): return (op << 26) | ((a >> 2) & 0x3ffffff)


def exe_code():
    menu = ['lui at, 0x8006', 'lw t0, -0x5158(at)', 'nop', 'addiu t0, t0, -5', 'sltiu t0, t0, 2']     # overlay word 0 in 5..6
    S = ['npre:', *menu, 'beqz t0, np9', f'lui t9, {H(NEWS)}', f'addiu t9, t9, {L(NEWS)}', f'lw t0, {VALID}(t9)', 'lui t8, 0x8005',
         'beqz t0, np9', f'lw t2, {MASK}(t9)',
         # riders (0x7440 bits 4..6 -> same bits), SPECIAL boards (0x7442 bits 0..2 -> bits 8..10)
         'lhu t0, 0x7440(t8)', f'lhu t1, {SNAP + 4}(t9)', 'nop', 'nor t1, t1, zero', 'and t0, t0, t1', 'andi t0, t0, 0x70', 'or t2, t2, t0',
         'lhu t0, 0x7442(t8)', f'lhu t1, {SNAP + 6}(t9)', 'nop', 'nor t1, t1, zero', 'and t0, t0, t1', 'andi t0, t0, 7', 'sll t0, t0, 8', 'or t2, t2, t0']
    for o, so, bit in ((0x7444, SNAP + 8, 11), (0x7446, SNAP + 10, 12)):            # Mirror, Hard: 0 -> not 0
        S += [f'lhu t0, {o}(t8)', f'lhu t1, {so}(t9)', 'sltu t0, zero, t0', 'sltiu t1, t1, 1', 'and t0, t0, t1', f'sll t0, t0, {bit}', 'or t2, t2, t0']
    # courses (0x743C / 0x743E: number open) -> bit 13
    S += ['lhu t0, 0x743c(t8)', f'lhu t1, {SNAP}(t9)', 'lhu t3, 0x743e(t8)', f'lhu t4, {SNAP + 2}(t9)', 'sltu t0, t1, t0', 'sltu t3, t4, t3',
          'or t0, t0, t3', 'sll t0, t0, 13', 'or t2, t2, t0', 'move t4, zero']
    # trophies (0x7448, 0x744A, 0x744C: 10 bits each) -> bit 14
    S += ['addiu t1, t8, 0x7448', f'addiu t3, t9, {SNAP + 12}', 'addiu t6, t1, 6',
          'npt:', 'lhu t0, 0(t1)', 'lhu t5, 0(t3)', 'addiu t1, t1, 2', 'nor t5, t5, zero', 'and t0, t0, t5', 'addiu t3, t3, 2', 'bne t1, t6, npt', 'or t4, t4, t0']
    S += ['andi t4, t4, 0x3ff', 'sltu t4, zero, t4', 'sll t4, t4, 14', 'or t2, t2, t4', f'sw t2, {MASK}(t9)',
          'np9:', f'j {PRE_FN}', 'nop']
    S += ['npost:', *menu, 'beqz t0, nq9', f'lui t9, {H(NEWS)}', f'addiu t9, t9, {L(NEWS)}', 'lui t8, 0x8005']
    S += ['addiu t1, t8, 0x743c', f'addiu t2, t9, {SNAP}', 'addiu t3, t1, 20',
          'nqc:', 'lw t0, 0(t1)', 'addiu t1, t1, 4', 'sw t0, 0(t2)', 'bne t1, t3, nqc', 'addiu t2, t2, 4']
    S += ['addiu t0, zero, 1', f'sw t0, {VALID}(t9)', 'nq9:', f'j {POST_FN}', 'nop']
    c, l = asm(S, CODE)
    assert c[-1][0] < NEWS_END, hex(c[-1][0])
    return c, l


def table():
    """-> (table bytes at MS_TABLE[0], strings bytes at MS_STR[0]); entry: u32 mask, s16 x, u16 0, u32 string"""
    tb, st = b'', b''
    for m, t in LINES:
        tb += struct.pack('<IhHI', m, 160 - 4 * len(t), 0, MS_STR[0] + len(st)); st += t.encode() + b'\0'
    tb += bytes(12)
    assert MS_TABLE[0] + len(tb) <= MS_TABLE[1] and MS_STR[0] + len(st) <= MS_STR[1]
    return tb, st


def ms_code():
    S = ['nhub:', 'addiu sp, sp, -0x48', 'sw ra, 0x40(sp)', 'sw s0, 0x20(sp)', 'sw s1, 0x24(sp)', 'sw s2, 0x28(sp)', 'sw s3, 0x2c(sp)',
         'sw s4, 0x30(sp)', 'sw a0, 0x3c(sp)', f'lui s4, {H(NEWS)}', f'addiu s4, s4, {L(NEWS)}', f'lw s3, {MASK}(s4)', 'lui t0, 0x8005', f'lbu t0, {OPT_FLAGS & 0xffff:#x}(t0)', 'nop', f'andi t0, t0, {OPT_BIT}', 'beqz t0, nho', 'nop', 'move s3, zero', 'nho:', 'beqz s3, nh9', 'nop',
         # 100 %: the game was not complete when SNAP was taken (some bit appeared), it is now
         'jal ncomp', 'nop', 'beqz v0, nh0', f'lui t0, {H(CREW_WORD[0])}', f'lw t0, {L(CREW_WORD[0])}(t0)',
         f'lui t1, {CREW_WORD[1] >> 16:#x}', f'ori t1, t1, {CREW_WORD[1] & 0xffff:#x}', 'ori s3, s3, 0x8000', 'bne t0, t1, nhx', 'lui t2, 2',
         'lui t2, 1', 'nhx:', 'or s3, s3, t2',
         # frame counter: starts at FRAMES, MASK = 0 at the end
         'nh0:', f'lw t0, {CNT}(s4)', 'nop', 'bnez t0, nh1', 'nop', f'addiu t0, zero, {FRAMES}',
         'nh1:', 'addiu t0, t0, -1', f'sw t0, {CNT}(s4)', 'bnez t0, nh2', 'nop', f'sw zero, {MASK}(s4)',
         # colour: t1 = 0..15..0 (32 frames), gold (0x80, 0x60, 0x10) to white (0xbc, 0xba, 0xb5)
         'nh2:', 'j ncol', 'nop', 'nh4:',
         # number of lines -> first line y (centred on 120)
         f'lui s1, {H(MS_TABLE[0])}', f'addiu s1, s1, {L(MS_TABLE[0])}', 'move t9, zero',
         'nhc:', 'lw t0, 0(s1)', 'nop', 'beqz t0, nhd', 'and t0, t0, s3', 'sltu t0, zero, t0', 'addu t9, t9, t0', 'j nhc', 'addiu s1, s1, 12',
         'nhd:', 'sw t9, 0x34(sp)', 'sll t0, t9, 3', 'subu t0, t0, t9', 'addiu t1, zero, 123', 'subu t0, t1, t0', 'sw t0, 0x38(sp)',
         'lui t0, 0x8006', f'lw s0, {PRIMS - 0x80060000}(t0)', f'lui s1, {H(MS_TABLE[0])}', f'addiu s1, s1, {L(MS_TABLE[0])}',
         'nhl:', 'lw t0, 0(s1)', 'nop', 'beqz t0, nhe', 'and t0, t0, s3', 'beqz t0, nhn', 'nop',
         'lw a0, 0x3c(sp)', 'move a1, s0', 'lw a2, 8(s1)', 'lw t0, 0x38(sp)', 'sw zero, 0x14(sp)', 'sw t0, 0x10(sp)', 'addiu t0, zero, 1',
         'sw t0, 0x18(sp)', f'jal {TEXTFN}', 'lh a3, 4(s1)',
         'nhk:', 'sltu t0, s0, v0', 'beqz t0, nhm', 'nop', 'lw t0, 4(s0)', 'lui t1, 0xff00', 'and t0, t0, t1', 'or t0, t0, s2', 'sw t0, 4(s0)',
         'j nhk', 'addiu s0, s0, 0x28',
         'nhm:', 'move s0, v0', 'lw t0, 0x38(sp)', 'nop', f'addiu t0, t0, {LINE_H}', 'sw t0, 0x38(sp)',
         'nhn:', 'j nhl', 'addiu s1, s1, 12',
         'nhe:', f'j nbox', 'nop',
         'nh8:', 'nh9:', 'lw a0, 0x3c(sp)', 'lw ra, 0x40(sp)', 'lw s0, 0x20(sp)', 'lw s1, 0x24(sp)', 'lw s2, 0x28(sp)', 'lw s3, 0x2c(sp)',
         'lw s4, 0x30(sp)', f'j {HUB_FN}', 'addiu sp, sp, 0x48']
    # ncomp -> v0 = 1 if the progress page says 100 % (same formula as remix/progress.py)
    C = ['ncomp:', 'lui at, 0x8005', 'lhu v0, 0x7440(at)', 'nop', 'srl v0, v0, 4', 'andi v0, v0, 7', 'xori v0, v0, 7', 'bnez v0, nc0',
          'lhu v0, 0x7442(at)', 'nop', 'andi v0, v0, 7', 'xori v0, v0, 7', 'bnez v0, nc0',
          *[x for o in (0x7448, 0x744A, 0x744C) for x in (f'lhu v0, {o}(at)', 'nop', 'andi v0, v0, 0x3ff', 'xori v0, v0, 0x3ff', 'bnez v0, nc0')],
          'lhu v0, 0x7444(at)', 'nop', 'beqz v0, nc0', 'lhu v0, 0x7446(at)', 'nop', 'beqz v0, nc0',
          'lhu v0, 0x743c(at)', 'nop', 'sltiu v0, v0, 10', 'bnez v0, nc0', 'lhu v0, 0x743e(at)', 'nop', 'sltiu v0, v0, 10', 'bnez v0, nc0', 'nop',
          'jr ra', 'addiu v0, zero, 1', 'nc0:', 'jr ra', 'move v0, zero']
    C += ['ncol:', 'andi t1, t0, 31', 'sltiu t2, t1, 16', 'bnez t2, nh3', 'nop', 'xori t1, t1, 31',
         'nh3:', 'sll t2, t1, 2', 'addiu t3, t2, 0x80', 'sll t5, t1, 1', 'addu t4, t2, t5', 'addiu t4, t4, 0x60', 'sll t6, t1, 3',
         'addu t5, t5, t6', 'addu t5, t5, t1', 'addiu t5, t5, 0x10',
         'sll t4, t4, 8', 'sll t5, t5, 16', 'or s2, t3, t4', 'or s2, s2, t5', 'j nh4', 'nop']
    B = [# dark box: the last letter (TEXT_LAST, right after the text's node) moves to s0, the box takes its place
         'nbox:', 'lw t9, 0x34(sp)', 'nop', 'beqz t9, nbx9', f'lui at, {H(TEXT_LAST)}', f'lw t4, {L(TEXT_LAST)}(at)', 'move t5, zero',
         'nhq:', 'addu t0, t4, t5', 'lw t1, 0(t0)', 'addu t0, s0, t5', 'addiu t5, t5, 4', 'slti t2, t5, 0x28', 'bnez t2, nhq', 'sw t1, 0(t0)',
         'lui t1, 0xff', 'ori t1, t1, 0xffff', 'and t2, s0, t1', 'lui t3, 0x0300', 'or t2, t2, t3', 'sw t2, 0(t4)',
         'lui t0, 0x6040', 'ori t0, t0, 0x1010', 'sw t0, 4(t4)',
         # y = 96 - 7 n (screen; the text routine draws 9 lines above its y), h = 14 n + 4 ; x = BOX_X - 160, w = BOX_W
         'sll t0, t9, 3', 'subu t0, t0, t9', 'addiu t1, zero, -10', 'subu t0, t1, t0', 'sll t0, t0, 16', f'ori t0, t0, {(BOX_X - 160) & 0xffff:#x}',
         'sw t0, 8(t4)', 'sll t0, t9, 4', 'sll t1, t9, 1', 'subu t0, t0, t1', 'addiu t0, t0, 4', 'sll t0, t0, 16', f'ori t0, t0, {BOX_W}', 'sw t0, 0xc(t4)',
         'addiu s0, s0, 0x28', 'nbx9:', 'lui t0, 0x8006', f'sw s0, {PRIMS - 0x80060000}(t0)', 'j nh8', 'nop']
    lab = {k: 0 for k in ('nbox', 'ncomp', 'ncol', 'nh4', 'nh8')}
    for _ in range(2):                                  # the pieces jump to each other: labels resolved in two passes
        c2, l2 = asm(C, MS_CODE2[0], lab); lab.update(l2)
        c3, l3 = asm(B, MS_CODE3[0], lab); lab.update(l3)
        c, l = asm(S, MS_CODE[0], lab); lab.update(l)
    l = lab
    assert c3[-1][0] < MS_CODE3[1], hex(c3[-1][0])
    assert c[-1][0] < MS_CODE[1] and c2[-1][0] < MS_CODE2[1], (hex(c[-1][0]), hex(c2[-1][0]))
    return c + c2 + c3, l


def ops(disc):
    exe = disc.read_file('/SCES_009.92'); ms = disc.read_file('/MAIN_SEL.BIN')
    we = lambda a: struct.unpack_from('<I', exe, a - EXE_BASE)[0]
    wm = lambda a: struct.unpack_from('<I', ms, a - OVL)[0]
    assert we(PRE) == J(3, PRE_FN) and we(POST) == J(3, POST_FN) and wm(HUB) == J(3, HUB_FN)
    assert wm(HUB + 4) == 0x27A40020                    # addiu a0, sp, 0x20
    c, l = exe_code()
    P = [('/SCES_009.92', a, w) for a, w in c] + [('/SCES_009.92', NEWS + i, 0) for i in range(0, 0x20, 4)]
    P += [('/SCES_009.92', PRE, J(3, l['npre'])), ('/SCES_009.92', POST, J(3, l['npost']))]
    mc, ml = ms_code(); tb, st = table(); st += bytes((-len(st)) % 4)
    P += [('/MAIN_SEL.BIN', a, w) for a, w in mc]
    P += [('/MAIN_SEL.BIN', MS_TABLE[0] + i, struct.unpack_from('<I', tb, i)[0]) for i in range(0, len(tb), 4)]
    P += [('/MAIN_SEL.BIN', MS_STR[0] + i, struct.unpack_from('<I', st, i)[0]) for i in range(0, len(st), 4)]
    P += [('/MAIN_SEL.BIN', HUB, J(3, ml['nhub']))]
    out = []
    for f, a, w in P:
        d, base = (exe, EXE_BASE) if f == '/SCES_009.92' else (ms, OVL)
        out.append(['w', f, a - base, struct.unpack_from('<I', d, a - base)[0], w])
    return out
