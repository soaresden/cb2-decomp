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
     '○ sur l’écran BOARDER : toutes les stats au maximum, « MAX » sous le portrait.', '○ on the BOARDER screen: every stat maxed, “MAX” under the portrait.'),
    ('air', 'Figures en l’air', 'Air control',
     'La croix seule fait tourner (gauche/droite = spin, haut/bas = flip), Carré = rotations ×4, grabs « X to Y » en gardant R1.',
     'The d-pad alone rotates (left/right = spin, up/down = flip), Square = rotations x4, “X to Y” grabs while holding R1.'),
    ('ramming', 'Chocs en Boarder Cross', 'Boarder Cross ramming',
     'Fonce dans un adversaire : le plus rapide des deux reste debout.', 'Ram an opponent: the faster of the two stays up.'),
    ('bam', 'Big Air Master', 'Big Air Master',
     'Touches toujours affichées et figures suivantes (NEXT) à droite.', 'Keys always shown and the next tricks (NEXT) on the right.'),
    ('progress', 'Progression dans le jeu', 'In-game progress',
     'SELECT maintenu sur l’écran des modes : riders cachés, Mirror, Hard, Hard + Mirror, planches SPECIAL, trophées et pourcentage.',
     'Hold SELECT on the mode select screen: hidden riders, Mirror, Hard, Hard + Mirror, SPECIAL boards, trophies and percentage.'),
    ('lift', 'Arrivée express en Free Style', 'Quick finish in Free Style',
     'À l’arrivée, le temps compte comme d’habitude (classement, records, trophées) mais sans célébration ni replay : classement, START, résultats avec ton temps, X = RETRY et tu repars aussitôt d’en haut.',
     'At the finish the run counts as usual (ranking, records, trophies) but without the celebration and the replay: ranking, START, results with your time, X = RETRY and you start again from the top.'),
]
INPUT = 'input'   # shared pad hook (needed by 'max' and 'air')

def _r(*xs): return xs
EXE_MAP = [   # (lo, hi, feature) in the executable
    (0x8001B594, 0x8001B594, INPUT), (0x8004F980, 0x8004F99F, INPUT), (0x8004FA10, 0x8004FBFF, INPUT), (0x8004F9A0, 0x8004F9DF, INPUT),
    (0x8004F8CC, 0x8004F8FF, INPUT), (0x8002957C, 0x8002979F, INPUT), (0x8002A030, 0x8002A180, INPUT),
    (0x8002815C, 0x80028413, 'max'), (0x8001228C, 0x8001228C, 'max'),
    (0x80028BF4, 0x80028D3C, 'ramming'),
    (0x8004F878, 0x8004F89F, 'hardmirror'),
    (0x8004F800, 0x8004F877, 'riders'), (0x8004F8A0, 0x8004F8CB, 'riders'), (0x8004F900, 0x8004F91F, 'riders'), (0x8004F940, 0x8004F96B, 'riders'),
    (0x8001CEFC, 0x8001CF00, 'riders'), (0x8001CFE0, 0x8001CFE0, 'riders'), (0x8001D078, 0x8001D078, 'riders'), (0x8001D104, 0x8001D10C, 'riders'),
    (0x8004F920, 0x8004F93F, 'outfits'), (0x8004F96C, 0x8004F97F, 'outfits'), (0x8004F9E0, 0x8004F9EF, 'outfits'),
    (0x8001D140, 0x8001D140, 'outfits'), (0x8001003C, 0x8001003C, 'outfits'), (0x800100B8, 0x800100B8, 'outfits'),
    (0x800100B4, 0x800100B4, 'progress'),
]
MODE_MAP = [(0x800643B4, 0x800643B4, 'progress'), (0x800832C8, 0x800836A8, 'progress')]
MS_MAP = [(0x8006B68C, 0x8006B68C, 'max'), (0x8006BE3C, 0x8006BE3C, 'max'), (0x8006CAAC, 0x8006CAAC, 'max'), (0x80063EA8, 0x80063EA8, 'unlock'), (0x8005B0C4, 0x8005B0C4, 'special'), (0x80069D00, 0x8006C910, 'special'),
          (0x800614B8, 0x800614B8, 'max'), (0x800626E4, 0x800626E4, 'max'), (0x80063FC8, 0x80063FCC, 'riders'), (0x80064044, 0x80064044, 'riders'),
          (0x800605B4, 0x80062180, 'outfits'), (0x800640EC, 0x80064210, 'outfits')]
SBC_MAP = {'/FREE.BIN': [(0x8005D5A4, 0x8005D5A4, 'lift')],
           '/SBC1.BIN': [(0x800832DC, 0x800832DC, 'riders'), (0x8008D8C8, 0x8008D910, 'riders')],
           '/SBC2.BIN': [(0x8005FF70, 0x8005FF70, 'ramming'), (0x80064D70, 0x80064D70, 'riders'), (0x800666EC, 0x800666F0, 'riders'),
                         (0x80066CB4, 0x80066CB8, 'riders'), (0x80090300, 0x80090420, 'riders'), (0x800847AC, 0x800847AC, 'riders'), (0x800902A8, 0x800902F0, 'riders')],
           '/TM.BIN': [(0x80075738, 0x80075758, 'bam'), (0x80074CFC, 0x80074CFC, 'bam'), (0x80094F18, 0x80095538, 'bam')]}
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
    pkg['ops'][INPUT] = []; pkg['ops']['input_noair'] = []
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
    files = {}; recs = {}; secs = {}
    origs = {}
    def orig(p):
        if p not in origs: origs[p] = disc.read_file(p)
        return origs[p]
    def buf(p):
        if p not in files: files[p] = bytearray(orig(p))
        return files[p]
    order = [f for f in ('unlock', 'special', 'hardmirror', 'riders', 'outfits', 'max', 'air', 'ramming', 'bam', 'progress', 'lift', INPUT, 'input_noair') if f in feats]
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
