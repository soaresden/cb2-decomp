# Boss's black outfit (part of the mod `crew`, v57).
#
# The CPU Boss of the Competition wears a black "skeleton" suit; the player's Boss had only the tattooed one. The
# black suit is already on the disc as a player texture: FR/FBD3/BOSS1.FBD (file 0xD9), which the game only used for
# player 2 when both players take Boss in VS (texture = 0xD8 + player).
#   WEAR screen: Boss gets it (MAIN_SEL asks for "rider < 4" in three places: 5 now), with one row only, like the
#     game's own "ensemble" outfits: the label in the middle (0x80061DE8 -> ensd), up / down do nothing (ensu),
#     left / right switch the outfit 0 / 1 in the jacket and pants cursors (ensr), validated as g_jacket.
#   preview: func_800640AC (the WEAR screen's texture upload, tables for riders 0..3 only) is skipped for Boss
#     (ensp): the outfit is kept in BOUT and the model rebuilt by crew's `mdl`, which takes menu model 4 (crew.py:
#     Boss's ending model ED_CHR71 with its black texture from ENDING.FBD, put in Boss's VRAM column x 640, y 256 and
#     palette row 484) when bossk says so. bossk is also what loads that model ahead (when Boss is on the BOARDER
#     screen and the model isn't in MENU_BUF yet, it asks for it: the menu shows the usual model meanwhile).
#   races: the texture load of the player's rider (crew's ld24 / ld20 hooks) goes through btx: Boss's file
#     0xD8 / 0xD9 is xored with the player's outfit (player 2 in VS keeps the other one when both take Boss).
# Code placed with crew's routines (crew.place), in the dead functions of the exe.
import struct
from asm import asm

EXE_BASE = 0x8000F800; OVL = 0x8005AEA8
BOUT = 0x8001FCA8                         # the outfit on the WEAR screen (last word of crew's data function)
B314 = 0x8007B314                         # WEAR cursors: jacket (B314), pants (B316), 4 bytes per player
RIDER_LT4 = [0x80060508, 0x800616F4, 0x80062310]    # slti v0, v0, 4 (WEAR screen for riders 0..3)
SLTI4, SLTI5 = 0x28420004, 0x28420005
DRAW = 0x80061DE8                         # lui v0, 0x8005 / lh v0, 0x742A(v0) (ensemble label?)
UPDN = 0x80062198                         # lh v0, 0(s5) (up / down)
LR = [0x80061FFC, 0x800620CC]             # lh v0, 0(s5) (right, left)
LHS5 = 0x86A20000
# Cindy's ending outfit (v58): off since v59 (the race model looked bad: thin, dark streaks on the legs); the code stays
CG_ON = False
CG_MODES = (1 << 2) | (1 << 5) | (1 << 7) | (1 << 8) if CG_ON else 0   # modes with it (one player)
PREV = 0x800640AC                         # func_800640AC: addiu sp, sp, -0x1830 / sw s4, 0x1828(sp)
TEX_SITES = {0x8001D55C: (4, 's4', 'ld24'), 0x8001D644: (0xE, 's4', 'ld24'), 0x8001D938: (4, 's2', 'ld20')}   # (jacket offset, menu struct)
TOP = {'bossk', 'ensd', 'ensu', 'ensr', 'ensp', 'btc_ld24', 'btc_ld20'} | {f'bt{a:x}' for a in TEX_SITES}


def H(a): return ((a + 0x8000) >> 16) & 0xffff
def L(a): return a - (((a + 0x8000) >> 16) << 16)


def routines(mm, magic, menu_save, shown):
    """asm lines placed with crew's routines (crew's labels aval, mdl, ld24, ld20 by name); mm: the menu model's
    magic word (model k in MENU_BUF: magic + k), menu_save: crew's MENU_SAVE (shown + k: model k's texture in VRAM)"""
    # bossk(a0 = rider, a1 = alias cursor): crew's aval, or a menu model of an outfit (s0 = a0): 4 for Boss in black
    # (BOUT 1), 5 for Cindy's ending outfit (BOUT 6, v58). Not in MENU_BUF yet: that model all the same (crew's mdl asks
    # for it and shows the usual one meanwhile), so it is there when the outfit is chosen
    S = ['bossk:', 'move t7, ra', 'jal aval', 'nop', 'move ra, t7',
         'bnez v0, bk9', 'addiu t0, zero, 4', 'addiu t3, zero, 1', 'beq s0, t0, bk1', 'addiu t4, zero, 2',
         'bne s0, t4, bk9' if CG_ON else 'b bk9', 'move v0, zero', 'addiu t0, zero, 5', 'addiu t3, zero, 6',
         'bk1:', f'lui at, {H(mm)}', f'lw t1, {L(mm)}(at)', f'lui t2, {H(magic)}', f'addiu t2, t2, {L(magic)}', 'addu t2, t2, t0',
         'bne t1, t2, bk9', 'move v0, t0',
         f'lui at, {H(BOUT)}', f'lw t1, {L(BOUT)}(at)', 'nop', 'beq t1, t3, bk9', 'nop', 'move v0, zero',
         'bk9:', 'jr ra', 'nop',
         # ensd / ensu: Boss (rider 4 at s3) -> the ensemble path, else the replaced load
         'ensd:', 'lhu t0, 0(s3)', 'addiu t1, zero, 4', 'bne t0, t1, ed1', 'lui at, 0x8006', 'addiu ra, at, 0x1E20',
         'ed1:', 'lui v0, 0x8005', 'jr ra', 'lh v0, 0x742A(v0)',
         'ensu:', 'lhu t0, 0(s3)', 'addiu t1, zero, 4', 'bne t0, t1, eu1', 'lui at, 0x8006', 'addiu ra, at, 0x1D14',
         'eu1:', 'jr ra', 'lh v0, 0(s5)',
         # ensr (right: ra 0x80062004, left: 0x800620D4): Boss switches 0 / 1 (jacket = pants); Cindy's jacket row
         # (s4 = 0) goes over 0..6 (3..5: her hidden outfits, mod outfits; 6: her ending outfit), then the preview
         'ensr:', 'lhu t0, 0(s3)', 'addiu t1, zero, 4', 'bne t0, t1, erc', f'lui at, {H(B314)}', 'addu at, at, s0',
         f'lhu t0, {L(B314)}(at)', 'nop', 'andi t0, t0, 1', 'xori t0, t0, 1', f'sh t0, {L(B314)}(at)', 'j erp', f'sh t0, {L(B314 + 2)}(at)',
         'erc:', 'addiu t1, zero, 2', 'bne t0, t1, er1', 'nop', 'bnez s4, er1', 'addu at, at, s0',
         # outfit 6 only where the race loads it (crew's ldg: Free Style, Big Air, Halfpipe, Board Park): t4 = 7 or 6 outfits
         'lui t3, 0x8005', 'lw t3, 0x7420(t3)', f'addiu t4, zero, {CG_MODES:#x}', 'srlv t4, t4, t3', 'andi t4, t4, 1', 'addiu t4, t4, 6',
         f'lh t0, {L(B314)}(at)', 'lui t2, 0x8006', 'addiu t2, t2, 0x2004', 'beq ra, t2, err', 'addiu t0, t0, 1',
         'addiu t0, t0, -2', 'bgez t0, ers', 'nop', 'j ers', 'addiu t0, t4, -1',
         'err:', 'slt t1, t0, t4', 'bnez t1, ers', 'nop', 'move t0, zero',
         'ers:', f'sh t0, {L(B314)}(at)',
         'erp:', 'lui at, 0x8006', 'addiu ra, at, 0x2184',
         'er1:', 'jr ra', 'lh v0, 0(s5)',
         # ensp: func_800640AC's entry (a0 = cursors, a1 = rider). Boss: outfit -> BOUT, model rebuilt (crew's mdl).
         # Cindy: outfit 6 -> the same; any other while that model is shown: back to her own model first
         'ensp:', 'sll t0, a1, 16', 'sra t0, t0, 16', 'addiu t1, zero, 4', 'beq t0, t1, ep4', 'addiu t1, zero, 2',
         'beq t0, t1, ep2', 'nop',
         'epn:', 'addiu sp, sp, -0x1830', f'j {PREV + 8:#x}', 'sw s4, 0x1828(sp)',
         'ep4:', 'lh t0, 0(a0)', f'lui at, {H(BOUT)}', f'sw t0, {L(BOUT)}(at)', 'j mdl', 'addiu a0, zero, 4',
         'ep2:', 'lh t0, 0(a0)', f'lui at, {H(BOUT)}', f'sw t0, {L(BOUT)}(at)', 'addiu t2, zero, 6', 'bne t0, t2, ep2n', 'nop',
         'j mdl', 'addiu a0, zero, 2',
         'ep2n:', f'lui at, {H(menu_save)}', f'lw t0, {L(menu_save)}(at)', f'lui t2, {H(shown + 5)}', f'addiu t2, t2, {L(shown + 5)}',
         'bne t0, t2, epn', 'nop',
         'addiu sp, sp, -16', 'sw ra, 0(sp)', 'sw a0, 4(sp)', 'sw a1, 8(sp)', 'jal mdl', 'addiu a0, zero, 2',
         'lw ra, 0(sp)', 'lw a0, 4(sp)', 'lw a1, 8(sp)', 'j epn', 'addiu sp, sp, 16']
    # btx: Boss's race texture (file 0xD8 / 0xD9) xored with the player's outfit, then crew's loader
    for site, (o, reg, ld) in TEX_SITES.items():
        S += [f'bt{site:x}:', f'lh t9, {o}({reg})', f'j btc_{ld}', 'addiu t8, a0, -0xD8']
    for ld in ('ld24', 'ld20'):
        S += [f'btc_{ld}:', 'sltiu t8, t8, 2', f'beqz t8, bc_{ld}', 'andi t9, t9, 1', 'xor a0, a0, t9', f'bc_{ld}:', f'j {ld}', 'nop']
    return S


def ops(disc, lb):
    """hooks (lb: crew's placed labels, these routines included)"""
    ex = disc.read_file('/SCES_009.92'); ms = disc.read_file('/MAIN_SEL.BIN')
    we = lambda a: struct.unpack_from('<I', ex, a - EXE_BASE)[0]
    wm = lambda a: struct.unpack_from('<I', ms, a - OVL)[0]
    J = lambda op, t: (op << 26) | ((t >> 2) & 0x3ffffff)
    out = []
    m = lambda a, new: out.append(['w', '/MAIN_SEL.BIN', a - OVL, wm(a), new])
    for a in RIDER_LT4: assert wm(a) == SLTI4, hex(a); m(a, SLTI5)
    assert wm(DRAW) == 0x3C028005 and wm(DRAW + 4) == 0x8442742A
    m(DRAW, J(3, lb['ensd'])); m(DRAW + 4, 0)
    assert wm(UPDN) == LHS5 and wm(UPDN + 4) == 0; m(UPDN, J(3, lb['ensu']))
    for a in LR: assert wm(a) == LHS5 and wm(a + 4) == 0, hex(a); m(a, J(3, lb['ensr']))
    assert wm(PREV) == 0x27BDE7D0 and wm(PREV + 4) == 0xAFB41828
    m(PREV, J(2, lb['ensp'])); m(PREV + 4, 0)
    for site in TEX_SITES:
        out.append(['w', '/SCES_009.92', site - EXE_BASE, we(site), J(3, lb[f'bt{site:x}'])])
    out.append(['w', '/SCES_009.92', BOUT - EXE_BASE, we(BOUT), 0])
    return out


def sites():
    """the hooks (for the in-game switch of crew)"""
    return ([('/MAIN_SEL.BIN', a) for a in RIDER_LT4 + [DRAW, DRAW + 4, UPDN] + LR + [PREV, PREV + 4]])


def merge(disc, crew_ops, lb):
    new = ops(disc, lb); keys = {(op[1], op[2]) for op in new}
    return [op for op in crew_ops if not (op[0] == 'w' and (op[1], op[2]) in keys)] + new


# Competition (mod riders, remix.py `tex` at CAVE_TEX, called at 0x8001CEFC): the player's texture file is 180 + 9 rider
# + 3 jacket + pants; riders 4..6 (Boss, Gray, Snowman) have 2 files each from 0xD8 on. Now those three take
# 0xD0 + 2 rider + (3 jacket + pants) / 4 & 1, i.e. Boss's outfit (jacket = pants = outfit); before, a jacket / pants
# left from an earlier rider gave them another file (Boss after Yaggi in jacket 2, pants 2 took SNOW0). tex's 8 words
# + its end in 2 free words after the next routine (the exe's zeros 0x8004F800..0x8004FC08 are the mods' caves; the
# game clears 0x800505B8.. at boot).
CAVE_TEX, TEX_END = 0x8004F800, 0x8004F838


def tex_ops(disc):
    ex = disc.read_file('/SCES_009.92'); we = lambda a: struct.unpack_from('<I', ex, a - EXE_BASE)[0]
    c, lb = asm(['tex:', 'slti at, s4, 4', 'bnez at, td', 'srl t5, t1, 2', 'andi t5, t5, 1', 'sll t4, s4, 1', 'addu v1, t4, t5',
                 'j td', 'addiu v1, v1, 0xD0'], CAVE_TEX, {'td': TEX_END})
    c2, _ = asm(['jr ra', 'sw v1, 0xc0(sp)'], TEX_END)
    assert c[-1][0] < CAVE_TEX + 0x20 and all(we(a) == 0 for a, _ in c + c2)
    return [['w', '/SCES_009.92', a - EXE_BASE, 0, w] for a, w in c + c2] + [
        ['w', '/SCES_009.92', TEX_CALL - EXE_BASE, we(TEX_CALL), (3 << 26) | ((CAVE_TEX >> 2) & 0x3ffffff)]]


TEX_CALL = 0x8001CEFC


def tex_merge(disc, riders_ops):
    new = tex_ops(disc); keys = {(op[1], op[2]) for op in new}
    stale = lambda op: op[1] == '/SCES_009.92' and 0x80050780 <= op[2] + EXE_BASE < 0x800507C0   # a first try (v57 work)
    return [op for op in riders_ops if not (op[0] == 'w' and ((op[1], op[2]) in keys or stale(op)))] + new
