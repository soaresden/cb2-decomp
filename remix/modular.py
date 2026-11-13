#!/usr/bin/env python3
"""Modular Remix: every mod can be switched on or off.

generate(): splits the Remix (remix.patches() + the data steps of remix.apply(), read back from a reference build)
            into features, each a list of operations relative to the ORIGINAL disc -> package (dict, JSON-able).
apply():    builds the user-data sectors for any set of features, from the player's own original disc.
With every feature on, apply() gives exactly the reference build; with none, the original disc.

Operations
  ['w', file, offset, old, new]      32-bit word of a file (old checked)
  ['b', file, offset, hexbytes]      bytes of a file
  ['bs', file, offset, segs]         bytes of a file: [[0, len, src] copied from the original file at src | [1, hex]]
  ['append', file, hexbytes]         bytes added at the end of a file (MAIN_SEL grows: it then moves, see below)
  ['px4', file, hdr, W, clear, tr, blits]  4-bit image: rectangles of the original copied (see px4)
  ['rec', path, lba, size]           directory record of a file
  ['sec', lba, subheader_hex, ops]   whole sector: ops = [[0, len, src_addr] copy from the original disc | [1, hex]]
"""
import base64, gzip, json, math, os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cb2disc

# ==== embeddable part (batocera/mkpygame.py copies from here to the end, without the __main__ block) ====
EXE, OVL = 0x80010000, 0x8005AEA8
FEATURES = [   # id, French name, English name, description FR, description EN
    ('unlock', 'Tout débloqué', 'Everything unlocked',
     'Pistes, riders, planches SPECIAL, miroir, hard et récompenses débloqués dès une nouvelle partie ; tous les riders sélectionnables même avec une ancienne sauvegarde.',
     'Tracks, riders, SPECIAL boards, mirror, hard and awards unlocked on a new game; every rider selectable even with an old save.'),
    ('special', 'Planches SPECIAL partout', 'SPECIAL boards everywhere',
     'Les planches SPECIAL sont toujours proposées, en compétition aussi.', 'SPECIAL boards always offered, in competition too.'),
    ('hardmirror', 'Hard + Mirror', 'Hard + Mirror',
     'L1 + R1 + X sur Competition : hard et miroir en même temps.', 'L1 + R1 + X on Competition: hard and mirror together.'),
    ('riders', 'Boss, Gray et Snowman en compétition', 'Boss, Gray and Snowman in competition',
     '7 riders en championnat, avec leurs noms dans les résultats, la voix de Boss (fin du film d’intro raccourcie) et les correctifs de ciel et de son. Le CPU Boss devient Jicchi.',
     '7 riders in competition, with their names in the results, Boss’s own voice (end of the intro movie cut) and the sky and sound fixes. The CPU Boss becomes Jicchi.'),
    ('outfits', 'Tenues cachées de Cindy et Irin', 'Cindy and Irin hidden outfits',
     'Tenues cachées en vestes 4 à 6 sur l’écran WEAR, avec aperçu dans le menu, dans tous les modes (fin de la vidéo d’info raccourcie).',
     'Hidden outfits as jackets 4 to 6 on the WEAR screen, previewed in the menu, in every mode (end of the info movie cut).'),
    ('max', 'Stats MAX', 'MAX stats',
     'R1 sur l’écran BOARDER : toutes les stats au maximum, « MAX » sous le portrait. Écran BOARD : ligne MAX sous SPECIAL, avec les 21 motifs.', 'R1 on the BOARDER screen: every stat maxed, “MAX” under the portrait. BOARD screen: a MAX line under SPECIAL, with all 21 designs.'),
    ('air', 'Figures en l’air', 'Air control',
     'Figures comme d’habitude ; en l’air, la croix dans le sens de la rotation l’accélère (×1,5), à l’envers la freine (×0,5) pour bien atterrir. Carré = rotations ×2, grabs « X to Y » en gardant R1.',
     'Tricks as usual; in the air, the d-pad in the rotation’s direction speeds it up (x1.5), the other way slows it (x0.5) to land right. Square = rotations x2, “X to Y” grabs while holding R1.'),
    ('ramming', 'Chocs en Boarder Cross', 'Boarder Cross ramming',
     'Fonce dans un adversaire : le plus rapide des deux reste debout.', 'Ram an opponent: the faster of the two stays up.'),
    ('bam', 'Big Air Master', 'Big Air Master',
     'Touches toujours affichées, figures suivantes (NEXT) à droite, et Exit dans la pause termine la session avec ta note et le classement.', 'Keys always shown, the next tricks (NEXT) on the right, and Exit in the pause menu ends the session with your grade and the ranking.'),
    ('progress', 'Progression dans le jeu', 'In-game progress',
     'SELECT maintenu sur l’écran des modes : riders cachés, Mirror, Hard, Hard + Mirror, planches SPECIAL, trophées et pourcentage.',
     'Hold SELECT on the mode select screen: hidden riders, Mirror, Hard, Hard + Mirror, SPECIAL boards, trophies and percentage.'),
    ('lift', 'Arrivée express en Free Style', 'Quick finish in Free Style',
     'À l’arrivée, le temps compte comme d’habitude (classement, records, trophées) mais sans célébration ni replay : classement, START, résultats avec ton temps, X = RETRY et tu repars aussitôt d’en haut.',
     'At the finish the run counts as usual (ranking, records, trophies) but without the celebration and the replay: ranking, START, results with your time, X = RETRY and you start again from the top.'),
    ('skipq', 'Qualifications au choix', 'Optional qualifying',
     'Sur l’écran « 1st STAGE » : START = jouer les qualifications, SELECT + START = les passer et partir 4e sur 8, au milieu du départ en handicap du Boarder Cross.',
     'On the “1st STAGE” screen: START = play the qualifying, SELECT + START = skip it and start 4th of 8, in the middle of the Boarder Cross handicap start.'),
    ('crew', 'Jicchi, Nick et Kelly jouables', 'Jicchi, Nick and Kelly playable',
     'Les trois riders de l’ordinateur rejoignent l’écran BOARDER après Irin, avec leur portrait (tiré de la vidéo de la Compétition), leur modèle 3D (celui de la fin du jeu dans le menu, celui des courses en piste) et leurs stats de course ; leur voix est celle du rider de base, plus grave (Nick, Jicchi) ou plus aiguë (Kelly). Free Style, Big Air, Halfpipe et Board Park (Free Style à 2 joueurs compris, pas en Compétition). Ils sont la récompense des 100 % (écran CONGRATULATIONS) ; avec « Tout débloqué », ils sont là d’office. Fin du film d’intro raccourcie d’environ une seconde.',
     'The three CPU riders join the BOARDER screen after Irin, with their portrait (from the Competition movie), their 3D model (the ending’s in the menu, the race one on the slopes) and their race stats; their voice is the base rider’s, deeper (Nick, Jicchi) or higher (Kelly). Free Style, Big Air, Halfpipe and Board Park (2-player Free Style included, not in Competition). They are the 100 % reward (CONGRATULATIONS screen); with “Everything unlocked” they are there from the start. End of the intro movie about one second shorter.'),
    ('rear', 'Vue arrière (Rond)', 'Rear view (Circle)',
     'En course, Rond maintenu : la caméra passe devant ton rider et regarde derrière lui (pour voir qui te suit).',
     'In a race, hold Circle: the camera moves in front of your rider and looks back (to see who is following).'),
    ('hplive', 'Notes du half-pipe en direct', 'Live half-pipe marks',
     'En half-pipe, les cinq notes des juges (figures, amplitude, réception, rotation, mérite technique) et le total s’affichent en haut à droite pendant le run, et montent à chaque figure.',
     'In the half-pipe, the five judges’ marks (manoeuvres, amplitude, landing, rotation, technical merit) and the total are shown at the top right during the run, and go up with each trick.'),
    ('options', 'Options dans le jeu', 'In-game options',
     'Sur l’écran de choix du mode, maintiens R1 : le panneau REMIX OPTIONS s’affiche ; L1 descend d’une ligne, R2 active ou coupe : vue arrière, notes du half-pipe en direct, annonces de déblocage, figures en l’air, chocs en Boarder Cross, et écran large 16:9 (coupé au départ : à utiliser avec l’image étirée en 16:9 et sans le « widescreen hack » de l’émulateur). Le réglage est gardé dans ta sauvegarde.',
     'On the mode select screen, hold R1: the REMIX OPTIONS panel shows; L1 moves down a line, R2 switches it on or off: rear view, live half-pipe marks, unlock announcements, air control, Boarder Cross ramming, and widescreen 16:9 (off at first: use it with the picture stretched to 16:9 and without the emulator’s widescreen hack). The setting is kept in your save.'),
    ('news', 'Annonces de déblocage', 'Unlock announcements',
     'De retour au menu après une course, un bandeau qui brille annonce ce que tu viens de gagner : Boss, Gray, Snowman, planche SPECIAL, Mirror, Hard, nouvelles pistes, trophée, et les 100 % (CONGRATULATIONS, avec Jicchi, Nick et Kelly si leur mod est coché).',
     'Back in the menu after a race, a shining banner tells what you just won: Boss, Gray, Snowman, SPECIAL board, Mirror, Hard, new courses, trophy, and the 100 % (CONGRATULATIONS, with Jicchi, Nick and Kelly if their mod is on).'),
]
INPUT = 'input'   # shared pad hook (needed by 'max' and 'air')
BRAND = 'brand'   # "REMIX" on the title screen: with any mod (already inside the moved title files when 'riders' is on)

def _r(*xs): return xs
EXE_MAP = [   # (lo, hi, feature) in the executable
    (0x8001B594, 0x8001B594, INPUT), (0x8004F980, 0x8004F99F, INPUT), (0x8004FA10, 0x8004FBFF, INPUT), (0x8004F9A0, 0x8004F9DF, INPUT),
    (0x8004F8CC, 0x8004F8FF, INPUT), (0x8002957C, 0x8002979F, INPUT), (0x8002A030, 0x8002A180, INPUT),
    (0x8002815C, 0x80028413, 'max'), (0x8001228C, 0x8001228C, 'max'), (0x8001B774, 0x8001B77B, INPUT), (0x8001B77C, 0x8001BA6F, 'max'),
    (0x80028BF4, 0x80028D3C, 'ramming'),
    (0x8004F878, 0x8004F89F, 'hardmirror'),
    (0x8004F800, 0x8004F877, 'riders'), (0x8004F8A0, 0x8004F8CB, 'riders'), (0x8004F900, 0x8004F91F, 'riders'), (0x8004F940, 0x8004F96B, 'riders'),
    (0x8001CEFC, 0x8001CF00, 'riders'), (0x8001CFE0, 0x8001CFE0, 'riders'), (0x8001D078, 0x8001D078, 'riders'), (0x8001D104, 0x8001D10C, 'riders'),
    (0x8004F920, 0x8004F93F, 'outfits'), (0x8004F96C, 0x8004F97F, 'outfits'), (0x8004F9E0, 0x8004F9EF, 'outfits'),
    (0x8001D140, 0x8001D140, 'outfits'), (0x8001003C, 0x8001003C, 'outfits'), (0x800100B8, 0x800100B8, 'outfits'),
    (0x800100B4, 0x800100B4, 'progress'),
    (0x800291CC, 0x8002934B, 'skipq'), (0x8002934C, 0x8002936F, 'bam'), (0x80029370, 0x800293F7, 'air'),
]
MODE_MAP = [(0x800643B4, 0x800643B4, 'progress'), (0x800832C8, 0x800836A8, 'progress')]
MS_MAP = [*[(a, a, 'max') for a in (0x8006E0A8, 0x8006E0AC, 0x8006E120, 0x8006E124, 0x8006E1CC, 0x8006D478, 0x8006DC98, 0x8006E4B8, 0x8006D614, 0x8006D618,
                                    0x8006DEA0, 0x8006DEA4, 0x8006E654, 0x8006E658, 0x8006B544, 0x8006BCF4, 0x8006C964, 0x8006D38C, 0x8006DBB8, 0x8006E3CC, 0x8006BA80, 0x8006C0C0, 0x8006D42C, 0x8006D430, 0x8006DC58, 0x8006DC5C, 0x8006E46C, 0x8006E470)],
          (0x8006B68C, 0x8006B68C, 'max'), (0x8006BE3C, 0x8006BE3C, 'max'), (0x8006CAAC, 0x8006CAAC, 'max'), (0x80063EA8, 0x80063EA8, 'unlock'), (0x8005B0C4, 0x8005B0C4, 'special'), (0x80069D00, 0x8006C910, 'special'),
          (0x800614B8, 0x800614B8, 'max'), (0x800626E4, 0x800626E4, 'max'), (0x80063FC8, 0x80063FCC, 'riders'), (0x80064044, 0x80064044, 'riders'),
          (0x800605B4, 0x80062180, 'outfits'), (0x800640EC, 0x80064210, 'outfits')]
SBC_MAP = {'/FREE.BIN': [(0x8005D5A4, 0x8005D5A4, 'lift')],
           '/SBC1.BIN': [(0x8005B058, 0x8005B058, 'skipq'), (0x800832DC, 0x800832DC, 'riders'), (0x8008D8C8, 0x8008D910, 'riders')],
           '/SBC2.BIN': [(0x8005FF70, 0x8005FF70, 'ramming'), (0x80064D70, 0x80064D70, 'riders'), (0x800666EC, 0x800666F0, 'riders'),
                         (0x80066CB4, 0x80066CB8, 'riders'), (0x80090300, 0x80090420, 'riders'), (0x800847AC, 0x800847AC, 'riders'), (0x800902A8, 0x800902F0, 'riders')],
           '/TM.BIN': [(0x8005CCC0, 0x8005CCC0, 'bam'), (0x80075738, 0x80075758, 'bam'), (0x80074CFC, 0x80074CFC, 'bam'), (0x80094F18, 0x80095538, 'bam')]}
MAXC = {('/SBC1.BIN', 0x80063F04), ('/SBC2.BIN', 0x80065BE4), ('/VS.BIN', 0x80064E08), ('/OMT.BIN', 0x80063C58), ('/BP.BIN', 0x80063B1C),
        ('/HP.BIN', 0x80063D0C), ('/FREE.BIN', 0x8006465C), ('/TM.BIN', 0x80063C38), ('/COMB.BIN', 0x80064B88)}
RACE = {'/SBC1.BIN', '/SBC2.BIN', '/VS.BIN', '/OMT.BIN', '/BP.BIN', '/HP.BIN', '/FREE.BIN', '/TM.BIN', '/COMB.BIN'}

def classify(f, a):
    tables = {'/SCES_009.92': EXE_MAP, '/MAIN_SEL.BIN': MS_MAP, '/MODE_SEL.BIN': MODE_MAP}.get(f, []) + SBC_MAP.get(f, [])
    for lo, hi, feat in tables:
        if lo <= a <= hi: return feat
    if f == '/INIT.BIN': return 'unlock'
    if f == '/MODE_SEL.BIN': return 'hardmirror'
    if (f, a) in MAXC: return 'max'
    if f in RACE: return 'air'
    raise ValueError('mot du Remix sans mod : %s 0x%08X' % (f, a))

def file_off(f, a): return (a - EXE + 0x800) if f == '/SCES_009.92' else (a - OVL)

def records(disc):
    """path -> (sector lba, offset in the sector) of its directory record"""
    out = {}
    def walk(lba, size, path):
        for k in range(-(-size // 2048)):
            d = disc.user(lba + k); i = 0
            while i < 2048 and d[i]:
                L = d[i]; nl = d[i + 32]; name = d[i + 33:i + 33 + nl]
                if name not in (b'\0', b'\1'):
                    p = path + '/' + name.decode('latin1').split(';')[0]; out[p] = (lba + k, i)
                    if d[i + 25] & 2: walk(struct.unpack_from('<I', d, i + 2)[0], struct.unpack_from('<I', d, i + 10)[0], p)
                i += L
    pvd = disc.user(16); walk(struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0], '')
    return out

def segments(d, orig, mn=12):
    """bytes -> [[0, len, offset in the original file] (copy) | [1, hex] (new bytes)]: game bytes are never stored"""
    out = []; i = 0; lit = bytearray()
    while i < len(d):
        k = orig.find(d[i:i + mn]) if i + mn <= len(d) else -1
        if k < 0: lit.append(d[i]); i += 1; continue
        n = mn
        while i + n < len(d) and k + n < len(orig) and d[i + n] == orig[k + n]: n += 1
        if lit: out.append([1, lit.hex()]); lit = bytearray()
        out.append([0, n, k]); i += n
    if lit: out.append([1, lit.hex()])
    return out

# ------------------------------------------------------------------------------------------------ generator
def generate(pal_chd, ref_chd, pal_fs, delta_gz):
    os.environ['CB2_FS'] = pal_fs
    import remix
    O, R = cb2disc.Disc(pal_chd), cb2disc.Disc(ref_chd)
    pkg = {'format': 'cb2mods', 'version': open(os.path.join(ROOT, 'remix', 'VERSION')).read().strip(),
           'exe_crc': None, 'features': [], 'ops': {k[0]: [] for k in FEATURES}}
    pkg['ops'][INPUT] = []; pkg['ops']['input_noair'] = []; pkg['ops'][BRAND] = []
    exe = O.read_file('/SCES_009.92'); import zlib; pkg['exe_crc'] = zlib.crc32(exe); pkg['exe_size'] = len(exe)
    for fid, nfr, nen, dfr, den in FEATURES: pkg['features'].append({'id': fid, 'fr': nfr, 'en': nen, 'dfr': dfr, 'den': den})
    words = {}; grown_files = set()
    for f, a, old, new in remix.patches():
        feat = classify(f, a); o = file_off(f, a)
        cur = struct.unpack_from('<I', O.read_file(f), o)[0]
        pkg['ops'][feat].append(['w', f, o, cur, new]); words[(f, o)] = new
    # without 'air', the shared pad code skips the air-control part (rm / inj): its jumps to rm return to the game
    RMJ = (2 << 26) | ((0x8004FB28 >> 2) & 0x3ffffff); BACK = (2 << 26) | ((0x8001B5A0 >> 2) & 0x3ffffff)
    for op in pkg['ops'][INPUT]:
        if op[4] == RMJ: pkg['ops']['input_noair'].append(['w', op[1], op[2], RMJ, BACK])
    # data steps, read back from the reference build: files that stay in place
    feat_of_file = {'/DATA/CHR/ENEMY1.FBD': 'riders', '/DATA/EFFECT/EFCT_SBC.FBD': 'riders'}
    # sectors reused by remix.layout() (unused files, duplicate course, free tail): taken as whole sectors below
    F = O.files; L = set(range(F['/DATA/CRS/VS/VS_CS1.DAT'][0], F['/DATA/CRS/VS/VS_CS1.DAT'][0] + 161))
    L |= set(range(F['/ENDING/S_CHR/ED_CHRCG.DAT'][0], F['/ETC'][0])) | set(range(F['/ETC'][0] + 1, F['/LOAD'][0])) | set(range(65645, 65795))
    def span(l, sz): return set(range(l, l + -(-sz // 2048)))
    for p, (lba, size, isdir) in sorted(O.files.items()):
        if isdir or p.startswith('/CDDA/') or p.startswith('/MOVIE/') or p in ('/MAIN_SEL.BIN', '/MODE_SEL.BIN'): continue
        rl, rs, _ = R.files[p]
        grown = rl == lba and rs > size and -(-rs // 2048) == -(-size // 2048)
        if ((rl, rs) != (lba, size) and not grown) or span(lba, size) & L: continue   # moved / overwritten files: sectors below
        if grown:
            tail = R.read_file(p)[size:]; base = (EXE - 0x800) if p == '/SCES_009.92' else OVL
            gf = classify(p, base + size); pkg['ops'][gf].append(['append', p, tail.hex()]); pkg['ops'][gf].append(['rec', p, rl, rs])
            grown_files.add(p)
        a = bytearray(O.read_file(p)); b = R.read_file(p)[:size]
        for (f, o), w in words.items():
            if f == p: struct.pack_into('<I', a, o, w)
        if a == b: continue
        if p == '/TITLE/MODE_SEL.FBD':
            import remix as _rx
            c = bytearray(O.read_file(p)); px4(c, _rx.HM_LABEL); assert bytes(c) == b, 'étiquette H+M différente'
            pkg['ops']['hardmirror'].append(list(_rx.HM_LABEL)); continue
        i = 0
        while i < len(a):
            if a[i] == b[i]: i += 1; continue
            j = i
            while j < len(a) and (a[j] != b[j] or (j + 8 < len(a) and a[j:j + 8] != b[j:j + 8])): j += 1
            feat = feat_of_file.get(p) or classify(p, (i + EXE - 0x800) if p == '/SCES_009.92' else i + OVL)
            pkg['ops'][feat].append(['bs', p, i, segments(bytes(b[i:j]), bytes(O.read_file(p)))]); i = j
    # title screen (title.py): drawn into the files at their original place; with 'riders' they are moved and the
    # moved copies (sectors below) already carry the word
    import title as _tt
    for p in _tt.FILES:
        a = O.read_file(p); b = _tt.draw(a); i = 0
        while i < len(a):
            if a[i] == b[i]: i += 1; continue
            j = i
            while j < len(a) and (a[j] != b[j] or (j + 8 < len(a) and a[j:j + 8] != b[j:j + 8])): j += 1
            pkg['ops'][BRAND].append(['bs', p, i, segments(bytes(b[i:j]), bytes(a))]); i = j
    # MODE_SEL moved (progress page, one more sector): words of the other mods are in pkg, the page is appended
    if R.files['/MODE_SEL.BIN'][0] != O.files['/MODE_SEL.BIN'][0]:
        a = bytearray(O.read_file('/MODE_SEL.BIN')); r = R.read_file('/MODE_SEL.BIN')
        for (f, o), w in words.items():
            if f == '/MODE_SEL.BIN': struct.pack_into('<I', a, o, w)
        assert bytes(a) == r[:len(a)], 'MODE_SEL : différences inattendues'
        pkg['ops']['progress'].append(['append', '/MODE_SEL.BIN', r[len(a):].hex()])
        grown_files.add('/MODE_SEL.BIN'); grown_files.add('/MOVIE/STAFFE.STR')
        ml, msz, _ = R.files['/MODE_SEL.BIN']; moved_extra = set(range(ml, ml + -(-msz // 2048)))
    else: moved_extra = set()
    # MAIN_SEL: other mods' words are in pkg already; the outfits block is appended
    ms_o = O.read_file('/MAIN_SEL.BIN'); ms_r = R.read_file('/MAIN_SEL.BIN')
    a = bytearray(ms_o)
    for (f, o), w in words.items():
        if f == '/MAIN_SEL.BIN' and o + 4 <= len(a): struct.pack_into('<I', a, o, w)
    assert bytes(a) == ms_r[:len(a)], 'MAIN_SEL : différences inattendues'
    pkg['ops']['outfits'].append(['append', '/MAIN_SEL.BIN', ms_r[len(a):].hex()])
    # directory records (MAIN_SEL / SBCMOVE are computed by apply() for 'outfits')
    for p in R.files:
        if p in ('/MAIN_SEL.BIN', '/MOVIE/SBCMOVE.STR'): continue
        if p in O.files and O.files[p][:2] != R.files[p][:2] and p not in grown_files:
            pkg['ops']['riders'].append(['rec', p, R.files[p][0], R.files[p][1]])
    # Jicchi, Nick and Kelly: computed here (not in the reference build), portraits drawn by the patcher itself
    import crew as _cw
    pkg['ops']['crew'] = _cw.ops(O)
    import rear as _rv
    pkg['ops']['rear'] = _rv.ops(O)
    import news as _nw
    pkg['ops']['news'] = _nw.ops(O)
    import hplive as _hl
    pkg['ops']['hplive'] = _hl.ops(O)
    import options as _op
    pkg['ops']['options'] = _op.ops(O)
    # sectors: everything else the reference changes (new blobs in free sectors, Boss voice bank at the end of the
    # intro movie, moved small files) -> 'riders', taken from the published delta (copies from the player's disc)
    P = gzip.decompress(open(delta_gz, 'rb').read()); n = struct.unpack_from('<I', P, 16)[0]; o = 20; entries = {}
    while n:
        lba = struct.unpack_from('<I', P, o)[0]; sub = P[o + 4:o + 12]; nops = struct.unpack_from('<H', P, o + 12)[0]; o += 14; ops = []
        for _ in range(nops):
            k, ln = P[o], struct.unpack_from('<H', P, o + 1)[0]; o += 3
            if k == 0: ops.append([0, ln, struct.unpack_from('<I', P, o)[0]]); o += 4
            else: ops.append([1, P[o:o + ln].hex()]); o += ln
        entries[lba] = (sub.hex(), ops); n -= 1
    covered = set()
    for p, (lba, size, isdir) in O.files.items():           # sectors of files rebuilt by apply()
        if isdir or p.startswith('/CDDA/'): continue
        if (R.files.get(p, (None, None))[:2] == (lba, size) or p in grown_files) and not span(lba, size) & L: covered |= span(lba, size)
    rec = records(O); covered |= {s for s, _ in rec.values()}
    ms_l, ms_s, _ = R.files['/MAIN_SEL.BIN']; covered |= set(range(ms_l, ms_l + -(-ms_s // 2048))) | moved_extra
    for lba, (sub, ops) in sorted(entries.items()):
        if lba not in covered: pkg['ops']['riders'].append(['sec', lba, sub, ops])
    return pkg

# ------------------------------------------------------------------------------------------------ engine
def apply(disc, pkg, feats, log=lambda m: None):
    """-> {lba: (subheader 8 bytes, user data 2048 bytes)} for cb2disc.write_patched / compose_soundtrack"""
    import zlib
    exe = disc.read_file('/SCES_009.92')
    if len(exe) != pkg['exe_size'] or zlib.crc32(exe) != pkg['exe_crc']: raise cb2disc.SourceError("ce disque n'est pas le Cool Boarders 2 (PAL) d'origine")
    feats = [f for f in pkg['ops'] if f in feats]
    if 'max' in feats or 'air' in feats: feats.append(INPUT)
    if INPUT in feats and 'air' not in feats: feats.append('input_noair')
    if feats and 'riders' not in feats and pkg['ops'].get(BRAND): feats.append(BRAND)
    files = {}; recs = {}; secs = {}
    origs = {}
    def orig(p):
        if p not in origs: origs[p] = disc.read_file(p)
        return origs[p]
    def buf(p):
        if p not in files: files[p] = bytearray(orig(p))
        return files[p]
    order = [f for f in ('unlock', 'special', 'hardmirror', 'riders', 'crew', 'outfits', 'max', 'air', 'ramming', 'bam', 'progress', 'lift', 'skipq', 'rear', 'news', 'hplive', 'options', INPUT, 'input_noair', BRAND) if f in feats]
    for feat in order:
        for op in pkg['ops'][feat]:
            t = op[0]
            if t == 'w':
                b = buf(op[1]); cur = struct.unpack_from('<I', b, op[2])[0]
                if feat != 'input_noair' and cur != op[3]: raise ValueError('mot inattendu %s +0x%x' % (op[1], op[2]))
                struct.pack_into('<I', b, op[2], op[4])
            elif t == 'b': b = buf(op[1]); d = bytes.fromhex(op[3]); b[op[2]:op[2] + len(d)] = d
            elif t == 'bs':
                b = buf(op[1]); src = orig(op[1]); d = b''.join(src[x[2]:x[2] + x[1]] if x[0] == 0 else bytes.fromhex(x[1]) for x in op[3])
                b[op[2]:op[2] + len(d)] = d
            elif t == 'append': buf(op[1]).extend(bytes.fromhex(op[2]))
            elif t == 'px4': px4(buf(op[1]), op)
            elif t == 'rec': recs[op[1]] = (op[2], op[3])
            elif t == 'sec': secs[op[1]] = (bytes.fromhex(op[2]), op[3])
            elif t == 'face':
                ml_, ms_, _ = disc.files[op[2]]; face_op(buf(op[1]), lambda k: disc.user(ml_ + k), ms_ // 2048, op)
            elif t == 'icons': icons_op(buf(op[1]), op)
            elif t == 'fcopy':     # ['fcopy', src, dst, [[src off, dst off, len]...]]: bytes of a file as patched so far
                sb, db = buf(op[1]), buf(op[2])
                for so, do, n in op[3]: db[do:do + n] = sb[so:so + n]
            elif t == 'crewmenu':
                ch = crew_menu_chunk(orig(op[2]), orig(op[3]), op[4]); nch = -(-len(ch) // 2048); ch += bytes(nch * 2048 - len(ch))
                for k in range(nch):
                    secs[op[1] + k] = (bytes([0, 0, 0x89 if k == nch - 1 else 0x08, 0]) * 2, [[1, ch[k * 2048:(k + 1) * 2048].hex()]])
    mods = {}
    loc = {p: (l, s) for p, (l, s, d) in disc.files.items()}
    # MAIN_SEL grown by 'outfits': it moves to the last sectors of the info movie, which is cut accordingly
    ms = files.get('/MAIN_SEL.BIN')
    if ms is not None and len(ms) > loc['/MAIN_SEL.BIN'][1]:
        nms = -(-len(ms) // 2048); sl, ss = loc['/MOVIE/SBCMOVE.STR']; sn = ss // 2048; ml = sl + sn - nms
        recs['/MOVIE/SBCMOVE.STR'] = (sl, (sn - nms) * 2048); recs['/MAIN_SEL.BIN'] = (ml, len(ms))
        blob = bytes(ms) + bytes((-len(ms)) % 2048)
        for k in range(nms): mods[ml + k] = (bytes([0, 0, 0x89 if k == nms - 1 else 0x08, 0]) * 2, blob[k * 2048:(k + 1) * 2048])
        del files['/MAIN_SEL.BIN']
    md = files.get('/MODE_SEL.BIN')
    if md is not None and -(-len(md) // 2048) > -(-loc['/MODE_SEL.BIN'][1] // 2048):
        n2 = -(-len(md) // 2048); sl, ss = loc['/MOVIE/STAFFE.STR']; sn = ss // 2048; ml = sl + sn - n2
        recs['/MOVIE/STAFFE.STR'] = (sl, (sn - n2) * 2048); recs['/MODE_SEL.BIN'] = (ml, len(md))
        blob = bytes(md) + bytes((-len(md)) % 2048)
        for k in range(n2): mods[ml + k] = (bytes([0, 0, 0x89 if k == n2 - 1 else 0x08, 0]) * 2, blob[k * 2048:(k + 1) * 2048])
        del files['/MODE_SEL.BIN']
    for p, b in files.items():
        lba, size = loc[p]
        if len(b) != size:
            assert -(-len(b) // 2048) == -(-size // 2048), p
            recs.setdefault(p, (lba, len(b)))
        for k in range(-(-len(b) // 2048)):
            orig = disc.user(lba + k); new = bytes(b[k * 2048:(k + 1) * 2048]); new += orig[len(new):]
            if new != orig: mods[lba + k] = (disc.img.sector(lba + k)[16:24], new)
    for lba, (sub, ops) in secs.items():
        data = bytearray()
        for op in ops: data += disc.read_user(op[2], op[1]) if op[0] == 0 else bytes.fromhex(op[1])
        mods[lba] = (sub, bytes(data))
    if recs:
        where = records(disc)
        for p, (l, s) in recs.items():
            sl, so = where[p]
            m = mods.get(sl); d = bytearray(m[1] if m else disc.user(sl))
            d[so + 2:so + 10] = struct.pack('<I', l) + struct.pack('>I', l); d[so + 10:so + 18] = struct.pack('<I', s) + struct.pack('>I', s)
            mods[sl] = (m[0] if m else disc.img.sector(sl)[16:24], bytes(d))
    return mods

# ------------------------------------------------------------------------------------------------ PS1 movie frames (mod crew)
# STR (MDEC bitstream version 2) -> RGB, integer only: the site (disc.js) decodes exactly the same pixels.
MZZ = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21,
      28, 35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61,
      54, 47, 55, 62, 63]
MQT = [2, 16, 19, 22, 26, 27, 29, 34, 16, 16, 22, 24, 27, 29, 34, 37, 19, 22, 26, 27, 29, 34, 34, 38, 22, 22, 26, 27,
      29, 34, 37, 40, 22, 26, 27, 29, 32, 35, 40, 48, 26, 27, 29, 32, 35, 40, 48, 58, 26, 27, 29, 34, 38, 46, 56, 69,
      27, 29, 35, 38, 46, 56, 69, 83]   # natural order
# 1-D IDCT basis, (c(u) / 2) * cos((2x + 1) u pi / 16) * 2^13, rounded (MB[u * 8 + x])
MB = [2896, 2896, 2896, 2896, 2896, 2896, 2896, 2896, 4017, 3406, 2276, 799, -799, -2276, -3406, -4017,
     3784, 1567, -1567, -3784, -3784, -1567, 1567, 3784, 3406, -799, -4017, -2276, 2276, 4017, 799, -3406,
     2896, -2896, -2896, 2896, 2896, -2896, -2896, 2896, 2276, -4017, 799, 3406, -3406, -799, 4017, -2276,
     1567, -3784, 3784, -1567, -1567, 3784, -3784, 1567, 799, -2276, 3406, -4017, 4017, -3406, 2276, -799]
# AC codes (without the sign bit): code -> (run, level)
_MAC = """11 0 1|011 1 1|0100 0 2|0101 2 1|00101 0 3|00111 3 1|00110 4 1|000110 1 2|000111 5 1|000101 6 1|000100 7 1|
0000110 0 4|0000100 2 2|0000111 8 1|0000101 9 1|00100110 0 5|00100001 0 6|00100101 1 3|00100100 3 2|00100111 10 1|
00100011 11 1|00100010 12 1|00100000 13 1|0000001010 0 7|0000001100 1 4|0000001011 2 3|0000001111 4 2|0000001001 5 2|
0000001110 14 1|0000001101 15 1|0000001000 16 1|000000011101 0 8|000000011000 0 9|000000010011 0 10|000000010000 0 11|
000000011011 1 5|000000010100 2 4|000000011100 3 3|000000010010 4 3|000000011110 6 2|000000010101 7 2|000000010001 8 2|
000000011111 17 1|000000011010 18 1|000000011001 19 1|000000010111 20 1|000000010110 21 1|0000000011010 0 12|
0000000011001 0 13|0000000011000 0 14|0000000010111 0 15|0000000010110 1 6|0000000010101 1 7|0000000010100 2 5|
0000000010011 3 4|0000000010010 5 3|0000000010001 9 2|0000000010000 10 2|0000000011111 22 1|0000000011110 23 1|
0000000011101 24 1|0000000011100 25 1|0000000011011 26 1|00000000011111 0 16|00000000011110 0 17|00000000011101 0 18|
00000000011100 0 19|00000000011011 0 20|00000000011010 0 21|00000000011001 0 22|00000000011000 0 23|00000000010111 0 24|
00000000010110 0 25|00000000010101 0 26|00000000010100 0 27|00000000010011 0 28|00000000010010 0 29|00000000010001 0 30|
00000000010000 0 31|000000000011000 0 32|000000000010111 0 33|000000000010110 0 34|000000000010101 0 35|
000000000010100 0 36|000000000010011 0 37|000000000010010 0 38|000000000010001 0 39|000000000010000 0 40|
000000000011111 1 8|000000000011110 1 9|000000000011101 1 10|000000000011100 1 11|000000000011011 1 12|
000000000011010 1 13|000000000011001 1 14|0000000000010011 1 15|0000000000010010 1 16|0000000000010001 1 17|
0000000000010000 1 18|0000000000010100 6 3|0000000000011010 11 2|0000000000011001 12 2|0000000000011000 13 2|
0000000000010111 14 2|0000000000010110 15 2|0000000000010101 16 2|0000000000011111 27 1|0000000000011110 28 1|
0000000000011101 29 1|0000000000011100 30 1|0000000000011011 31 1"""
MAC = {}
for _me in _MAC.replace('\n', '').split('|'):
    _mc, _mr, _ml = _me.split(); MAC[(len(_mc), int(_mc, 2))] = (int(_mr), int(_ml))


def mdec_frame(sector, nsec, n):
    """the bitstream of frame n (1-based, as in the sector headers) of an STR; sector(k) = user data of its k-th sector"""
    parts = {}
    for k in range(nsec):
        d = sector(k)
        if d[:4] != b'\x60\x01\x01\x80': continue
        chunk, chunks, fr = struct.unpack_from('<HHI', d, 4)
        if fr == n: parts[chunk] = d[32:2048]
        elif fr > n and parts: break
    return b''.join(parts[k] for k in sorted(parts))


class _MBits:
    def __init__(s, d): s.d = d; s.p = 0; s.acc = 0; s.n = 0

    def peek(s, n):
        while s.n < n:
            w = s.d[s.p] | (s.d[s.p + 1] << 8) if s.p + 1 < len(s.d) else 0
            s.p += 2; s.acc = (s.acc << 16) | w; s.n += 16
        return (s.acc >> (s.n - n)) & ((1 << n) - 1)

    def get(s, n):
        v = s.peek(n); s.n -= n; s.acc &= (1 << s.n) - 1; return v


def _msigned(v, n): return v - (1 << n) if v >> (n - 1) else v


def _mdec_block(br, q, idct=True):
    c = [0] * 64
    v = _msigned(br.get(10), 10) * MQT[0]
    c[0] = max(-1024, min(1023, v))
    k = 0
    while True:
        if br.peek(2) == 2: br.get(2); break
        if br.peek(6) == 1:
            br.get(6); run = br.get(6); lev = _msigned(br.get(10), 10)
        else:
            for ln in range(2, 17):
                e = MAC.get((ln, br.peek(ln)))
                if e: break
            else: raise ValueError('bad AC code')
            br.get(ln); run, lev = e
            if br.get(1): lev = -lev
        k += run + 1
        if k > 63: raise ValueError('AC past the block')
        z = MZZ[k]
        c[z] = max(-1024, min(1023, (lev * MQT[z] * q + 4) >> 3))
    if not idct: return c
    # IDCT: rows then columns
    t = [0] * 64
    for y in range(8):
        r = c[y * 8:y * 8 + 8]
        for x in range(8):
            s = 0
            for u in range(8):
                if r[u]: s += MB[u * 8 + x] * r[u]
            t[y * 8 + x] = (s + 1024) >> 11
    o = [0] * 64
    for x in range(8):
        for y in range(8):
            s = 0
            for v in range(8): s += MB[v * 8 + y] * t[v * 8 + x]
            o[y * 8 + x] = (s + 16384) >> 15
    return o


def mdec_decode(bs, w, h, x0=0, y0=0, x1=None, y1=None):
    """RGB rows (list of bytearrays w*3) of a version-2 frame; only the macroblocks touching [x0,x1)x[y0,y1) are built
    (the others are still parsed)"""
    x1 = w if x1 is None else x1; y1 = h if y1 is None else y1
    q, ver = struct.unpack_from('<HH', bs, 4)
    assert ver == 2, ver
    br = _MBits(bs[8:])
    img = [bytearray(w * 3) for _ in range(h)]
    for mx in range(0, w, 16):
        for my in range(0, h, 16):
            use = not (mx + 16 <= x0 or mx >= x1 or my + 16 <= y0 or my >= y1)
            cr = _mdec_block(br, q, use); cb = _mdec_block(br, q, use); ys = [_mdec_block(br, q, use) for _ in range(4)]
            if not use: continue
            for yy in range(16):
                row = img[my + yy]
                for xx in range(16):
                    yv = ys[(yy >> 3) * 2 + (xx >> 3)][(yy & 7) * 8 + (xx & 7)] + 128
                    k = (yy >> 1) * 8 + (xx >> 1); r_ = cr[k]; b_ = cb[k]
                    R = yv + ((359 * r_ + 128) >> 8); G = yv - ((88 * b_ + 183 * r_ + 128) >> 8); Bv = yv + ((454 * b_ + 128) >> 8)
                    p = (mx + xx) * 3
                    row[p] = 0 if R < 0 else 255 if R > 255 else R
                    row[p + 1] = 0 if G < 0 else 255 if G > 255 else G
                    row[p + 2] = 0 if Bv < 0 else 255 if Bv > 255 else Bv
    return img


def face_op(fbd, sector, nsec, op):
    """['face', fbd, movie, {cards, face, clut, n}]: portraits from frames of a PS1 movie of the player's disc (mod crew).
    cards = [[frame, x, y, w, h, white background], ...]; picture k (64x64, 8-bit) at VRAM face + (32 k, 0), its
    palette (n colours, 0 = transparent) at clut + (0, k); fbd = bytearray of a FBD file (header 20, x 320, w 704);
    sector(k) = user data of the k-th of the nsec sectors of the movie"""
    p = op[3]; fx, fy = p['face']; cx, cy = p['clut']; n = p['n']
    vo = lambda x, y: 20 + (y * 704 + x - 320) * 2
    for k, card in enumerate(p['cards']):
        idx, clut = _face(sector, nsec, card, n)
        for y in range(64): o = vo(fx + 32 * k, fy + y); fbd[o:o + 64] = bytes(idx[y * 64:(y + 1) * 64])
        o = vo(cx, cy + k); fbd[o:o + 2 * n] = struct.pack('<%dH' % n, *clut)


def _face(sector, nsec, card, ncol):
    fr, x0, y0, w, h, white = card
    img = mdec_decode(mdec_frame(sector, nsec, fr), 320, 240, x0, y0, x0 + w, y0 + h)
    px = [[(img[y0 + y][(x0 + x) * 3], img[y0 + y][(x0 + x) * 3 + 1], img[y0 + y][(x0 + x) * 3 + 2]) for x in range(w)] for y in range(h)]
    def isbg(c):
        if white: return min(c) >= 236 and max(c) - min(c) <= 16
        return max(c) <= 48
    def fringe(c):   # the light (or dark) halo of the compression around the drawing
        if white: return min(c) >= 196 and max(c) - min(c) <= 40
        return max(c) <= 72
    bg = [[False] * w for _ in range(h)]
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if bg[y][x] or not isbg(px[y][x]): continue
        bg[y][x] = True
        if x > 0: stack.append((x - 1, y))
        if x < w - 1: stack.append((x + 1, y))
        if y > 0: stack.append((x, y - 1))
        if y < h - 1: stack.append((x, y + 1))
    for _ in range(2):   # the halo next to the background goes too (two pixels deep at most)
        add = [(x, y) for y in range(h) for x in range(w) if not bg[y][x] and fringe(px[y][x])
               and ((x > 0 and bg[y][x - 1]) or (x < w - 1 and bg[y][x + 1]) or (y > 0 and bg[y - 1][x]) or (y < h - 1 and bg[y + 1][x]))]
        for x, y in add: bg[y][x] = True
    small = []
    for dy in range(64):
        sy0, sy1 = dy * h // 64, (dy + 1) * h // 64
        for dx in range(64):
            sx0, sx1 = dx * w // 64, (dx + 1) * w // 64
            r = g = b = c = t = 0
            for y in range(sy0, sy1):
                for x in range(sx0, sx1):
                    t += 1
                    if bg[y][x]: continue
                    q = px[y][x]; r += q[0]; g += q[1]; b += q[2]; c += 1
            small.append(None if c == 0 or c * 2 < t else (r // c, g // c, b // c))
    for _ in range(2):   # specks: an opaque pixel with at most one opaque neighbour (4-connected) becomes transparent
        nxt = list(small)
        for i in range(4096):
            if small[i] is None: continue
            x, y = i % 64, i // 64
            on = (x > 0 and small[i - 1] is not None) + (x < 63 and small[i + 1] is not None) + (y > 0 and small[i - 64] is not None) + (y < 63 and small[i + 64] is not None)
            if on <= 1: nxt[i] = None
        small = nxt
    ink = [i for i in range(4096) if small[i] is None and (
        (i % 64 > 0 and small[i - 1] is not None) or (i % 64 < 63 and small[i + 1] is not None) or
        (i >= 64 and small[i - 64] is not None) or (i < 4032 and small[i + 64] is not None))]
    pal = _median_cut([q for q in small if q is not None], ncol - 2)
    idx = []
    for q in small:
        if q is None: idx.append(0); continue
        best = 0; bd = 1 << 30
        for i, c in enumerate(pal):
            d = (q[0] - c[0]) ** 2 + (q[1] - c[1]) ** 2 + (q[2] - c[2]) ** 2
            if d < bd: bd = d; best = i
        idx.append(best + 1)
    for i in ink: idx[i] = len(pal) + 1   # a dark outline around the picture, like the ink of the game's portraits
    clut = [0] + [((c[0] >> 3) | (c[1] >> 3) << 5 | (c[2] >> 3) << 10) or 0x8000 for c in pal] + [0x0842]
    return idx, clut + [0] * (ncol - len(clut))


def _median_cut(pixels, n):
    boxes = [sorted(pixels)]
    while len(boxes) < n:
        best = -1; br = 0; bc = 0
        for i, bx in enumerate(boxes):
            if len(bx) < 2: continue
            for c in range(3):
                lo = min(q[c] for q in bx); hi = max(q[c] for q in bx)
                if hi - lo > br: br = hi - lo; best = i; bc = c
        if best < 0: break
        bx = sorted(boxes[best], key=lambda q: (q[bc], q[0], q[1], q[2])); m = len(bx) // 2
        boxes[best:best + 1] = [bx[:m], bx[m:]]
    return [(sum(q[0] for q in bx) // len(bx), sum(q[1] for q in bx) // len(bx), sum(q[2] for q in bx) // len(bx)) for bx in boxes]


def crew_menu_chunk(archive, fbd, p):
    """['crewmenu', lba, archive, fbd, p] (mod crew): menu model of a CPU rider built from its ending model (TMD of
    16 parts in a CHR archive: hands joined to the forearms, board left out, lowered by p['yshift'], texture moved to
    p['col'] / palette row p['cly']) + its texture from ENDING.FBD; TMD already mapped for p['dest']"""
    n0 = struct.unpack_from('<I', archive, 4)[0]; t = archive[n0 * 4:4 * struct.unpack_from('<I', archive, 8)[0]]
    n = struct.unpack_from('<I', t, 8)[0]; parts = []
    for i in range(n):
        vt, nv, nt, nn, pt, np_, sc = struct.unpack_from('<7I', t, 12 + 28 * i)
        verts = [list(struct.unpack_from('<4h', t, 12 + vt + 8 * j)) for j in range(nv)]
        norms = t[12 + nt:12 + nt + 8 * nn]
        prims = []; o = 12 + pt
        for _ in range(np_):
            ilen = t[o + 1]; prims.append(list(struct.unpack_from('<%dI' % (ilen + 1), t, o))); o += 4 + 4 * ilen
        if not any((w[0] >> 24) & 4 and (w[2] >> 16) & 0x1f == 5 for w in prims): parts.append((verts, norms, prims))
    col, cly = p['col'], p['cly']; ncba = (768 >> 4) | (cly << 6)
    idx = {int(k): v for k, v in p['idx'].items()}
    out = []
    for group in p['parts']:
        V = []; N = bytearray(); P = []
        for gi in group:
            verts, norms, prims = parts[gi]; vo, no = len(V), len(N) // 8
            V += [[x, y + p['yshift'], z, q] for x, y, z, q in verts]; N += norms
            for w in prims:
                w = list(w); mode = (w[0] >> 24) & 0xff
                for wi, half, kind in idx[mode]:
                    sh = 16 * half; val = ((w[wi] >> sh) & 0xffff) + (vo if kind == 'v' else no)
                    w[wi] = (w[wi] & ~(0xffff << sh) & 0xffffffff) | (val << sh)
                if mode & 4:
                    w[1] = (w[1] & 0xffff) | (ncba << 16)
                    w[2] = (w[2] & 0xffff) | (((((w[2] >> 16) & 0xffff) & ~0x1f) | (col >> 6)) << 16)
                P.append(w)
        out.append((V, N, P))
    hdr = 12 + 28 * len(out); body = bytearray(); table = []; dest = p['dest']
    for V, N, P in out:
        vt = hdr + len(body); body += b''.join(struct.pack('<4h', *v) for v in V)
        nt = hdr + len(body); body += N
        pt = hdr + len(body); body += b''.join(struct.pack('<%dI' % len(w), *w) for w in P)
        table.append((dest + vt, len(V), dest + nt, len(N) // 8, dest + pt, len(P), 0))
    tmd = struct.pack('<3I', 0x41, 1, len(out)) + b''.join(struct.pack('<7I', *e) for e in table) + bytes(body)
    assert len(tmd) <= p['clut_off'], len(tmd)
    px, py, cx, cy = p['src']; vo_ = lambda x, y: 20 + (y * 704 + x - 320) * 2
    chunk = bytearray(p['size']); chunk[:len(tmd)] = tmd
    chunk[p['clut_off']:p['clut_off'] + 512] = fbd[vo_(cx, cy):vo_(cx, cy) + 512]
    chunk[p['img_off']:p['img_off'] + 32768] = b''.join(fbd[vo_(px, py + y):vo_(px, py + y) + 128] for y in range(256))
    struct.pack_into('<I', chunk, p['magic_off'], p['magic'])
    return bytes(chunk)


def icons_op(fbd, op):
    """['icons', fbd, p] (mod crew): 16x16 4-bit heads of the riders, made from the menu portraits of the FBD (8-bit,
    p['src'] = [[x, y (VRAM of the picture's top left), w, h, clut x, clut y, colours], ...]); icon i at
    p['dest'] + (4 i, 0), its palette at p['clut'] + (16 (i % 6), i // 6), the grey one 2 rows lower"""
    p = op[2]; vo = lambda x, y: 20 + (y * 704 + x - 320) * 2
    dx, dy = p['dest']; cx0, cy0 = p['clut']
    for i, (sx, sy, w, h, cx, cy, nc) in enumerate(p['src']):
        clut = struct.unpack_from('<%dH' % nc, fbd, vo(cx, cy))
        small = []
        for y in range(16):
            for x in range(16):
                r = g = b = c = t = 0
                for yy in range(y * h // 16, (y + 1) * h // 16):
                    row = vo(sx, sy + yy)
                    for xx in range(x * w // 16, (x + 1) * w // 16):
                        t += 1; ci = fbd[row + xx]; v = clut[ci] if ci < nc else 0
                        if v == 0: continue
                        r += (v & 31) << 3; g += ((v >> 5) & 31) << 3; b += ((v >> 10) & 31) << 3; c += 1
                small.append(None if c == 0 or c * 2 < t else (r // c, g // c, b // c))
        pal = _median_cut([q for q in small if q is not None], 15)
        idx = []
        for q in small:
            if q is None: idx.append(0); continue
            best = 0; bd = 1 << 30
            for j, c in enumerate(pal):
                dd = (q[0] - c[0]) ** 2 + (q[1] - c[1]) ** 2 + (q[2] - c[2]) ** 2
                if dd < bd: bd = dd; best = j
            idx.append(best + 1)
        for y in range(16):
            o = vo(dx + 4 * i, dy + y)
            for x in range(0, 16, 2): fbd[o + x // 2] = idx[y * 16 + x] | (idx[y * 16 + x + 1] << 4)
        cols = [0] + [((c[0] >> 3) | (c[1] >> 3) << 5 | (c[2] >> 3) << 10) or 0x8000 for c in pal]
        greys = [0] + [((((c[0] * 77 + c[1] * 150 + c[2] * 29) >> 8) * 5 // 8) >> 3) * 0x421 or 0x8000 for c in pal]
        cols += [0] * (16 - len(cols)); greys += [0] * (16 - len(greys))
        for row, cl in ((cy0 + i // 6, cols), (cy0 + 2 + i // 6, greys)):
            o = vo(cx0 + 16 * (i % 6), row); fbd[o:o + 32] = struct.pack('<16H', *cl)


def px4(d, op):
    """['px4', file, header, width (halfwords), [x, y, w, h, fill], transparent, [[sx, sy, w, h, dx, dy]...]]:
    copies the non-transparent 4-bit pixels of rectangles of the original image into it (d: bytearray, in place)"""
    _, _, hdr, W, (cx, cy, cw, ch, fill), tr, blits = op
    rows = (len(d) - hdr) // (W * 2)
    def get(x, y): v = d[hdr + y * W * 2 + x // 2]; return (v >> 4) if x & 1 else (v & 15)
    def put(x, y, c):
        i = hdr + y * W * 2 + x // 2; d[i] = (d[i] & 15) | (c << 4) if x & 1 else (d[i] & 0xf0) | c
    src = {}
    for sx, sy, w, h, dx, dy in blits:
        for y in range(h):
            for x in range(w): src[(sx + x, sy + y)] = get(sx + x, sy + y)
    for y in range(ch):
        for x in range(cw): put(cx + x, cy + y, fill)
    for sx, sy, w, h, dx, dy in blits:
        for y in range(h):
            for x in range(w):
                c = src[(sx + x, sy + y)]
                if c != tr: put(dx + x, dy + y, c)

def mark(disc, mods, text):
    """write the configuration code in the volume descriptor (application-use area, unused by the game)"""
    m = mods.get(16); d = bytearray(m[1] if m else disc.user(16)); s = ('CB2REMIX ' + text).encode()[:100]
    d[900:1000] = s + bytes(100 - len(s)); mods[16] = (m[0] if m else disc.img.sector(16)[16:24], bytes(d)); return mods

def read_config(disc):
    s = disc.user(16)[900:1000].split(b'\0')[0].decode('latin1')
    return s[9:] if s.startswith('CB2REMIX ') else None

def save(pkg, path): open(path, 'wb').write(gzip.compress(json.dumps(pkg, separators=(',', ':')).encode(), 9, mtime=0))
def load(path): return json.loads(gzip.decompress(open(path, 'rb').read()))

# ------------------------------------------------------------------------------------------------ configuration code
# bytes: [1] version, [2] mods (bit i = FEATURES[i], 16 bits LE), [1] options (bit 0 = USA music, bits 1-2 intro
# (reserved), bit 3 = 60 Hz (reserved)), [up to 8] ready-to-wear skins (bit i = entry i of the site's skins/index.json);
# trailing zero bytes dropped, then 1 check byte (crc32 & 255); Crockford base32, "CB2-XXXX-XXXX".
B32 = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
IDS = [f[0] for f in FEATURES]
RETIRED = {'lift'}                       # kept in IDS so that old codes still decode; no longer offered
SHOWN = [f for f in IDS if f not in RETIRED]

def encode_config(mods, us_music=False, skins=()):
    m = sum(1 << IDS.index(f) for f in mods); s = sum(1 << i for i in skins if 0 <= i < 64)
    b = bytearray([1, m & 255, m >> 8, 1 if us_music else 0]) + s.to_bytes(8, 'little')
    while len(b) > 2 and b[-1] == 0: b.pop()
    import zlib; b.append(zlib.crc32(bytes(b)) & 255)
    n = int.from_bytes(b, 'big'); nb = len(b) * 8; k = -(-nb // 5); n <<= k * 5 - nb
    s = ''.join(B32[(n >> (5 * (k - 1 - i))) & 31] for i in range(k))
    return 'CB2-' + '-'.join(s[i:i + 4] for i in range(0, len(s), 4))

def decode_config(code):
    import zlib
    s = code.upper().strip(); s = s[3:] if s.startswith('CB2') else s
    s = s.translate(str.maketrans('OIL', '011')).replace('-', '').replace(' ', '')
    if not s or any(c not in B32 for c in s): raise ValueError('code invalide')
    n = 0
    for c in s: n = n * 32 + B32.index(c)
    nb = len(s) * 5 // 8; n >>= len(s) * 5 - nb * 8; b = n.to_bytes(nb, 'big')
    if len(b) < 2 or zlib.crc32(b[:-1]) & 255 != b[-1] or b[0] != 1: raise ValueError('code invalide')
    b = b[:-1] + bytes(12); m = b[1] | b[2] << 8; s = int.from_bytes(b[4:12], 'little')
    return {'mods': [f for i, f in enumerate(IDS) if m >> i & 1], 'us_music': bool(b[3] & 1), 'skins': [i for i in range(64) if s >> i & 1]}

if __name__ == '__main__':
    # usage: modular.py PAL.chd REFERENCE.chd PAL_fs remix/cb2remix.delta.gz out.json.gz
    pkg = generate(*sys.argv[1:5]); save(pkg, sys.argv[5])
    print({k: len(v) for k, v in pkg['ops'].items()}, os.path.getsize(sys.argv[5]), 'octets')
