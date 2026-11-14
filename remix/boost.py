# Trick boost (part of the mod `radar`, v43): in the Boarder Cross of the competition, airs and tricks fill a boost
# meter (an SSX / Speed Freaks style bar under the times, top left); R2 on the ground spends it: the rider goes 50 %
# faster and leaves a trail of his colour. REMIX OPTIONS, RACE: TRICK BOOST (R2) (bit 19 of the options, on by default).
#
# Where: the code (`bmain`, ~1.3 KB) lives in free static RAM (BASE 0x801F3100, the snowtod helper below it, the packed
# TOD A of the Boarder Cross above 0x801F4000); its work words just under B_PTR (VARS).
#   SBC1: the entry's call of func_8001BFD4 (0x8005AEC0, every start of SBC1: the 1st stage always comes before the
#         Boarder Cross, skipq included) goes to `bins` (dead function func_8007E4D8; the image in it and in func_80073F20, func_8005EF1C): the image (MAGIC + code + tables)
#         copied to BASE, VARS zeroed, FlushCache, then func_8001BFD4.
#   SBC2: the race loop's call of the falls function func_8006D0C0 (0x8005F33C, once per game frame, 25/s; s0 = the
#         player's racer) goes to `btr` (end of radar's data function): `bmain` when BASE holds MAGIC, else the
#         function as before. bmain keeps a0..a3 and ends with a jump to func_8006D0C0.
# bmain, each frame (when the player moved: not in the pause):
#   - air (racer + 0x3E != 0): pending + 1, + 2 while a trick motion plays (racer + 0x6C4 != 47, the plain air),
#     + 1 while a trick button is held (L1 L2 R1 triangle circle square); a stumble (+ 0x740) loses it;
#   - landing: LAND frames later, without a stumble, meter += pending (+ BONUS after an air of 15 frames or more);
#   - R2 held on the ground, meter > 0, no stumble: the move of this frame is made 1.5 times (half of it added to the
#     five copies of the position: + 0x2C, 0x84, 0x134, 0x4A74, 0xDC, as the race's own updates write them), meter
#     - COST, the trail shown TRAILF more frames;
#   - a move of more than 4000 (a new race, a retry) clears everything.
# Drawing: the bar (ordering-table entry BAR_ENT: light border, black inside, the meter in the rider's colour, the
# pending part translucent white, quarter ticks; a full bar blinks) and the trail (entry TRAIL_ENT, drawn before the
# HUD): the last NH positions projected with the view (GsWSMATRIX 0x80058E20, translation 0x80058E34: the rider is
# the origin of the world; sx = x * H / z, H = camera + 0xA), a translucent ribbon (half-and-half blending) tapering
# away from the rider, a lighter core, clipped at z = ZMIN (the trail runs between the rider and the camera).
import struct
from asm import asm

OVL = 0x8005AEA8
BASE = 0x801F3100
MAGIC = 0x424F5354                         # 'TSOB'
VARS = 0x801F3F40                          # work words (< 0x801F3FF0: snowtod's B_PTR)
BASE_END = VARS
SBC1_SITE, SBC1_TAIL = 0x8005AEC0, 0x8001BFD4  # jal func_8001BFD4 in SBC1's entry
CAVES = [(0x8007E4D8, 0x8007E4D8 + 0x66C), (0x80073F20, 0x80073F20 + 0x360), (0x8005EF1C, 0x8005EF1C + 0x354), (0x8006FAD8, 0x8006FAD8 + 0x278)]   # dead functions of SBC1
SBC2_SITE, SBC2_TAIL = 0x8005F33C, 0x8006D0C0  # jal func_8006D0C0 (falls) in SBC2's race loop
BTR = 0x8007C700                           # after radar's rfall, in radar's data function (DATA_END 0x8007C81C)
FLUSH = 0x8003CB2C
OPT_FLAGS, BOOST_BIT = 0x80057438, 19
RIDERS, G_RIDER, PAD = 0x8009B9A8, 0x80057408, 0x8004FBF0
WS, PRIMS = 0x80058E20, 0x80058E0C
COP = [0x2C, 0x84, 0x134, 0x4A74, 0xDC]
MAX, COST, BONUS, LAND, TRAILF = 480, 4, 25, 10, 10
NH, ZMIN = 8, 60
TRAIL_ENT, BAR_ENT = 12, 4
BX, BY, BW, BH = -140, -54, 80, 6          # the bar (HUD coordinates: centre of the screen = 0, 0)
TPAGE = 0xE100041C                         # half-and-half blending (as radar's)
# trail colours by g_rider (0x00BBGGRR): Yaggi, Jin, Cindy, Irin, Boss, Gray, Snowman, (other)
COLS = [0x2040FF, 0x40E040, 0xC060FF, 0xFF8040, 0x00C8FF, 0xFF60A0, 0xFFE060, 0x00FFFF]
WTAB = [max(8, 48 - 14 * i) for i in range(NH + 1)]   # half width of the ribbon at history point i (world units)
import math
DIRS = [(round(128 * math.cos(math.radians(a))), round(-128 * math.sin(math.radians(a)))) for a in (-15, 10, 35, 60, 82, 98, 120, 145, 170, 195)]
STREAK_UP = 40                              # the speed lines' centre: that much above the rider's feet
# VARS offsets
LX, METER, PEND, WAIR, LTIM, BFR, HN, FLASH, AIRF, FRM, CA, CB, HIST = 0, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 60, 72
VARS_LEN = HIST + 12 * NH


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)
def J(op, t): return (op << 26) | ((t >> 2) & 0x3ffffff)
def la(r, a): return [f'lui {r}, {H(a)}', f'addiu {r}, {r}, {L(a)}']
def li(r, v):
    v &= 0xffffffff
    if v < 0x8000 or v >= 0xffff8000: return [f'addiu {r}, zero, {v - (1 << 32) if v >= 0x80000000 else v}']
    return [f'lui {r}, {v >> 16:#x}', f'ori {r}, {r}, {v & 0xffff:#x}']
def xy(x, y): return ((y & 0xffff) << 16) | (x & 0xffff)


def main_code(tables):
    V = lambda o: f'{o}(s1)'
    S = ['bmain:', 'addiu sp, sp, -0x70', 'sw ra, 0x10(sp)', 'sw a0, 0x14(sp)', 'sw a1, 0x18(sp)', 'sw a2, 0x1c(sp)', 'sw a3, 0x20(sp)',
         'sw s0, 0x24(sp)', 'sw s1, 0x28(sp)', 'sw s2, 0x2c(sp)', 'sw s3, 0x30(sp)', 'sw s4, 0x34(sp)', 'sw s5, 0x38(sp)',
         'sw s6, 0x3c(sp)', 'sw s7, 0x40(sp)',
         f'lui t0, {H(OPT_FLAGS)}', f'lw t0, {L(OPT_FLAGS)}(t0)', f'lui t1, {(1 << BOOST_BIT) >> 16:#x}', 'and t0, t0, t1', 'bnez t0, bout', 'nop',
         f'lui t0, {H(RIDERS)}', f'lw s0, {L(RIDERS)}(t0)', 'nop', 'beqz s0, bout', 'nop', *la('s1', VARS),
         # this frame's move
         'lw t0, 0x2c(s0)', 'lw t1, 0x30(s0)', 'lw t2, 0x34(s0)', 'lw t3, 0(s1)', 'lw t4, 4(s1)', 'lw t5, 8(s1)',
         'subu s5, t0, t3', 'subu s6, t1, t4', 'subu s7, t2, t5', 'sw t0, 0(s1)', 'sw t1, 4(s1)', 'sw t2, 8(s1)']
    for k, r in enumerate(('s5', 's6', 's7')):
        S += [f'sra t7, {r}, 31', f'xor t6, {r}, t7', 'subu t6, t6, t7', 'slti at, t6, 4000', 'beqz at, breset', 'nop']
    S += ['or t6, s5, s6', 'or t6, t6, s7', 'beqz t6, bdraw', 'nop',
          f'lw t9, {V(FRM)}', 'nop', 'addiu t9, t9, 1', f'sw t9, {V(FRM)}',
          'lbu t0, 0x3e(s0)', 'lh t1, 0x740(s0)', f'lui t2, {H(PAD)}', f'lhu t2, {L(PAD)}(t2)', 'nop',
          'beqz t0, bground', 'nop',
          # in the air
          f'lw t3, {V(PEND)}', 'lh t4, 0x6c4(s0)', 'addiu t3, t3, 1', 'addiu t5, zero, 47', 'beq t4, t5, ba1', 'nop', 'addiu t3, t3, 2',
          'ba1:', 'andi t5, t2, 0xbd', 'beqz t5, ba2', 'nop', 'addiu t3, t3, 1',
          'ba2:', 'beqz t1, ba3', 'nop', 'move t3, zero',
          'ba3:', f'sw t3, {V(PEND)}', 'addiu t4, zero, 1', f'sw t4, {V(WAIR)}', f'sw zero, {V(LTIM)}',
          f'lw t4, {V(AIRF)}', 'nop', 'addiu t4, t4, 1', f'sw t4, {V(AIRF)}', 'j bhist', 'nop',
          # on the ground
          'bground:', f'lw t3, {V(WAIR)}', 'nop', 'beqz t3, bg1', 'nop', f'sw zero, {V(WAIR)}', f'addiu t3, zero, {LAND}', f'sw t3, {V(LTIM)}',
          'bg1:', f'lw t3, {V(LTIM)}', 'nop', 'blez t3, bg3', 'nop', 'beqz t1, bg2', 'nop',
          f'sw zero, {V(PEND)}', f'sw zero, {V(LTIM)}', f'sw zero, {V(AIRF)}', 'j bg3', 'nop',
          'bg2:', 'addiu t3, t3, -1', f'sw t3, {V(LTIM)}', 'bnez t3, bg3', 'nop',
          f'lw t4, {V(METER)}', f'lw t5, {V(PEND)}', f'lw t6, {V(AIRF)}', 'addu t4, t4, t5',
          'slti at, t6, 15', 'bnez at, bg2b', 'nop', f'addiu t4, t4, {BONUS}',
          'bg2b:', f'slti at, t4, {MAX + 1}', 'bnez at, bg2c', 'nop', f'addiu t4, zero, {MAX}',
          'bg2c:', f'sw t4, {V(METER)}', f'sw zero, {V(PEND)}', f'sw zero, {V(AIRF)}', 'beqz t5, bg3', 'nop',
          'addiu t5, zero, 12', f'sw t5, {V(FLASH)}',
          # boost
          'bg3:', 'andi t5, t2, 2', 'beqz t5, bhist', 'nop', 'bnez t1, bhist', 'nop',
          f'lw t4, {V(METER)}', 'nop', 'blez t4, bhist', 'nop', f'addiu t4, t4, -{COST}', 'bgez t4, bb1', 'nop', 'move t4, zero',
          'bb1:', f'sw t4, {V(METER)}', f'addiu t5, zero, {TRAILF + 1}', f'sw t5, {V(BFR)}',
          'sra s5, s5, 1', 'sra s6, s6, 1', 'sra s7, s7, 1']
    for o in COP + [None]:
        b, p = ('s1', 0) if o is None else ('s0', o)
        S += [f'lw t6, {p}({b})', f'lw t7, {p + 4}({b})', f'lw t8, {p + 8}({b})', 'addu t6, t6, s5', 'addu t7, t7, s6', 'addu t8, t8, s7',
              f'sw t6, {p}({b})', f'sw t7, {p + 4}({b})', f'sw t8, {p + 8}({b})']
    # history: shift, the position now at HIST
    S += ['bhist:', *la('t0', VARS + HIST + 12 * (NH - 1)), *la('t1', VARS + HIST),
          'bh1:', 'lw t2, -12(t0)', 'lw t3, -8(t0)', 'lw t4, -4(t0)', 'sw t2, 0(t0)', 'sw t3, 4(t0)', 'sw t4, 8(t0)',
          'addiu t0, t0, -12', 'bne t0, t1, bh1', 'nop',
          'lw t2, 0x2c(s0)', 'lw t3, 0x30(s0)', 'lw t4, 0x34(s0)', f'sw t2, {V(HIST)}', f'sw t3, {V(HIST + 4)}', f'sw t4, {V(HIST + 8)}',
          f'lw t2, {V(HN)}', 'nop', f'slti at, t2, {NH}', 'beqz at, bh2', 'nop', 'addiu t2, t2, 1', f'sw t2, {V(HN)}',
          'bh2:']
    for o in (BFR, FLASH):
        S += [f'lw t2, {V(o)}', 'nop', f'blez t2, bd{o}', 'nop', 'addiu t2, t2, -1', f'sw t2, {V(o)}', f'bd{o}:']
    S += ['j bdraw', 'nop',
          'breset:', *[f'sw zero, {V(o)}' for o in (METER, PEND, WAIR, LTIM, BFR, HN, FLASH, AIRF)],
          'bdraw:', f'lui t0, {H(PRIMS)}', f'lw s2, {L(PRIMS)}(t0)', 'lw t0, 0x14(sp)', 'nop', 'lw s3, 4(t0)',
          f'lw t0, {V(BFR)}', 'nop', 'blez t0, bbar', 'nop', 'jal btrail', 'nop',
          'bbar:', 'jal bbarf', 'nop', f'lui t0, {H(PRIMS)}', f'sw s2, {L(PRIMS)}(t0)',
          'bout:', 'lw a0, 0x14(sp)', 'lw a1, 0x18(sp)', 'lw a2, 0x1c(sp)', 'lw a3, 0x20(sp)', 'lw s0, 0x24(sp)', 'lw s1, 0x28(sp)',
          'lw s2, 0x2c(sp)', 'lw s3, 0x30(sp)', 'lw s4, 0x34(sp)', 'lw s5, 0x38(sp)', 'lw s6, 0x3c(sp)', 'lw s7, 0x40(sp)',
          'lw ra, 0x10(sp)', f'j {SBC2_TAIL}', 'addiu sp, sp, 0x70']
    # btrail: the ribbon from HIST[0] (the rider) back through the history
    S += ['btrail:', 'sw ra, 0x44(sp)', f'lw t0, {V(HN)}', 'nop', 'slti at, t0, 2', 'bnez at, btr9', 'nop',
          f'addiu s4, zero, {TRAIL_ENT}', *la('a0', VARS + HIST), *la('a1', VARS + CA), 'jal bproj', 'nop',
          *la('a1', VARS + CA), 'jal bscr', 'move a2, zero', 'sw t0, 0x68(sp)', f'addiu t1, t1, -{STREAK_UP}', 'sw t1, 0x6c(sp)',
          # colours: main (rider's) and core (half way to white), semi-transparent POLY_F4 (0x2A)
          f'lui t0, {H(G_RIDER)}', f'lh t0, {L(G_RIDER)}(t0)', 'nop', 'andi t0, t0, 7', 'sll t0, t0, 2', *la('t1', tables['cols']),
          'addu t1, t1, t0', 'lw t0, 0(t1)', 'lui t2, 0x2a00', 'or t1, t0, t2', 'sw t1, 0x60(sp)',
          'lui t3, 0x00fe', 'ori t3, t3, 0xfefe', 'and t0, t0, t3', 'srl t0, t0, 1', 'lui t3, 0x2a7f', 'ori t3, t3, 0x7f7f', 'addu t0, t0, t3', 'sw t0, 0x64(sp)',
          'move s5, zero',
          'btl:', 'addiu t0, s5, 1', f'lw t1, {V(HN)}', 'nop', 'slt at, t0, t1', 'beqz at, btr8', 'nop',
          'sll t2, t0, 2', 'sll t3, t0, 3', 'addu t2, t2, t3', *la('a0', VARS + HIST), 'addu a0, a0, t2', *la('a1', VARS + CB),
          'jal bproj', 'nop',
          f'lw t0, {V(CA + 8)}', f'lw t1, {V(CB + 8)}', 'move s6, zero', f'slti at, t0, {ZMIN + 1}', 'bnez at, btr8', 'nop',
          f'slti at, t1, {ZMIN}', 'beqz at, bnc', 'nop',
          f'addiu t2, t0, -{ZMIN}', 'sll t2, t2, 12', 'subu t3, t0, t1', 'div t2, t3', 'mflo t4', 'nop', 'nop']
    for k in (0, 4):
        S += [f'lw t5, {V(CA + k)}', f'lw t6, {V(CB + k)}', 'nop', 'subu t6, t6, t5', 'mult t6, t4', 'mflo t6', 'nop', 'nop',
              'sra t6, t6, 12', 'addu t6, t6, t5', f'sw t6, {V(CB + k)}']
    S += [f'addiu t1, zero, {ZMIN}', f'sw t1, {V(CB + 8)}', 'addiu s6, zero, 1',
          'bnc:', *la('a1', VARS + CA), 'jal bscr', 'move a2, s5', 'sw t0, 0x48(sp)', 'sw t1, 0x4c(sp)', 'sw t4, 0x50(sp)',
          *la('a1', VARS + CB), 'jal bscr', 'addiu a2, s5, 1', 'sw t0, 0x54(sp)', 'sw t1, 0x58(sp)', 'sw t4, 0x5c(sp)',
          'lw a0, 0x64(sp)', 'jal bquad', 'addiu a1, zero, 2', 'lw a0, 0x60(sp)', 'jal bquad', 'move a1, zero',
          f'lw t0, {V(CB)}', f'lw t1, {V(CB + 4)}', f'lw t2, {V(CB + 8)}', f'sw t0, {V(CA)}', f'sw t1, {V(CA + 4)}', f'sw t2, {V(CA + 8)}',
          'bnez s6, btr8', 'addiu s5, s5, 1', f'slti at, s5, {NH - 1}', 'bnez at, btl', 'nop',
          'btr8:', 'jal bstreak', 'nop', 'jal btp', 'nop',
          'btr9:', 'lw ra, 0x44(sp)', 'nop', 'jr ra', 'nop']
    # bstreak: speed lines around the rider (thin semi-transparent POLY_F3 in the core colour), moving outwards
    S += ['bstreak:', 'sw ra, 0x48(sp)', *la('s6', tables['dirs']), 'move s5, zero',
          'bsl:', f'lw t0, {V(FRM)}', 'addiu t2, zero, 23', 'mult t0, t2', 'mflo t3', 'nop', 'nop', 'addiu t2, zero, 37', 'mult s5, t2',
          'mflo t4', 'addu t3, t3, t4', 'andi t3, t3, 127', 'addiu t7, t3, 28', 'andi t8, s5, 1', 'sll t8, t8, 4', 'addu t8, t8, t7',
          'addiu t8, t8, 40', 'lh t5, 0(s6)', 'lh t6, 2(s6)', 'lw t0, 0x68(sp)', 'lw t1, 0x6c(sp)',
          'mult t5, t7', 'mflo t2', 'nop', 'nop', 'sra t2, t2, 7', 'addu t2, t2, t0',            # tip x
          'mult t6, t7', 'mflo t3', 'nop', 'nop', 'sra t3, t3, 7', 'addu t3, t3, t1',            # tip y
          'sll t3, t3, 16', 'andi t2, t2, 0xffff', 'or t2, t2, t3', 'sw t2, 8(s2)',
          'mult t5, t8', 'mflo t2', 'nop', 'nop', 'sra t2, t2, 7', 'addu t2, t2, t0',            # base x
          'mult t6, t8', 'mflo t3', 'nop', 'nop', 'sra t3, t3, 7', 'addu t3, t3, t1',            # base y
          'sra t4, t6, 5', 'sra t7, t5, 5',                                                       # half width (2 px) across
          'subu t0, t2, t4', 'addu t1, t3, t7', 'sll t1, t1, 16', 'andi t0, t0, 0xffff', 'or t0, t0, t1', 'sw t0, 12(s2)',
          'addu t0, t2, t4', 'subu t1, t3, t7', 'sll t1, t1, 16', 'andi t0, t0, 0xffff', 'or t0, t0, t1', 'sw t0, 16(s2)',
          'lui t0, 0x400', 'sw t0, 0(s2)', 'lw t0, 0x64(sp)', 'lui t1, 0x00ff', 'ori t1, t1, 0xffff', 'and t0, t0, t1', 'lui t1, 0x2200',
          'or t0, t0, t1', 'sw t0, 4(s2)', 'move a0, s2', 'jal badd', 'addiu s2, s2, 20',
          'addiu s6, s6, 4', 'addiu s5, s5, 1', f'slti at, s5, {len(DIRS)}', 'bnez at, bsl', 'nop',
          'lw ra, 0x48(sp)', 'nop', 'jr ra', 'nop']
    # bproj: a0 = history point, a1 = out: (R (p - HIST[0]) >> 12) + T
    S += ['bproj:', 'lw t0, 0(a0)', 'lw t1, 4(a0)', 'lw t2, 8(a0)', f'lw t3, {V(HIST)}', f'lw t4, {V(HIST + 4)}', f'lw t5, {V(HIST + 8)}',
          'subu t0, t0, t3', 'subu t1, t1, t4', 'subu t2, t2, t5', *la('t9', WS)]
    for r in range(3):
        S += [f'lh t3, {6 * r}(t9)', f'lh t4, {6 * r + 2}(t9)', f'lh t5, {6 * r + 4}(t9)', 'nop',
              'mult t3, t0', 'mflo t6', 'nop', 'nop', 'mult t4, t1', 'mflo t7', 'nop', 'nop', 'mult t5, t2', 'mflo t8',
              'addu t6, t6, t7', 'addu t6, t6, t8', 'sra t6, t6, 12', f'lw t3, {0x14 + 4 * r}(t9)', 'nop', 'addu t6, t6, t3',
              f'sw t6, {4 * r}(a1)']
    S += ['jr ra', 'nop']
    # bscr: a1 = camera point, a2 = history index -> t0 = sx, t1 = sy, t4 = half width (clamped)
    S += ['bscr:', 'lw t0, 0(a1)', 'lw t1, 4(a1)', 'lw t2, 8(a1)', 'lw t3, 0x6d8(s0)', 'nop', 'lh t3, 0xa(t3)', 'nop',
          'mult t0, t3', 'mflo t0', 'nop', 'nop', 'div t0, t2', 'mflo t0', 'nop', 'nop',
          'mult t1, t3', 'mflo t1', 'nop', 'nop', 'div t1, t2', 'mflo t1', 'nop', 'nop',
          *la('t4', tables['wtab']), 'sll t5, a2, 2', 'addu t4, t4, t5', 'lw t4, 0(t4)', 'nop',
          'mult t4, t3', 'mflo t4', 'nop', 'nop', 'div t4, t2', 'mflo t4']
    for r, m in (('t0', 900), ('t1', 480), ('t4', 200)):
        S += [f'slti at, {r}, {m}', f'bnez at, bc{r}a', 'nop', f'addiu {r}, zero, {m}', f'bc{r}a:',
              f'slti at, {r}, -{m}', f'beqz at, bc{r}b', 'nop', f'addiu {r}, zero, -{m}', f'bc{r}b:']
    S += ['jr ra', 'nop']
    # bquad: a0 = code + colour, a1 = width shift; A at 0x48.., B at 0x54..
    S += ['bquad:', 'move t9, ra', 'lw t0, 0x48(sp)', 'lw t1, 0x4c(sp)', 'lw t2, 0x50(sp)', 'lw t3, 0x54(sp)', 'lw t4, 0x58(sp)', 'lw t5, 0x5c(sp)',
          'srav t2, t2, a1', 'srav t5, t5, a1', 'lui t6, 0x500', 'sw t6, 0(s2)', 'sw a0, 4(s2)', 'sll t1, t1, 16', 'sll t4, t4, 16']
    for k, (x, s, w, y) in enumerate((('t0', 'subu', 't2', 't1'), ('t0', 'addu', 't2', 't1'), ('t3', 'subu', 't5', 't4'), ('t3', 'addu', 't5', 't4'))):
        S += [f'{s} t6, {x}, {w}', 'andi t6, t6, 0xffff', f'or t6, t6, {y}', f'sw t6, {8 + 4 * k}(s2)']
    S += ['move a0, s2', 'jal badd', 'addiu s2, s2, 24', 'jr t9', 'nop']
    # btp: DR_TPAGE (half-and-half) linked last in entry s4: drawn first
    S += ['btp:', 'move t9, ra', 'lui t4, 0x100', 'sw t4, 0(s2)', *li('t4', TPAGE), 'sw t4, 4(s2)', 'move a0, s2', 'jal badd',
          'addiu s2, s2, 8', 'jr t9', 'nop']
    # btile: TILE a3 (code + colour) at a1 (y << 16 | x), size a2 (h << 16 | w)
    S += ['btile:', 'move t9, ra', 'lui t4, 0x300', 'sw t4, 0(s2)', 'sw a3, 4(s2)', 'sw a1, 8(s2)', 'sw a2, 12(s2)', 'move a0, s2',
          'jal badd', 'addiu s2, s2, 16', 'jr t9', 'nop']
    # badd: link a0 into entry s4 of the ordering table s3
    S += ['badd:', 'sll t0, s4, 2', 'addu t0, s3, t0', 'lw t1, 0(t0)', 'lui t2, 0xff', 'ori t2, t2, 0xffff', 'lw t3, 0(a0)',
          'and t4, t1, t2', 'lui t5, 0xff00', 'and t3, t3, t5', 'or t3, t3, t4', 'sw t3, 0(a0)', 'and t1, t1, t5', 'and t4, a0, t2',
          'or t1, t1, t4', 'jr ra', 'sw t1, 0(t0)']
    # bbarf: the bar (linked last = drawn first: border, inside, meter, pending, ticks)
    S += ['bbarf:', 'sw ra, 0x44(sp)', f'addiu s4, zero, {BAR_ENT}']
    for k in (1, 2, 3):
        S += [*li('a1', xy(BX + BW * k // 4, BY)), *li('a2', xy(1, BH)), *li('a3', 0x60404040), 'jal btile', 'nop']
    S += [f'lw t0, {V(METER)}', f'lw t1, {V(PEND)}', f'addiu t2, zero, {MAX // BW}', 'divu t0, t2', 'mflo s5', 'nop', 'nop',
          'divu t1, t2', 'mflo s6', f'addiu t3, zero, {BW}', 'subu t3, t3, s5', 'slt at, t3, s6', 'beqz at, bp1', 'nop', 'move s6, t3',
          'bp1:', 'blez s6, bp2', 'nop', f'addiu a1, s5, {BX}', 'andi a1, a1, 0xffff', f'lui t0, {BY & 0xffff:#x}', 'or a1, a1, t0',
          f'lui a2, {BH}', 'or a2, a2, s6', *li('a3', 0x62FFFFFF), 'jal btile', 'nop',
          'bp2:', 'blez s5, bp5', 'nop',
          f'lui t0, {H(G_RIDER)}', f'lh t0, {L(G_RIDER)}(t0)', 'nop', 'andi t0, t0, 7', 'sll t0, t0, 2', *la('t1', tables['cols']),
          'addu t1, t1, t0', 'lw a3, 0(t1)', f'lw t0, {V(FRM)}', f'lw t1, {V(FLASH)}', 'andi t2, t0, 2', 'andi t1, t1, 2', 'bnez t1, bp3', 'nop',
          f'lw t1, {V(METER)}', f'addiu t3, zero, {MAX}', 'bne t1, t3, bp4', 'nop', 'beqz t2, bp4', 'nop',
          'bp3:', *li('a3', 0xFFFFFF),
          'bp4:', 'lui t0, 0x6000', 'or a3, a3, t0', *li('a1', xy(BX, BY)), f'lui a2, {BH}', 'or a2, a2, s5', 'jal btile', 'nop',
          'bp5:', *li('a1', xy(BX - 1, BY - 1)), *li('a2', xy(BW + 2, BH + 2)), *li('a3', 0x60000000), 'jal btile', 'nop',
          *li('a1', xy(BX - 2, BY - 2)), *li('a2', xy(BW + 4, BH + 4)), *li('a3', 0x60C0C0C0), 'jal btile', 'nop',
          'jal btp', 'nop', 'lw ra, 0x44(sp)', 'nop', 'jr ra', 'nop']
    return S


def image():
    """the words copied to BASE: MAGIC, the code, the tables"""
    def build(tables):
        c, l = asm(main_code(tables), BASE + 4)
        return c, l
    c, l = build({'cols': 0, 'wtab': 0, 'dirs': 0})
    t0 = c[-1][0] + 4
    tables = {'cols': t0, 'wtab': t0 + 4 * len(COLS), 'dirs': t0 + 4 * len(COLS) + 4 * len(WTAB)}
    c, l = build(tables)
    words = [MAGIC] + [w for _, w in c] + COLS + WTAB + [(dx & 0xffff) | ((dy & 0xffff) << 16) for dx, dy in DIRS]
    assert BASE + 4 * len(words) <= BASE_END and VARS + VARS_LEN <= 0x801F3FF0
    return words, l


def sbc1_code(img):
    """`bins`: copies the image to BASE (in pieces: CAVES), clears VARS, FlushCache, then the call it replaces"""
    def S(chunks):
        out = ['bins:', 'addiu sp, sp, -0x20', 'sw ra, 0x10(sp)', 'sw a0, 0x14(sp)', 'sw a1, 0x18(sp)', 'sw a2, 0x1c(sp)', *la('t1', BASE)]
        for k, (src, n) in enumerate(chunks):
            out += [*la('t0', src), *la('t2', src + 4 * n), f'bi{k}:', 'lw t3, 0(t0)', 'addiu t0, t0, 4', 'sw t3, 0(t1)',
                    f'bne t0, t2, bi{k}', 'addiu t1, t1, 4']
        out += [*la('t1', VARS), *la('t2', VARS + VARS_LEN), 'biz:', 'sw zero, 0(t1)', 'addiu t1, t1, 4', 'bne t1, t2, biz', 'nop',
                f'jal {FLUSH}', 'nop', 'lw ra, 0x10(sp)', 'lw a0, 0x14(sp)', 'lw a1, 0x18(sp)', 'lw a2, 0x1c(sp)',
                f'j {SBC1_TAIL}', 'addiu sp, sp, 0x20']
        return out
    c0, _ = asm(S([(c, 1) for c, _ in CAVES]), CAVES[0][0])
    first = c0[-1][0] + 4
    room = [(first, CAVES[0][1])] + CAVES[1:]
    chunks, rest = [], list(img)
    for a, e in room:
        n = min(len(rest), (e - a) // 4)
        chunks.append((a, n)); rest = rest[n:]
    assert not rest, len(rest)
    chunks = [(a, n) for a, n in chunks if n]
    c, l = asm(S(chunks), CAVES[0][0])
    assert c[-1][0] + 4 == first or len(chunks) < len(CAVES)
    k = 0
    for a, n in chunks:
        c += [(a + 4 * i, w) for i, w in enumerate(img[k:k + n])]; k += n
    return c, l


def sbc2_code(bmain):
    S = ['btr:', f'lui t0, {H(BASE)}', f'lw t0, {L(BASE)}(t0)', *li('t1', MAGIC), 'bne t0, t1, bt9', 'nop', f'j {bmain}', 'nop',
         'bt9:', f'j {SBC2_TAIL}', 'nop']
    return asm(S, BTR)


def ops(disc):
    s1 = disc.read_file('/SBC1.BIN'); s2 = disc.read_file('/SBC2.BIN')
    w1 = lambda a: struct.unpack_from('<I', s1, a - OVL)[0]
    w2 = lambda a: struct.unpack_from('<I', s2, a - OVL)[0]
    assert w1(SBC1_SITE) == J(3, SBC1_TAIL) and w1(CAVES[0][0]) == 0x27BDFFA8, hex(w1(CAVES[0][0]))
    assert w2(SBC2_SITE) == J(3, SBC2_TAIL)
    img, l = image()
    c1, l1 = sbc1_code(img)
    c2, l2 = sbc2_code(l['bmain'])
    assert c2[-1][0] < 0x8007C81C
    out = [['w', '/SBC1.BIN', a - OVL, w1(a), x] for a, x in c1 + [(SBC1_SITE, J(3, l1['bins']))]]
    out += [['w', '/SBC2.BIN', a - OVL, w2(a), x] for a, x in c2 + [(SBC2_SITE, J(3, l2['btr']))]]
    return out


if __name__ == '__main__':
    img, l = image(); c1, _ = sbc1_code(img)
    print('image', len(img) * 4, 'bytes; last word', hex(c1[-1][0]), 'labels', {k: hex(v) for k, v in l.items() if k in ('bmain', 'btrail', 'bbarf')})
