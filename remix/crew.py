# Jicchi, Nick and Kelly as player riders (mod `crew`, v26): portraits, names, game code and new files.
#
# The three CPU-only riders of the Tour Competition get a place on the BOARDER screen. Their portrait comes from
# their profile card in the competition movie of the player's own disc (MOVIE/SBCMOVE.STR, decoded by the patcher: modular.face_op):
# cropped, background removed, scaled to 64x64 (drawn 64x80 like the others) and reduced to 95 colours + transparent.
# It goes into the menu texture file TITLE/MAIN_SEL.FBD, in an area that no menu screen uses (VRAM x 832..1023,
# y 320..383): faces at x 832 / 864 / 896 (8-bit), their palettes on rows 320..322 at x 928 (96 entries), and the
# name tags (drawn here, 48x32, 4-bit, palette of the game's own name tags at 768,464) at x 960 / 972 / 984, y 352.
# The portraits are integer arithmetic: the site (disc.js) computes exactly the same bytes.
import os, struct

NAMES = ['JICCHI', 'NICK', 'KELLY']
# STR frame (1-based), crop x, y, w, h in the 320x240 frame, background: 1 = white, 0 = black (order of NAMES)
CARDS = [[318, 181, 96, 106, 130, 1], [344, 177, 96, 106, 130, 0], [330, 25, 19, 106, 132, 1]]
FACE_X, FACE_Y, CLUT_X, CLUT_Y, NCOL = 832, 320, 928, 320, 96
NAME_X, NAME_Y = 960, 352
FBD = '/TITLE/MAIN_SEL.FBD'; FBD_X, FBD_W, FBD_HDR = 320, 704, 20
STR = '/MOVIE/SBCMOVE.STR'


def vram_off(x, y): return FBD_HDR + (y * FBD_W + (x - FBD_X)) * 2


def face_op():
    """the package operation that draws the portraits (computed by the patcher from the player's disc: modular.face_op)"""
    return ['face', FBD, STR, {'cards': CARDS, 'face': [FACE_X, FACE_Y], 'clut': [CLUT_X, CLUT_Y], 'n': NCOL}]


def write_faces(fbd, str_data):
    import modular
    out = bytearray(fbd); modular.face_op(out, lambda k: str_data[k * 2048:(k + 1) * 2048], len(str_data) // 2048, face_op()); return bytes(out)


# ---- name tags (drawn here: not game data)
def name_tags(font=None):
    """three 48x32 4-bit tags (index 0 white .. 14 light grey, 15 transparent), as 32 rows of 24 bytes each"""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    font = font or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'NotoSans-BlackItalic.ttf')
    out = []
    for name in NAMES:
        S = 4; W, H = 48 * S, 32 * S
        size = {6: 15, 4: 19, 5: 17}[len(name)] * S
        f = ImageFont.truetype(font, size)
        txt = Image.new('L', (W * 2, H * 2), 0); d = ImageDraw.Draw(txt)
        bb = d.textbbox((0, 0), name, font=f); tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.text(((W * 2 - tw) // 2 - bb[0], (H * 2 - th) // 2 - bb[1]), name, font=f, fill=255)
        txt = txt.rotate(14, resample=Image.BICUBIC).crop((W // 2, H // 2, W // 2 + W, H // 2 + H))
        outline = txt.filter(ImageFilter.MaxFilter(2 * S + 1))
        a = txt.resize((48, 32), Image.LANCZOS).load(); o = outline.resize((48, 32), Image.LANCZOS).load()
        rows = []
        for y in range(32):
            row = []
            for x in range(48):
                if a[x, y] >= 110: row.append(0)                       # white
                elif o[x, y] >= 90: row.append(1 + min(13, a[x, y] // 9))   # dark rim, lighter towards the letter
                else: row.append(15)
            rows.append(bytes(row[i] | row[i + 1] << 4 for i in range(0, 48, 2)))
        out.append(rows)
    return out


def write_names(fbd, tags):
    out = bytearray(fbd)
    for k, rows in enumerate(tags):
        for y in range(32):
            o = vram_off(NAME_X + 12 * k, NAME_Y + y); out[o:o + 24] = rows[y]
    return bytes(out)


# ---------------------------------------------------------------------------------------------------- game code
# The three riders are "aliases": the game keeps a normal rider number (BASE: Jicchi -> Yaggi, Nick -> Jin,
# Kelly -> Cindy, for animations, voices and everything else) and the alias number (ALIAS, 1..3) says that the
# player's rider is in fact Jicchi / Nick / Kelly. Only in the modes whose rider files come through func_8001D1B8
# (MODES).
#   BOARDER screen: the rider list (func_80063E7C) gets JICCHI NICK KELLY after IRIN; its cursor alias is ACUR,
#     copied from ALIAS when the screen opens (cinit) and back when the selection is validated (ccom).
#   portrait / name (func_80063324 / func_800637A4): drawn as usual, then the primitive is pointed at the new
#     pictures (fw / nw); stat bars (D_8007B328 rows): STATS.
#   race: the player's model and texture files (func_8001D1B8 -> func_80013BD0) become the new files (ld); the
#     player's parameters (initRacers, row of the overlay's table) become PARAMS (the CPU rider's own, from SBC2).
# The new files are entries of a file table in the exe (ENT, MSF + size): their index is (ENT - g_fileTable) / 8.
from asm import asm

EXE_BASE = 0x8000F800; OVL = 0x8005AEA8; G_FILES = 0x800583E8
# dead functions of the exe (never called, no pointer to them anywhere); 0x8001E630..0x8001E7C4: mod news
CAVES = [(0x80013940, 0x80013A34), (0x800169B4, 0x80016AB0), (0x800238E0, 0x80023998),
         (0x80029AE0, 0x80029B7C), (0x80021DA0, 0x80021E38), (0x80022B70, 0x80022C08), (0x80021BB0, 0x80021C38),
         (0x8001FA0C, 0x8001FA98),   # (0x800280B8, 0x8002E7D0: mod rear)
         (0x800404E4, 0x80040640), (0x8001B69C, 0x8001B718),
         (0x8002DE10, 0x8002DE88), (0x8002E96C, 0x8002EA10), (0x80027E9C, 0x80027F04), (0x8002C49C, 0x8002C504),
         (0x800290C8, 0x80029128), (0x8003F028, 0x8003F088), (0x800439C4, 0x80043A24),
         (0x80017BF8, 0x80017C9C), (0x8002043C, 0x8002050C), (0x80021A88, 0x80021B28), (0x800312C4, 0x80031374), (0x80028078, 0x800280B8),
         (0x8001829C, 0x80018320), (0x80031180, 0x8003120C),   # v54: given by remix/options.py (unused there)
         # v26 (2 players): small unreferenced functions, checked against every jump, branch and pointer of every file
         # (0x80031180, 0x8003BD98, 0x80040AA4, 0x8001829C, 0x8003EAC4, 0x800123C8: mod options)
         (0x80013BA0, 0x80013BD0), (0x80020288, 0x800202C4), (0x80020394, 0x800203BC), (0x80028D78, 0x80028DB4), (0x80028E18, 0x80028E40),
         (0x80029194, 0x800291CC), (0x8002A62C, 0x8002A694), (0x8002A798, 0x8002A7C4), (0x8002E6A4, 0x8002E6D0), (0x8002E79C, 0x8002E7D0),
         (0x80031230, 0x80031280), (0x8003C0A4, 0x8003C108), (0x8003C138, 0x8003C168),
         (0x8003EFEC, 0x8003F028), (0x800435B4, 0x80043604)]
DATA2 = 0x8003EE98; DATA2_END = 0x8003EF00             # menu models: file entries, rectangles, state
ENT2, IDX2, RCOL, RCLUT, PENDING, DUMMY = (DATA2 + o for o in (0, 0x18, 0x20, 0x38, 0x50, 0x54))
MENU_SHOWN = 0x4D575253                                 # 'SRWM' + k in MENU_SAVE: alias k's texture is in VRAM
MODELS = 0x8007C4E8; FN_MDL = 0x80064A08; MUSIC = 0x800171B4; MDL_SITES = [0x800602E8, 0x80061580]
UPLOAD = 0x8005DB60; WEAR_UPLOADS = [0x80064100, 0x80064124]
LOADIMAGE = 0x80029B7C; STOREIMAGE = 0x80029BE0; DRAWSYNC = 0x800298B8; QPOLL = 0x80013CE0
CDMODE = 0x80013C94       # CdControl(CdlSetmode, 0xA0): data reading, as the game's own loads do
DATA = 0x8001FBC4; DATA_END = 0x8001FCA8
ALIASV, ACUR, AB, ASTP, BASEV, MODESV, IDX, STATS, PARAMS, ENT, VPITCH = (DATA + o for o in (0, 4, 8, 0xC, 0x10, 0x14, 0x18, 0x24, 0x48, 0x7C, 0xAC))
ENT3, IDX3, ALIAS2 = DATA + 0xB4, DATA + 0xCC, DATA + 0xD4   # 2 players: player 2's models (files, indices), player 2's alias
TEN = DATA + 0xD8; MAX_FLAG = 0x8002957C                        # a stat of 10 (MAX on the WEAR screen); mod max's on/off flag
# voices: the base rider's, played higher or lower (SPU pitch, 0x5CE = the game's own): Jicchi -1.5, Nick -4, Kelly +3 semitones
PLAY = 0x80015D18; VOICE_CH, VOICE_PITCH = 0x100000, 0x5CE
VOICE_SEMI = [-1.5, -4, 3]
BASE = [0, 1, 2]
MODES = (1 << 2) | (1 << 3) | (1 << 5) | (1 << 6) | (1 << 7) | (1 << 8)   # Free Style (1P, 2P), Big Air, Big Air Master, Halfpipe, Board Park
STAT_BARS = [(3, 4, 4, 6, 6, 8), (2, 4, 6, 4, 8, 6), (6, 8, 6, 6, 4, 4)]    # BOARDER screen bars (display only)
SBC2_PARAMS = 0x8008F1F8; SBC2_SLOT = [4, 5, 6]                               # race parameters of the CPU riders
NAV = 0x80063E7C; FACE = 0x80063324; NAME = 0x800637A4; ENQ = 0x80013BD0
NAV_H = [0x8005FCE0, 0x8005FE58]; NAV_B = [0x80061570]; NAV_H2 = [0x8005FD48]       # hub (2 players: player 2's name)
FACE_H = [0x800600F4]; NAME_H = [0x8005FFCC, 0x8006005C, 0x80060118]; NAME_H2 = [0x8005FFF0, 0x80060080]
FACE_B = [0x80062680, 0x800628DC, 0x800643D4, 0x8006476C]; NAME_B = [0x800626A0, 0x800628FC, 0x800643FC, 0x80064794]
BARS = [(0x800612F4, 'a0', 't1'), (0x800614AC, 'a0', 't1'), (0x80061904, 'a0', 't0'), (0x80062990, 'v1', 's7'), (0x800629E0, 'v1', 's7')]
LOAD_SITES = [(0x8001D420, 0x24), (0x8001D55C, 0x24),   # func_8001D1B8 (Free Style...): P1 model (not VS) / P1 texture
              (0x8001D828, 0x20), (0x8001D938, 0x20),   # func_8001D694 (Halfpipe...): P1 model / P1 texture
              (0x8001D3AC, 0x24), (0x8001D3E8, 0x24), (0x8001D644, 0x24)]   # 2 players (VS): P1 model, P2 model, P2 texture
CINIT = 0x80060218; CCOM = 0x800605A8
RACE = {'/FREE.BIN': 0x8006465C, '/TM.BIN': 0x80063C38, '/HP.BIN': 0x80063D0C, '/BP.BIN': 0x80063B1C, '/OMT.BIN': 0x80063C58,
        '/COMB.BIN': 0x80064B88, '/VS.BIN': 0x80064E08}   # addu of the params pointer (VS: 2 players, racer number at sp + 0x408)
VS_RACER = 0x408


def H(a): return ((a + 0x8000) >> 16) & 0xffff
def L(a): return a - (((a + 0x8000) >> 16) << 16)


def routines(race_regs):
    S = []
    # aval(a0 = rider, a1 = alias) -> v0 = alias if usable in this mode for this rider, else 0 (uses at only)
    S += ['aval:', 'beqz a1, av0', f'lui at, {H(BASEV)}', 'addu at, at, a1', f'lbu at, {L(BASEV)}(at)', 'nop', 'bne at, a0, av0',
          'lui at, 0x8005', 'lw v0, 0x7420(at)', f'lui at, {H(MODESV)}', f'lw at, {L(MODESV)}(at)', 'nop',
          'srlv at, at, v0', 'andi at, at, 1', 'beqz at, av0', 'nop', 'j acomp', 'nop', 'av0:', 'jr ra', 'move v0, zero']
    # amode() -> v0 = 1 if the mode allows the new riders and they are won (uses at, a1)
    S += ['amode:', 'lui at, 0x8005', 'lw v0, 0x7420(at)', f'lui at, {H(MODESV)}', f'lw at, {L(MODESV)}(at)', 'nop', 'srlv at, at, v0',
          'andi at, at, 1', 'bnez at, am1', 'nop', 'jr ra', 'move v0, zero', 'am1:', 'j acomp', 'addiu a1, zero, 1']
    # acomp(a1) -> v0 = a1 if the game is complete (100 % of the progress page) or with the 'unlock' mod, else 0 (uses at, v0)
    S += ['acomp:', f'lui at, {H(UNLOCK_ALL[0])}', f'lw v0, {L(UNLOCK_ALL[0])}(at)', f'lui at, {UNLOCK_ALL[1] >> 16:#x}', f'ori at, at, {UNLOCK_ALL[1] & 0xffff:#x}',
          'beq v0, at, ac1', 'lui at, 0x8005', 'lhu v0, 0x7440(at)', 'nop', 'srl v0, v0, 4', 'andi v0, v0, 7', 'xori v0, v0, 7', 'bnez v0, ac0',
          'lhu v0, 0x7442(at)', 'nop', 'andi v0, v0, 7', 'xori v0, v0, 7', 'bnez v0, ac0',
          *[x for o in (0x7448, 0x744A, 0x744C) for x in (f'lhu v0, {o}(at)', 'nop', 'andi v0, v0, 0x3ff', 'xori v0, v0, 0x3ff', 'bnez v0, ac0')],
          'lhu v0, 0x7444(at)', 'nop', 'beqz v0, ac0', 'lhu v0, 0x7446(at)', 'nop', 'beqz v0, ac0',
          'lhu v0, 0x743c(at)', 'nop', 'sltiu v0, v0, 10', 'bnez v0, ac0', 'lhu v0, 0x743e(at)', 'nop', 'sltiu v0, v0, 10', 'bnez v0, ac0', 'nop',
          'ac1:', 'jr ra', 'move v0, a1', 'ac0:', 'jr ra', 'move v0, zero']
    # setcur(a0 = alias): ACUR, AB (base + 1, 0 = none), ASTP (stat bars row)
    S += ['setcur:', f'lui at, {H(ACUR)}', f'sw a0, {L(ACUR)}(at)', 'beqz a0, sc0', 'move v0, zero',
          f'lui at, {H(BASEV)}', 'addu at, at, a0', f'lbu v0, {L(BASEV)}(at)', 'nop', 'addiu v0, v0, 1',
          'sc0:', f'lui at, {H(AB)}', f'sw v0, {L(AB)}(at)', 'sll v0, a0, 3', 'sll at, a0, 2', 'addu v0, v0, at',
          f'lui at, {H(STATS - 12)}', f'addiu at, at, {L(STATS - 12)}', 'addu v0, v0, at', f'lui at, {H(ASTP)}', 'jr ra', f'sw v0, {L(ASTP)}(at)']
    # rider list: navH (hub, ALIAS) / navB (BOARDER screen, ACUR); a0 = rider, a1 = direction (< 0 = next)
    S += ['navH2:', f'lui t9, {H(ALIAS2)}', 'j nav', f'addiu t9, t9, {L(ALIAS2)}',
          'navH:', f'lui t9, {H(ALIASV)}', 'j nav', f'addiu t9, t9, {L(ALIASV)}',
          'navB:', f'lui t9, {H(ACUR)}', f'addiu t9, t9, {L(ACUR)}',
          'nav:', 'addiu sp, sp, -0x28', 'sw ra, 0x10(sp)', 'sw s0, 0x14(sp)', 'sw s1, 0x18(sp)', 'sw s2, 0x1c(sp)', 'sw s3, 0x20(sp)',
          'move s0, t9', 'move s1, a0', 'move s2, a1', 'lw a1, 0(s0)', 'jal aval', 'nop', 'move s3, v0', 'jal amode', 'nop',
          'bltz s2, nx', 'nop',
          'beqz s3, pv0', 'addiu s3, s3, -1', 'bnez s3, fink', 'nop', 'j fin', 'addiu v0, zero, 3',
          'pv0:', 'move s3, zero', 'sw v0, 0x24(sp)', 'move a0, s1', f'jal {NAV}', 'move a1, s2', 'lw t0, 0x24(sp)', 'addiu at, zero, 3',
          'bne v0, at, fin', 'nop', 'beqz t0, fin', 'nop', 'beq s1, at, fin', 'nop', 'j fink', 'addiu s3, zero, 3',
          'nx:', 'bnez s3, nx1', 'addiu at, zero, 3', 'bne s1, at, nxo', 'nop', 'beqz v0, nxo', 'nop', 'j fink', 'addiu s3, zero, 1',
          'nx1:', 'beq s3, at, nx3', 'nop', 'j fink', 'addiu s3, s3, 1',
          'nx3:', 'move s3, zero', 'addiu s1, zero, 3',
          'nxo:', 'move a0, s1', f'jal {NAV}', 'move a1, s2', 'j fin', 'nop',
          'fink:', f'lui at, {H(BASEV)}', 'addu at, at, s3', f'lbu v0, {L(BASEV)}(at)',
          'fin:', 'sw s3, 0(s0)', f'lui at, {H(ACUR)}', f'addiu at, at, {L(ACUR)}', 'bne s0, at, fn9', 'sw v0, 0x24(sp)',
          'jal setcur', 'move a0, s3',
          'fn9:', 'lw v0, 0x24(sp)', 'lw ra, 0x10(sp)', 'lw s0, 0x14(sp)', 'lw s1, 0x18(sp)', 'lw s2, 0x1c(sp)', 'lw s3, 0x20(sp)', 'jr ra', 'addiu sp, sp, 0x28']
    # portrait / name: call the game's function, then point the primitive (v0 - 0x28) at the new picture
    for kind, fn in (('f', FACE), ('n', NAME)):
        S += [f'{kind}wH2:', f'lui t9, {H(ALIAS2)}', f'j {kind}w', f'addiu t9, t9, {L(ALIAS2)}',
              f'{kind}wH:', f'lui t9, {H(ALIASV)}', f'j {kind}w', f'addiu t9, t9, {L(ALIASV)}',
              f'{kind}wB:', f'lui t9, {H(ACUR)}', f'addiu t9, t9, {L(ACUR)}',
              f'{kind}w:', 'addiu sp, sp, -0x30', 'sw ra, 0x28(sp)', 'sw s0, 0x24(sp)', 'sw t9, 0x1c(sp)',
              *([f'lui t0, {H(ACUR)}', f'addiu t0, t0, {L(ACUR)}', 'bne t0, t9, fwp', 'nop', 'jal mpoll', 'nop', 'fwp:', 'lw t9, 0x1c(sp)'] if kind == 'f' else []),
              'sw a0, 0x18(sp)',
              'lw t0, 0x40(sp)', 'lw t1, 0x44(sp)',
              'sw t0, 0x10(sp)', 'sw t1, 0x14(sp)', f'jal {fn}', 'sw t1, 0x20(sp)', 'move s0, v0',
              f'j {kind}wx', 'nop', f'{kind}wx:',
              'lw t9, 0x1c(sp)', 'lw a0, 0x20(sp)', 'lw a1, 0(t9)', 'jal aval', 'nop', 'beqz v0, ' + kind + 'w9', 'addiu v0, v0, -1']
        if kind == 'f':   # 8-bit 64x64 at VRAM (832 + 32 k, 320): u 64 k, v 64..128; CLUT (928, 320 + k); tpage x 832, y 256
            S += ['sll t0, v0, 6', 'addiu t1, t0, 64', 'addiu t2, zero, 64', 'addiu t3, zero, 128',
                  f'addiu t4, v0, {CLUT_Y}', 'sll t4, t4, 6', f'ori t4, t4, {CLUT_X >> 4}', 'sh t4, -0x1a(s0)', 'ori t5, zero, 0x1d']
        else:             # 4-bit 48x32 at VRAM (960 + 12 k, 352): u 48 k, v 96..128; tpage x 960, y 256
            S += ['sll t0, v0, 5', 'sll t1, v0, 4', 'addu t0, t0, t1', 'addiu t1, t0, 48', 'addiu t2, zero, 96', 'addiu t3, zero, 128', 'ori t5, zero, 0x1f']
        S += ['sb t0, -0x1c(s0)', 'sb t0, -0xc(s0)', 'sb t1, -0x14(s0)', 'sb t1, -0x4(s0)',
              'sb t2, -0x1b(s0)', 'sb t2, -0x13(s0)', 'sb t3, -0xb(s0)', 'sb t3, -0x3(s0)',
              'lhu t4, -0x12(s0)', 'nop', 'andi t4, t4, 0xffe0', 'or t4, t4, t5', 'sh t4, -0x12(s0)',
              f'{kind}w9:',
              *([f'lui t0, {H(ACUR)}', 'lw t9, 0x1c(sp)', f'addiu t0, t0, {L(ACUR)}', 'bne t0, t9, nws', 'move a0, s0',
                 'lw a1, 0x20(sp)', 'jal strip', 'addiu a2, s0, -0x28', 'move s0, v0', 'nws:'] if kind == 'n' else []),
              'move v0, s0', 'lw ra, 0x28(sp)', 'lw s0, 0x24(sp)', 'jr ra', 'addiu sp, sp, 0x30']
    # stat bars: replaces "sll v0, v0, 2" (delay slot: addu v0, v0, X) -> v0 = row pointer offset
    for rr, xr in sorted({(r, x) for _, r, x in BARS}):
        # WEAR screen (v1, s7; the value is then read at s2 + v0): with MAX on (mod max: its flag is 1), every bar
        # reads TEN, as maxd does on the BOARDER screen (without the mod the word holds code, never 1)
        mx = ([f'lui at, {H(MAX_FLAG)}', f'lw at, {L(MAX_FLAG)}(at)', 'nop', 'xori at, at, 1', f'bnez at, bm_{rr}_{xr}', 'nop',
               f'lui v0, {H(TEN)}', f'addiu v0, v0, {L(TEN)}', 'jr ra', 'subu v0, v0, s2', f'bm_{rr}_{xr}:'] if (rr, xr) == ('v1', 's7') else [])
        S += [f'bar_{rr}_{xr}:', *mx, f'lui at, {H(AB)}', f'lw at, {L(AB)}(at)', f'addiu {rr}, {rr}, 1', f'bne at, {rr}, br_{rr}_{xr}', f'addiu {rr}, {rr}, -1',
              f'lui at, {H(ASTP)}', f'lw v0, {L(ASTP)}(at)', 'jr ra', 'nop',
              f'br_{rr}_{xr}:', f'subu v0, v0, {xr}', 'sll v0, v0, 2', 'jr ra', f'addu v0, v0, {xr}']
    # file loads of the player's rider (P1 model / texture)
    S += ['ld24:', 'j ld', 'addiu t7, s1, 0x24', 'ld20:', 'j ld', 'addiu t7, s1, 0x20',
          'ld:', 'subu t8, a2, s1', 'addiu at, zero, 0x14', 'beq t8, at, ldq', 'addiu at, zero, 0x28', 'beq t8, at, ldq', 'nop',
          'move t4, ra', 'move t5, a0', 'move t6, a1', 'lui at, 0x8005', 'lh a0, 0x7408(at)', f'lui at, {H(ALIASV)}', f'lw a1, {L(ALIASV)}(at)', 'jal aval', 'nop',
          'move ra, t4', 'move a0, t5', 'beqz v0, ld9', 'move a1, t6', 'sll t0, v0, 1', f'lui at, {H(IDX)}', 'addu at, at, t0',
          'addiu t1, s1, 0x10', 'bne a2, t1, ld1', 'nop', 'j ld9', f'lh a0, {L(IDX) - 2}(at)',
          'ld1:', 'bne a2, t7, ld9', 'nop', f'lh a0, {L(IDX) + 4}(at)',
          'ld9:', f'j {ENQ}', 'nop',
          # player 2 (2 players): slot 0x14 = model (its own copy, IDX3), 0x28 = texture (the same files as player 1)
          'ldq:', 'move t4, ra', 'move t5, a0', 'move t6, a1', 'lui at, 0x8005', 'lh a0, 0x7412(at)', f'lui at, {H(ALIAS2)}', f'lw a1, {L(ALIAS2)}(at)',
          'jal aval', 'nop', 'move ra, t4', 'move a0, t5', 'beqz v0, ld9', 'move a1, t6', 'sll t0, v0, 1', 'addiu at, zero, 0x14',
          'bne t8, at, ldq1', f'lui at, {H(IDX3)}', 'addu at, at, t0', 'j ld9', f'lh a0, {L(IDX3) - 2}(at)',
          'ldq1:', f'lui at, {H(IDX)}', 'addu at, at, t0', 'j ld9', f'lh a0, {L(IDX) + 4}(at)']
    # BOARDER screen opens (sel_riderCursor = g_rider): ACUR = usable ALIAS; validated: ALIAS = ACUR
    S += ['cinit:', 'lhu v0, 0x7408(v0)', 'move t4, ra', 'move t5, a0', 'move t6, a1', 'move t3, v0', 'sll a0, v0, 16', 'sra a0, a0, 16',
          f'lui at, {H(ALIASV)}', 'beqz a1, ci1', f'lw a1, {L(ALIASV)}(at)', 'lui at, 0x8005', 'lh a0, 0x7412(at)', f'lui at, {H(ALIAS2)}',
          f'lw a1, {L(ALIAS2)}(at)', 'ci1:', 'jal aval', 'nop', 'jal setcur', 'move a0, v0',
          'move ra, t4', 'move a0, t5', 'move a1, t6', 'move v0, t3', f'j {CINIT + 8}', 'nop']
    # play function of the exe (a0 pitch, a1 SPU voice bit, a2 sample, a3 volume): the rider's voice in a race
    # (voice 20, pitch 0x5CE) with an alias -> its own pitch. Replaces "lui v0 / lhu v0" at the entry. Not aval: its
    # 'unlock' test reads MAIN_SEL, gone in a race.
    S += ['vp:', f'lui at, {VOICE_CH >> 16:#x}', 'bne a1, at, vp9', f'addiu at, zero, {VOICE_PITCH}', 'bne a0, at, vp9',
          'lui at, 0x8006', 'lw at, -0x5158(at)', 'nop', 'addiu at, at, -8', 'bnez at, vp9',
          # alias chosen (the BOARDER screen already checked it was won), for this base rider, in an allowed mode
          f'lui at, {H(ALIASV)}', f'lw t0, {L(ALIASV)}(at)', 'nop', 'beqz t0, vp9', f'lui at, {H(BASEV)}', 'addu at, at, t0',
          f'lbu t1, {L(BASEV)}(at)', 'lui at, 0x8005', 'lh t2, 0x7408(at)', 'lw t3, 0x7420(at)', 'bne t1, t2, vp9',
          f'lui at, {H(MODESV)}', f'lw at, {L(MODESV)}(at)', 'nop', 'srlv at, at, t3', 'andi at, at, 1', 'beqz at, vp9',
          'sll t3, t0, 1', f'lui at, {H(VPITCH - 2)}', 'addu at, at, t3', f'lhu a0, {L(VPITCH - 2)}(at)',
          'vp9:', 'lui v0, 0x8005', 'lhu v0, 0x08a8(v0)', f'j {PLAY + 8}', 'nop']
    S += ['ccom:', 'sh v0, 0x7408(at)', f'lui at, {H(ACUR)}', f'lw t9, {L(ACUR)}(at)', 'bnez s6, cc2', f'lui at, {H(ALIASV)}', f'j {CCOM + 8}',
          f'sw t9, {L(ALIASV)}(at)', 'cc2:', f'lui at, {H(ALIAS2)}', f'j {CCOM + 8}', f'sw t9, {L(ALIAS2)}(at)']
    # race parameters: replaces "sll v0, R, 4" (delay slot: lui v1, hi); the next instruction (at ra) is addiu v1, v1, lo
    # rider in a register R (one stub per register: t2 = R); 2 players (VS.BIN, R = s2): racer 0 = player 1 (g_rider,
    # ALIAS), racer 1 = player 2 (0x80057412, ALIAS2), racer number at sp + VS_RACER
    for rr in sorted(set(race_regs)):
        S += [f'rp_{rr}:', 'sw t2, -12(sp)', 'j rpg', f'move t2, {rr}']
    S += ['rpv:', 'sw t2, -12(sp)', 'sw t0, -4(sp)', 'sw t1, -8(sp)', 'move t2, s2', f'lw t1, {VS_RACER}(sp)', 'lui at, 0x8005', 'lh t0, 0x7408(at)',
          'beqz t1, rpv1', 'addiu t1, t1, -1', 'bnez t1, rpvn', 'lh t0, 0x7412(at)', f'lui t1, {H(ALIAS2)}', 'j rpc', f'lw t1, {L(ALIAS2)}(t1)',
          'rpv1:', f'lui t1, {H(ALIASV)}', 'j rpc', f'lw t1, {L(ALIASV)}(t1)', 'rpvn:', 'j rp9', 'nop',
          'rpg:', 'sw t0, -4(sp)', 'sw t1, -8(sp)', 'lui at, 0x8005', 'lh t0, 0x7408(at)', 'lw t1, 0x7420(at)', f'lui at, {H(MODESV)}',
          f'lw at, {L(MODESV)}(at)', 'nop', 'srlv at, at, t1', 'andi at, at, 1', 'beqz at, rp9', f'lui t1, {H(ALIASV)}', f'lw t1, {L(ALIASV)}(t1)',
          'rpc:', 'bne t0, t2, rp9', 'nop', 'beqz t1, rp9', f'lui at, {H(BASEV)}', 'addu at, at, t1', f'lbu at, {L(BASEV)}(at)', 'nop',
          'bne at, t0, rp9', 'nop', 'lh at, 0(ra)', 'sll t1, t1, 4', 'addu at, at, v1', f'lui t0, {H(PARAMS - 16)}', f'addiu t0, t0, {L(PARAMS - 16)}',
          'addu t0, t0, t1', 'j rpe', 'subu v0, t0, at',
          'rp9:', 'sll v0, t2, 4', 'rpe:', 'lw t0, -4(sp)', 'lw t1, -8(sp)', 'lw t2, -12(sp)', 'jr ra', 'nop']
    # ---- menu models (BOARDER screen): see menu_chunk()
    MM = MENU_BUF + M_MAGIC
    rect = lambda tbl, kreg: [f'addiu t0, {kreg}, -1', 'sll t0, t0, 3', f'lui a0, {H(tbl)}', f'addiu a0, a0, {L(tbl)}', 'addu a0, a0, t0']
    # mreq(a0 = k): load the model of alias k into MENU_BUF (CD queue), unless already asked
    S += ['mreq:', 'addiu sp, sp, -0x20', 'sw ra, 0x10(sp)', 'sw s0, 0x14(sp)', 'move s0, a0',
          f'lui at, {H(PENDING)}', f'lw t0, {L(PENDING)}(at)', 'nop', 'beq t0, s0, mr9', 'nop', f'sw s0, {L(PENDING)}(at)',
          f'lui at, {H(MM)}', f'sw zero, {L(MM)}(at)', f'jal {CDMODE}', 'nop',
          'sll t0, s0, 1', f'lui at, {H(IDX2 - 2)}', 'addu at, at, t0', f'lh a0, {L(IDX2 - 2)}(at)',
          f'lui a1, {H(MENU_BUF)}', f'addiu a1, a1, {L(MENU_BUF)}', f'lui a2, {H(DUMMY)}', f'addiu a2, a2, {L(DUMMY)}',
          f'jal {ENQ}', 'addiu a3, zero, 1',
          'mr9:', 'lw ra, 0x10(sp)', 'lw s0, 0x14(sp)', 'jr ra', 'addiu sp, sp, 0x20']
    # munsh(): the base rider's texture back in VRAM if an alias's is there
    S += ['munsh:', 'addiu sp, sp, -0x20', 'sw ra, 0x10(sp)', 'sw s0, 0x14(sp)', f'lui at, {H(MENU_SAVE)}', f'lw s0, {L(MENU_SAVE)}(at)',
          f'lui t0, {H(MENU_SHOWN)}', f'addiu t0, t0, {L(MENU_SHOWN)}', 'subu s0, s0, t0', 'addiu t1, s0, -1', 'sltiu t1, t1, 3', 'beqz t1, mu9', 'nop',
          f'jal {DRAWSYNC}', 'move a0, zero', *rect(RCOL, 's0'), f'lui a1, {H(MENU_SAVE + 0x204)}', f'jal {LOADIMAGE}', f'addiu a1, a1, {L(MENU_SAVE + 0x204)}',
          *rect(RCLUT, 's0'), f'lui a1, {H(MENU_SAVE + 4)}', f'jal {LOADIMAGE}', f'addiu a1, a1, {L(MENU_SAVE + 4)}',
          f'jal {DRAWSYNC}', 'move a0, zero', f'lui at, {H(MENU_SAVE)}', f'sw zero, {L(MENU_SAVE)}(at)',
          'mu9:', 'lw ra, 0x10(sp)', 'lw s0, 0x14(sp)', 'jr ra', 'addiu sp, sp, 0x20']
    # mshow(a0 = k): the base rider's texture saved, alias k's put in its place
    S += ['mshow:', 'addiu sp, sp, -0x20', 'sw ra, 0x10(sp)', 'sw s0, 0x14(sp)', 'move s0, a0', f'lui at, {H(MENU_SAVE)}', f'lw t1, {L(MENU_SAVE)}(at)',
          f'lui t0, {H(MENU_SHOWN)}', f'addiu t0, t0, {L(MENU_SHOWN)}', 'addu t0, t0, s0', 'bne t0, t1, msa', 'nop', 'j ms9', 'nop', 'msa:',
          'jal munsh', 'nop', f'jal {DRAWSYNC}', 'move a0, zero',
          *rect(RCOL, 's0'), f'lui a1, {H(MENU_SAVE + 0x204)}', f'jal {STOREIMAGE}', f'addiu a1, a1, {L(MENU_SAVE + 0x204)}',
          *rect(RCLUT, 's0'), f'lui a1, {H(MENU_SAVE + 4)}', f'jal {STOREIMAGE}', f'addiu a1, a1, {L(MENU_SAVE + 4)}',
          f'jal {DRAWSYNC}', 'move a0, zero', 'j msb', 'nop', 'msb:',
          *rect(RCOL, 's0'), f'lui a1, {H(MENU_BUF + M_IMG)}', f'jal {LOADIMAGE}', f'addiu a1, a1, {L(MENU_BUF + M_IMG)}',
          *rect(RCLUT, 's0'), f'lui a1, {H(MENU_BUF + M_CLUT)}', f'jal {LOADIMAGE}', f'addiu a1, a1, {L(MENU_BUF + M_CLUT)}',
          f'jal {DRAWSYNC}', 'move a0, zero',
          f'lui t0, {H(MENU_SHOWN)}', f'addiu t0, t0, {L(MENU_SHOWN)}', 'addu t0, t0, s0', f'lui at, {H(MENU_SAVE)}', f'sw t0, {L(MENU_SAVE)}(at)',
          'ms9:', 'lw ra, 0x10(sp)', 'lw s0, 0x14(sp)', 'jr ra', 'addiu sp, sp, 0x20']
    # mdl(a0 = rider): replaces the BOARDER screen's calls to func_80064A08 (model of the rider)
    S += ['mdl:', 'addiu sp, sp, -0x28', 'sw ra, 0x10(sp)', 'sw s0, 0x14(sp)', 'sw s1, 0x18(sp)', 'sw s2, 0x1c(sp)', 'move s0, a0',
          f'lui at, {H(ACUR)}', f'lw a1, {L(ACUR)}(at)', 'jal aval', 'nop', 'move s1, v0', 'bnez s1, mdk', 'nop', 'j md0', 'nop',
          'mdk:', f'lui at, {H(MM)}', f'lw t0, {L(MM)}(at)', f'lui t1, {H(MENU_MAGIC)}', f'addiu t1, t1, {L(MENU_MAGIC)}', 'addu t1, t1, s1', 'beq t0, t1, mdk2', 'nop',
          'j mdq', 'nop', 'mdk2:',
          'jal mshow', 'move a0, s1',
          'sll t2, s0, 2', f'lui at, {H(MODELS)}', 'addu at, at, t2', f'lw s2, {L(MODELS)}(at)', f'lui t3, {H(MENU_BUF)}', f'addiu t3, t3, {L(MENU_BUF)}', f'sw t3, {L(MODELS)}(at)',
          f'jal {FN_MDL}', 'move a0, s0',
          'sll t2, s0, 2', f'lui at, {H(MODELS)}', 'addu at, at, t2', 'j md9', f'sw s2, {L(MODELS)}(at)',
          'mdq:', 'jal mreq', 'move a0, s1',
          'md0:', 'jal munsh', 'nop', f'jal {FN_MDL}', 'move a0, s0',
          'md9:', 'lw ra, 0x10(sp)', 'lw s0, 0x14(sp)', 'lw s1, 0x18(sp)', 'lw s2, 0x1c(sp)', 'jr ra', 'addiu sp, sp, 0x28']
    # mpoll(): every frame of the BOARDER screen while a model is being loaded (keeps a0-a3)
    S += ['mpoll:', f'lui at, {H(PENDING)}', f'lw t0, {L(PENDING)}(at)', 'nop', 'bnez t0, mp1', 'nop', 'jr ra', 'nop',
          'mp1:', 'addiu sp, sp, -0x28', 'sw ra, 0x10(sp)', 'sw s0, 0x14(sp)', 'sw a0, 0x18(sp)', 'sw a1, 0x1c(sp)', 'sw a2, 0x20(sp)', 'sw a3, 0x24(sp)', 'move s0, t0',
          f'jal {QPOLL}', 'nop', f'lui at, {H(MM)}', f'lw t0, {L(MM)}(at)', f'lui t1, {H(MENU_MAGIC)}', f'addiu t1, t1, {L(MENU_MAGIC)}', 'addu t1, t1, s0', 'bne t0, t1, mp9',
          f'lui at, {H(PENDING)}', f'sw zero, {L(PENDING)}(at)',
          # the read stopped the menu's CD music (data mode): it starts again, as MAIN_SEL's entry starts it (v54)
          'addiu a0, zero, 3', f'jal {MUSIC}', 'addiu a1, zero, 2',
          f'lui at, {H(ACUR)}', f'lw t0, {L(ACUR)}(at)', 'nop', 'bne t0, s0, mp9', f'lui at, {H(BASEV)}',
          'addu at, at, s0', 'jal mdl', f'lbu a0, {L(BASEV)}(at)',
          'mp9:', 'lw ra, 0x10(sp)', 'lw s0, 0x14(sp)', 'lw a0, 0x18(sp)', 'lw a1, 0x1c(sp)', 'lw a2, 0x20(sp)', 'lw a3, 0x24(sp)', 'jr ra', 'addiu sp, sp, 0x28']
    # strip(a0 = primitive buffer, a1 = rider under the cursor, a2 = the name tag's primitive) -> v0 = buffer after the
    # 10 heads (POLY_FT4 written here, linked right after the name tag: drawn over the screen like it)
    S += ['strip:', 'addiu sp, sp, -0x48', 'sw ra, 0x40(sp)', 'sw s0, 0x20(sp)', 'sw s1, 0x24(sp)', 'sw s2, 0x28(sp)', 'sw s3, 0x2c(sp)',
          'sw s4, 0x30(sp)', 'sw s5, 0x34(sp)', 'move s0, a0', 'move s2, a1', 'move s1, a2',
          f'lui at, {H(ACUR)}', f'lw a1, {L(ACUR)}(at)', 'jal aval', 'move a0, s2', 'bnez v0, st1', 'addiu s3, v0, 3',
          'move s3, s2', 'slti t0, s2, 4', 'bnez t0, st1', 'nop', 'addiu s3, s2, 3',
          'st1:', 'lui at, 0x8005', 'lhu s4, 0x7440(at)', f'lui at, {H(UNLOCK_ALL[0])}', f'lw t0, {L(UNLOCK_ALL[0])}(at)',
          f'lui t1, {UNLOCK_ALL[1] >> 16:#x}', f'ori t1, t1, {UNLOCK_ALL[1] & 0xffff:#x}', 'bne t0, t1, st2', 'nop', 'ori s4, s4, 0x7f',
          'st2:', 'jal amode', 'nop', 'beqz v0, st3', 'nop', 'ori s4, s4, 0x380',
          'st3:', 'j stl', 'move s5, zero',
          # i -> availability bit: 0..3 = riders 0..3, 4..6 = bits 7..9, 7..9 = riders 4..6
          'stl:', 'move t0, s5', 'slti t1, s5, 4', 'bnez t1, st4', 'slti t1, s5, 7', 'beqz t1, st4', 'addiu t0, s5, -3', 'addiu t0, s5, 3',
          'st4:', 'srlv t0, s4, t0', 'andi t9, t0, 1',            # t9 = 1: available
          # colour: 0x80 under the cursor, 0x50 the others
          'lui t0, 0x2c50', 'ori t0, t0, 0x5050', 'bne s5, s3, st5', 'nop', 'lui t0, 0x2c80', 'ori t0, t0, 0x8080',
          'st5:', 'sw t0, 4(s0)',
          # screen: two rows of 5 under the BOARDER title, 16x16 (20x20 under the cursor)
          'move t8, s5', f'addiu t1, zero, {STRIP_Y}', 'slti t0, s5, 5', 'bnez t0, sts', 'nop', 'addiu t8, s5, -5', f'addiu t1, t1, {STRIP_DY}',
          'sts:', 'sll t0, t8, 4', 'sll t8, t8, 1', 'addu t0, t0, t8', f'addiu t0, t0, {STRIP_X}', 'addiu t2, t0, 16', 'addiu t3, t1, 16',
          'bne s5, s3, st7', 'nop', 'addiu t0, t0, -2', 'addiu t1, t1, -2', 'addiu t2, t2, 2', 'addiu t3, t3, 2',
          'st7:', 'sh t0, 8(s0)', 'sh t1, 0xa(s0)', 'sh t2, 0x10(s0)', 'sh t1, 0x12(s0)', 'sh t0, 0x18(s0)', 'sh t3, 0x1a(s0)', 'sh t2, 0x20(s0)', 'sh t3, 0x22(s0)',
          'j stp', 'nop',
          # texture: u 16 i, v 68..84, tpage of the name tag with x 960, y 256; palette x 928 + 16 (i % 6), row 340 + i // 6 (+ 2: grey)
          'stp:', 'sll t0, s5, 4', 'sb t0, 0xc(s0)', 'sb t0, 0x1c(s0)', 'addiu t0, t0, 16', 'sb t0, 0x14(s0)', 'sb t0, 0x24(s0)',
          f'addiu t0, zero, {ICON_Y - 256}', 'sb t0, 0xd(s0)', 'sb t0, 0x15(s0)', f'addiu t0, zero, {ICON_Y - 240}', 'sb t0, 0x1d(s0)', 'sb t0, 0x25(s0)',
          'lhu t0, 0x16(s1)', 'nop', 'andi t0, t0, 0xffe0', 'ori t0, t0, 0x1f', 'sh t0, 0x16(s0)',
          'slti t1, s5, 6', 'move t2, s5', f'addiu t3, zero, {ICON_CLUT_Y}', 'bnez t1, st8', 'nop', 'addiu t2, s5, -6', f'addiu t3, zero, {ICON_CLUT_Y + 1}',
          'st8:', 'bnez t9, st9', 'nop', 'addiu t3, t3, 2',
          'st9:', 'sll t3, t3, 6', f'addiu t2, t2, {ICON_CLUT_X >> 4}', 'or t3, t3, t2', 'sh t3, 0xe(s0)',
          # link after the name tag: s0.tag = 9 words, next = the name's next; name.next = s0
          'lw t0, 0(s1)', 'lui t1, 0xff', 'ori t1, t1, 0xffff', 'and t2, t0, t1', 'lui t3, 0x0900', 'or t2, t2, t3', 'sw t2, 0(s0)',
          'lui t3, 0xff00', 'and t0, t0, t3', 'and t2, s0, t1', 'or t0, t0, t2', 'sw t0, 0(s1)', 'move s1, s0',
          'addiu s0, s0, 0x28', 'addiu s5, s5, 1', 'slti t0, s5, 10', 'beqz t0, stx', 'nop', 'j stl', 'nop', 'stx:',
          'move v0, s0',          'st9x:', 'move v0, s0', 'lw ra, 0x40(sp)', 'lw s0, 0x20(sp)', 'lw s1, 0x24(sp)', 'lw s2, 0x28(sp)', 'lw s3, 0x2c(sp)', 'lw s4, 0x30(sp)', 'lw s5, 0x34(sp)', 'jr ra', 'addiu sp, sp, 0x48']
    # wup: the WEAR screen's texture uploads are skipped while an alias's texture is shown
    S += ['wup:', f'lui at, {H(MENU_SAVE)}', f'lw t0, {L(MENU_SAVE)}(at)', f'lui t1, {H(MENU_SHOWN)}', f'addiu t1, t1, {L(MENU_SHOWN + 1)}', 'subu t0, t0, t1',
          'sltiu t0, t0, 3', 'beqz t0, wu1', 'nop', 'jr ra', 'nop', 'wu1:', f'j {UPLOAD}', 'nop']
    return S



def place(S):
    """split the routines over the caves (whole routines only) -> words, labels"""
    blocks = []; cur = []
    for l in S:
        if l.endswith(':') and cur and not any(cur[-1].startswith(x) for x in ()) and l[:-1] in TOP: blocks.append(cur); cur = []
        cur.append(l)
    blocks.append(cur)
    def size(b): return 4 * sum(1 for l in b if not l.endswith(':'))
    caves = [[lo, lo, hi, []] for lo, hi in CAVES]
    order = sorted(blocks, key=lambda b: -size(b))            # best fit, largest first; backtracking when stuck (v54)
    def fit_all(i):
        if i == len(order): return True
        b = order[i]; tried = set()
        for c in sorted((c for c in caves if c[1] + size(b) <= c[2]), key=lambda c: c[2] - c[1]):
            room = c[2] - c[1]
            if room in tried: continue
            tried.add(room); c[3].append(b); c[1] += size(b)
            if fit_all(i + 1): return True
            c[3].pop(); c[1] -= size(b)
        return False
    import sys; sys.setrecursionlimit(10000)
    if not fit_all(0): raise ValueError('plus de place pour les routines de crew')
    cave_of = {}; bad = []
    for lo, _, _, bl in caves:
        for l in (l for b in bl for l in b):
            if l.endswith(':'): cave_of[l[:-1]] = lo
    for lo, _, _, bl in caves:
        for l in (l for b in bl for l in b):
            op = l.split()[0] if not l.endswith(':') else ''
            if op in ('beq', 'bne', 'beqz', 'bnez', 'bltz', 'bgez', 'blez', 'bgtz'):
                t = l.split(',')[-1].strip()
                if cave_of.get(t, lo) != lo: bad.append(l)
    assert not bad, 'branches hors de leur zone : ' + ', '.join(bad)
    labels = {}
    for lo, _, _, bl in caves:
        pc = lo
        for l in (l for b in bl for l in b):
            if l.endswith(':'): labels[l[:-1]] = pc
            else: pc += 4
    words = []
    for lo, _, _, bl in caves:
        if bl: words += asm([l for b in bl for l in b], lo, labels)[0]
    return words, labels


# block starts for place(); nx and mdq are not fallen into (an unconditional jump comes before them)
TOP = {'aval', 'amode', 'setcur', 'navH2', 'fwH2', 'nwH2', 'rpv', 'rpg', 'msb', 'navH', 'fwH', 'nwH', 'ld24', 'mreq', 'munsh', 'mshow', 'mdl', 'mdq', 'mpoll', 'wup', 'strip', 'stl', 'stp', 'acomp', 'fwx', 'nwx', 'vp', 'cinit', 'ccom'} | {f'bar_{r}_{x}' for _, r, x in BARS} | {f'rp_{r}' for r in ('s0', 's1', 's2', 's3', 's4', 's5', 's6', 's7')}


# ---------------------------------------------------------------------------------------------------- disc layout
MOVIE = '/MOVIE/OPMOVIEE.STR'; RIDERS_CUT = 37391      # first sector used by the 'riders' mod at the end of the intro movie


def files(fs_read):
    """the six new files (model, texture) x (Jicchi, Nick, Kelly), from the player's own disc"""
    import cpurider
    p0 = fs_read('/DATA/CHR/PLAYER0.DAT'); e1 = fs_read('/DATA/CHR/ENEMY1.FBD'); e2 = fs_read('/DATA/CHR/ENEMY2.FBD')
    hd = fs_read('/DATA/CHR/FR/FBD/FRM1_00.FBD')
    out = []
    for n in NAMES: out += [cpurider.model(p0, n), cpurider.texture(e1, e2, hd, n)]
    return out


def layout(blobs):
    """-> first sector, [(lba, blob)] at the end of the intro movie, just before the 'riders' sectors"""
    n = sum(-(-len(b) // 2048) for b in blobs); lba = RIDERS_CUT - n; first = lba; out = []
    for b in blobs: out.append((lba, b)); lba += -(-len(b) // 2048)
    return first, out


def msf_bcd(lba):
    a = lba + 150; m, sc, f = a // 4500, (a // 75) % 60, a % 75
    b = lambda x: (x // 10) * 16 + x % 10
    return bytes([b(m), b(sc), b(f), 0])


def patches(fs_read, placed):
    """-> [(file, address, new word)] (code, hooks and data); placed = layout()[1]"""
    J = lambda op, t: (op << 26) | ((t >> 2) & 0x3ffffff)
    race_regs = {}
    for f, a in RACE.items():
        d = fs_read(f); sll = struct.unpack_from('<I', d, a - 12 - OVL)[0]
        assert sll & 0xffe0ffff == 0x00001100 and struct.unpack_from('<I', d, a - OVL)[0] == 0x00431021, f
        race_regs[f] = 'zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7'.split()[(sll >> 16) & 31]
    words, lb = place(routines(race_regs.values()))
    P = [('/SCES_009.92', a, w) for a, w in words]
    # data
    ent = b''.join(msf_bcd(l) + struct.pack('<I', len(b)) for l, b in placed[:6])
    idx = [(ENT + 8 * j - G_FILES) // 8 for j in range(6)]
    sb = fs_read('/SBC2.BIN')
    params = b''.join(sb[SBC2_PARAMS - OVL + 16 * s:SBC2_PARAMS - OVL + 16 * s + 16] for s in SBC2_SLOT)
    data = (struct.pack('<IIII', 0, 0, 0, 0) + bytes([0xff] + BASE) + struct.pack('<I', MODES)
            + struct.pack('<6h', idx[0], idx[2], idx[4], idx[1], idx[3], idx[5])
            + b''.join(struct.pack('<6h', *s) for s in STAT_BARS) + params)
    data += bytes(ENT - DATA - len(data)) + ent
    data += b''.join(struct.pack('<H', round(VOICE_PITCH * 2 ** (k / 12))) for k in VOICE_SEMI)
    # 2 players: player 2's models (files 9..11 of placed), their indices, player 2's alias
    data += bytes(ENT3 - DATA - len(data)) + b''.join(msf_bcd(l) + struct.pack('<I', len(b)) for l, b in placed[9:12])
    data += struct.pack('<3h', *[(ENT3 + 8 * k - G_FILES) // 8 for k in range(3)]) + bytes(2) + struct.pack('<I', 0)
    assert (ENT3 - G_FILES) % 8 == 0 and DATA + len(data) == ALIAS2 + 4
    data += struct.pack('<hh', 10, 0); assert DATA + len(data) == TEN + 4 <= DATA_END
    assert DATA + len(data) <= DATA_END and (ENT - G_FILES) % 8 == 0
    data += bytes((-len(data)) % 4)
    P += [('/SCES_009.92', DATA + i, struct.unpack_from('<I', data, i)[0]) for i in range(0, len(data), 4)]
    # menu models: their files, VRAM rectangles of the base riders (texture column, palette row), state
    d2 = b''.join(msf_bcd(l) + struct.pack('<I', len(b)) for l, b in placed[6:9])
    d2 += struct.pack('<3h', *[(ENT2 + 8 * k - G_FILES) // 8 for k in range(3)]) + bytes(2)
    d2 += b''.join(struct.pack('<4h', MENU_COL[k], 0, 64, 256) for k in range(3))
    d2 += b''.join(struct.pack('<4h', 768, MENU_CLUT_Y[k], 256, 1) for k in range(3)) + bytes(8)
    assert DATA2 + len(d2) <= DATA2_END and (ENT2 - G_FILES) % 8 == 0 and len(d2) == DUMMY + 4 - DATA2
    P += [('/SCES_009.92', DATA2 + i, struct.unpack_from('<I', d2, i)[0]) for i in range(0, len(d2), 4)]
    # hooks
    ms = fs_read('/MAIN_SEL.BIN'); ex = fs_read('/SCES_009.92')
    w_ms = lambda a: struct.unpack_from('<I', ms, a - OVL)[0]; w_ex = lambda a: struct.unpack_from('<I', ex, a - EXE_BASE)[0]
    for sites, fn, lab in ((NAV_H, NAV, 'navH'), (NAV_B, NAV, 'navB'), (FACE_H, FACE, 'fwH'), (NAME_H, NAME, 'nwH'), (FACE_B, FACE, 'fwB'), (NAME_B, NAME, 'nwB'),
                           (NAV_H2, NAV, 'navH2'), (NAME_H2, NAME, 'nwH2')):
        for a in sites: assert w_ms(a) == J(3, fn), hex(a); P.append(('/MAIN_SEL.BIN', a, J(3, lb[lab])))
    for a, r, x in BARS:
        assert w_ms(a) == 0x00021080 and w_ms(a + 4) & 0xffe0ffff == 0x00401021, hex(a); P.append(('/MAIN_SEL.BIN', a, J(3, lb[f'bar_{r}_{x}'])))
    for a, o in LOAD_SITES: assert w_ex(a) == J(3, ENQ), hex(a); P.append(('/SCES_009.92', a, J(3, lb['ld%x' % o])))
    assert w_ms(CINIT) == 0x3c028005 and w_ms(CCOM) == 0x3c018005
    P += [('/MAIN_SEL.BIN', CINIT, J(2, lb['cinit'])), ('/MAIN_SEL.BIN', CINIT + 4, 0x3c028005),
          ('/MAIN_SEL.BIN', CCOM, J(2, lb['ccom'])), ('/MAIN_SEL.BIN', CCOM + 4, 0x3c018005)]
    for f, a in RACE.items(): P.append((f, a - 12, J(3, lb['rpv' if f == '/VS.BIN' else 'rp_' + race_regs[f]])))
    for a in MDL_SITES: assert w_ms(a) == J(3, FN_MDL), hex(a); P.append(('/MAIN_SEL.BIN', a, J(3, lb['mdl'])))
    for a in WEAR_UPLOADS: assert w_ms(a) == J(3, UPLOAD), hex(a); P.append(('/MAIN_SEL.BIN', a, J(3, lb['wup'])))
    assert w_ex(PLAY) == 0x3c028005 and w_ex(PLAY + 4) == 0x944208a8          # lui v0, 0x8005 / lhu v0, 0x8a8(v0)
    P += [('/SCES_009.92', PLAY, J(2, lb['vp'])), ('/SCES_009.92', PLAY + 4, 0)]
    return P


# ---------------------------------------------------------------------------------------------------- package
SOURCES = ['/DATA/CHR/PLAYER0.DAT', '/DATA/CHR/ENEMY1.FBD', '/DATA/CHR/ENEMY2.FBD', '/DATA/CHR/FR/FBD/FRM1_00.FBD']


def _segments(d, srcs, mn=12):
    """bytes -> [[0, len, disc address] copied from the player's disc | [1, hex]] (srcs: [(disc address, bytes)])"""
    out = []; i = 0; lit = bytearray()
    while i < len(d):
        best = None
        if i + mn <= len(d):
            for base, s in srcs:
                k = s.find(d[i:i + mn])
                if k < 0: continue
                n = mn
                while i + n < len(d) and k + n < len(s) and d[i + n] == s[k + n]: n += 1
                if best is None or n > best[1]: best = (base + k, n)
        if best is None: lit.append(d[i]); i += 1; continue
        if lit: out.append([1, lit.hex()]); lit = bytearray()
        out.append([0, best[1], best[0]]); i += best[1]
    if lit: out.append([1, lit.hex()])
    return out


def _split(segs, n):
    """cut a segment list into chunks of n bytes"""
    out = []; cur = []; room = n
    for s in segs:
        if s[0] == 0: ln, src = s[1], s[2]
        else: data = bytes.fromhex(s[1]); ln = len(data)
        o = 0
        while o < ln:
            m = min(room, ln - o)
            cur.append([0, m, src + o] if s[0] == 0 else [1, data[o:o + m].hex()])
            o += m; room -= m
            if room == 0: out.append(cur); cur = []; room = n
    if cur: cur.append([1, bytes(room).hex()]); out.append(cur)
    return out


def ops(disc):
    """the operations of the mod, relative to the player's original disc"""
    rd = disc.read_file
    import vs2p
    fl = files(rd); blobs = fl + [bytes(M_SIZE)] * 3 + [vs2p.to_p2(fl[2 * k]) for k in range(3)]; first, placed = layout(blobs)
    out = []
    for f, a, new in patches(rd, placed):
        o = (a - EXE_BASE) if f == '/SCES_009.92' else (a - OVL)
        out.append(['w', f, o, struct.unpack_from('<I', rd(f), o)[0], new])
    for k, rows in enumerate(name_tags()):
        for y in range(32): out.append(['b', FBD, vram_off(NAME_X + 12 * k, NAME_Y + y), rows[y].hex()])
    out.append(face_op())
    out.append(icons_op())
    import crewrank      # rankings: own rider numbers in the records, heads on the ranking screens
    out += crewrank.ops(disc, ALIASV, BASEV, MODESV, FBD, ICON_X, ICON_Y, ICON_CLUT_X, ICON_CLUT_Y, [STRIP_ORDER.index(c) for c in 'JNK'])
    ml = disc.files[MOVIE][0]; out.append(['rec', MOVIE, ml, (first - ml) * 2048])
    srcs = [(disc.files[p][0] * 2048, rd(p)) for p in SOURCES]
    import bundle, cpurider
    p0 = rd(SOURCES[0]); p0a = srcs[0][0]
    for j, (lba, b) in enumerate(placed):
        if 6 <= j < 9:     # menu model: built by the patcher from the ending model and ENDING.FBD
            out.append(['crewmenu', lba, ENDING_MODELS[j - 6], ENDING_FBD, menu_params(j - 6)]); continue
        if j % 2 == 0 or j >= 9:     # model (player 1, or player 2's copy): from the CPU model in PLAYER0.DAT, recomputed bytes only
            src = bundle.parse(p0)[cpurider.CPU[NAMES[j // 2 if j < 9 else j - 9]][0]]; o = p0.find(src); assert o >= 0 and len(src) == len(b)
            segs = []; i = 0
            while i < len(b):
                k = i; same = b[i] == src[i]
                while k < len(b) and (b[k] == src[k]) == same: k += 1
                segs.append([0, k - i, p0a + o + i] if same else [1, b[i:k].hex()]); i = k
        else: segs = _segments(b, srcs)
        chunks = _split(segs, 2048)
        for k, c in enumerate(chunks):
            out.append(['sec', lba + k, (bytes([0, 0, 0x89 if k == len(chunks) - 1 else 0x08, 0]) * 2).hex(), c])
    return out


# ---------------------------------------------------------------------------------------------------- menu models
# The BOARDER screen shows a 3D model of the rider (TITLE/CHR.DAT: one TMD of 13 parts per rider, 8-bit texture in a
# 64x256 VRAM column per rider: Yaggi x 512, Jin 576, Cindy 640, palettes on rows 476 + 2 rider). The ending of the
# game has the same kind of models for the CPU riders (ENDING/S_CHR/ED_CHR41/51/61.DAT: TMD of 16 parts = the 13 of
# the menu with the hands apart and the board; texture in ENDING/ENDING.FBD). menu_chunk() turns one into a menu
# model (hands joined to the forearms, board left out, 3040 lower, texture moved to the base rider's column),
# already "mapped" (absolute pointers) for MENU_BUF where the game code loads it when the rider is selected.
ENDING_MODELS = ['/ENDING/S_CHR/ED_CHR41.DAT', '/ENDING/S_CHR/ED_CHR51.DAT', '/ENDING/S_CHR/ED_CHR61.DAT']
ENDING_FBD = '/ENDING/ENDING.FBD'
MENU_BUF = 0x801C2000; MENU_SAVE = 0x801D2000          # free RAM in the menu (left-over copy of MAIN_SEL.FBD)
M_CLUT = 0x7800; M_IMG = 0x7A00; M_MAGIC = 0xFA00; M_SIZE = 0xFA04
MENU_COL = [512, 576, 640]                              # VRAM column of the base rider (Yaggi, Jin, Cindy)
MENU_CLUT_Y = [476, 478, 480]
Y_SHIFT = 3040
# words of a TMD primitive holding indices: mode -> [(word, half, 'v' vertex | 'n' normal)]
TMD_IDX = {0x34: [(4, 0, 'n'), (4, 1, 'v'), (5, 0, 'n'), (5, 1, 'v'), (6, 0, 'n'), (6, 1, 'v')],
           0x3C: [(5, 0, 'n'), (5, 1, 'v'), (6, 0, 'n'), (6, 1, 'v'), (7, 0, 'n'), (7, 1, 'v'), (8, 0, 'n'), (8, 1, 'v')],
           0x30: [(2, 0, 'n'), (2, 1, 'v'), (3, 0, 'n'), (3, 1, 'v'), (4, 0, 'n'), (4, 1, 'v')],
           0x38: [(2, 0, 'n'), (2, 1, 'v'), (3, 0, 'n'), (3, 1, 'v'), (4, 0, 'n'), (4, 1, 'v'), (5, 0, 'n'), (5, 1, 'v')],
           0x20: [(2, 0, 'n'), (2, 1, 'v'), (3, 0, 'v'), (3, 1, 'v')],
           0x28: [(2, 0, 'n'), (2, 1, 'v'), (3, 0, 'v'), (3, 1, 'v'), (4, 0, 'v')],
           0x24: [(4, 0, 'n'), (4, 1, 'v'), (5, 0, 'v'), (5, 1, 'v')],
           0x2C: [(5, 0, 'n'), (5, 1, 'v'), (6, 0, 'v'), (6, 1, 'v'), (7, 0, 'v')],
           0x25: [(5, 0, 'v'), (5, 1, 'v'), (6, 0, 'v')]}         # (flag 1: no light, no normal)
MENU_PARTS = [[0], [1], [2], [3], [4, 5], [6], [7, 8], [9], [10], [11], [12], [13], [14]]   # ending parts (board out)


def menu_params(k, dest=MENU_BUF):
    (px, py), (cx, cy) = END_TEX[k]
    return {'dest': dest, 'col': MENU_COL[k], 'cly': MENU_CLUT_Y[k], 'src': [px, py, cx, cy], 'yshift': Y_SHIFT,
            'parts': MENU_PARTS, 'idx': {str(m): v for m, v in TMD_IDX.items()}, 'clut_off': M_CLUT, 'img_off': M_IMG,
            'magic_off': M_MAGIC, 'size': M_SIZE, 'magic': MENU_MAGIC + k + 1}


def menu_chunk(archive, fbd, k, dest=MENU_BUF):
    import modular
    return modular.crew_menu_chunk(archive, fbd, menu_params(k, dest))


MENU_MAGIC = 0x4D575243   # 'CRWM' (+ 1..3)
END_TEX = [((512, 256), (768, 485)), ((576, 256), (768, 486)), ((640, 256), (768, 487))]   # Jicchi, Nick, Kelly in ENDING.FBD



# ---------------------------------------------------------------------------------------------------- rider strip
# BOARDER screen: a row of 16x16 heads, in the order of the list (YAGGI JIN CINDY IRIN JICCHI NICK KELLY BOSS GRAY
# SNOWMAN), grey for the riders not available. The heads are made by the patcher from the menu portraits
# (modular.icons_op) into the free VRAM of the menu: x 960 + 4 i, y 324 (4-bit), palettes at x 928 rows 340/341, grey
# 342/343. Drawn by strip() from the BOARDER screen's portrait wrapper, with the game's own name-tag function.
STRIP_ORDER = [0, 1, 2, 3, 'J', 'N', 'K', 4, 5, 6]
ICON_X, ICON_Y, ICON_CLUT_X, ICON_CLUT_Y = 960, 324, 928, 340
STRIP_X, STRIP_Y, STRIP_DX, STRIP_DY = 16 - 160, 46 - 120, 18, 17   # first head (screen x 16, y 46, under the title; the menu draws from the centre), steps
UNLOCK_ALL = (0x80063EA8, 0x2403007F)                    # the 'unlock' mod's word: every boarder selectable
FACE_TPX = [0x140] * 6 + [0x180]; FACE_U = [0, 0x40, 0x40, 0, 0x40, 0, 0]; FACE_V = [0x50, 0x50, 0xA0, 0xA0, 0, 0, 0xB0]
FACE_CY = [0x1C8, 0x1C9, 0x1CB, 0x1CA, 0x1CD, 0x1CC, 0x1CE]          # tables of func_80063324 (menu portraits)


def icons_op():
    src = []
    for r in STRIP_ORDER:
        if isinstance(r, int): src.append([FACE_TPX[r] + FACE_U[r] // 2, 256 + FACE_V[r] + 4, 64, 64, 0x300, FACE_CY[r], 256])
        else: k = 'JNK'.index(r); src.append([FACE_X + 32 * k, FACE_Y, 64, 64, CLUT_X, CLUT_Y + k, NCOL])
    return ['icons', FBD, {'src': src, 'dest': [ICON_X, ICON_Y], 'clut': [ICON_CLUT_X, ICON_CLUT_Y]}]
