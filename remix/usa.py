#!/usr/bin/env python3
"""Cool Boarders 2 Remix for the USA version (SCUS-94358): the Remix patches carried over with tools/port_usa.py.

Ported so far (phase 1, see docs/remix_usa.md):
  - everything unlocked on a new save (tracks, riders, special boards, mirror, hard, awards),
  - every rider selectable even with an old save, SPECIAL boards always offered (competition too),
  - Hard + Mirror together: L1 + R1 + X on Competition.
usage: python3 remix/usa.py PAL_fs USA_fs  -> prints the patch list (file, USA address, old word, new word)
"""
import os, pickle, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from port_usa import Port, EXE, OVL, USA_OVL
USA_EXE = '/SCUS_943.58'

def sx(v): return (v & 0xffff) - ((v & 0x8000) << 1)

class Translator:
    def __init__(s, port, usa_fs):
        s.p = port; s.fs = usa_fs; s.cache = {}
    def usa_word(s, f, addr):
        path = os.path.join(s.fs, (USA_EXE if f == '/SCES_009.92' else f).lstrip('/'))
        if path not in s.cache: s.cache[path] = open(path, 'rb').read()
        o = (addr - EXE + 0x800) if f == '/SCES_009.92' else (addr - USA_OVL)
        return struct.unpack_from('<I', s.cache[path], o)[0]
    def code(s, f, addr):
        """PAL code address -> USA (exe for addresses below the overlays, else the overlay `f`)"""
        ff = 'SCES_009.92' if addr < OVL else f.lstrip('/')
        u = s.p.code(ff, addr)
        if u is None: raise KeyError('adresse de code non alignée : %s 0x%08X' % (ff, addr))
        return u
    def single(s, f, a, old, new):
        """one replaced instruction in the game's own code"""
        ua = s.code(f, a); uo = s.usa_word(f, ua)
        if old is not None and old != 0:
            # same instruction apart from an address immediate: take the USA immediate
            same_shape = (old >> 16) == (uo >> 16) or ((old >> 26) == (uo >> 26) and (old >> 26) not in (0, 2, 3))
            if not same_shape: raise ValueError('instruction inattendue %s 0x%08X : PAL %08x USA %08x' % (f, ua, old, uo))
        un = new
        op_o, op_n = old >> 26, new >> 26
        mem = (0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2b)
        if op_o in mem and op_n in mem and ((old >> 21) & 31) == ((new >> 21) & 31) and (old & 0xffff) == (new & 0xffff):
            un = (new & 0xffff0000) | (uo & 0xffff)                      # same variable as the old instruction
        if op_n in (2, 3):
            t = ((a & 0xf0000000) | ((new & 0x3ffffff) << 2)); un = (new & 0xfc000000) | ((s.target(f, t) >> 2) & 0x3ffffff)
        return (f, ua, uo, un)
    def target(s, f, t):
        if t in getattr(s, 'override', {}): return s.override[t]
        return s.caves[t] if t in getattr(s, 'caves', {}) else s.code(f, t)
    def block(s, f, pal_base, words, usa_base, ctx_file):
        """new code written into a free zone: jumps/branches to the game and lui/lo address pairs are translated"""
        out = list(words); n = len(words); end = pal_base + 4 * n
        inside = lambda t: pal_base <= t < end
        for i, w in enumerate(words):
            op = w >> 26; pa = pal_base + 4 * i; ua = usa_base + 4 * i
            if op in (2, 3):
                t = (pa & 0xf0000000) | ((w & 0x3ffffff) << 2)
                ut = usa_base + (t - pal_base) if inside(t) else s.target(ctx_file, t)
                out[i] = (w & 0xfc000000) | ((ut >> 2) & 0x3ffffff)
            elif op in (1, 4, 5, 6, 7):
                t = pa + 4 + sx(w) * 4
                ut = usa_base + (t - pal_base) if inside(t) else s.target(ctx_file, t)
                out[i] = (w & 0xffff0000) | (((ut - (ua + 4)) >> 2) & 0xffff)
            elif op == 0x0f:                                           # lui: find its users
                r = (w >> 16) & 31; hi = (w & 0xffff) << 16; uses = []
                for j in range(i + 1, n):
                    x = words[j]; xo = x >> 26; rs = (x >> 21) & 31; rt = (x >> 16) & 31
                    if xo in (9, 13, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2b) and rs == r: uses.append(j)
                    wr = ((x >> 11) & 31) if xo == 0 else rt if xo not in (1, 2, 3, 4, 5, 0x28, 0x29, 0x2b) else None
                    if wr == r and not (xo in (9, 13) and rs == r and False): break
                if not uses: continue
                his = set()
                for j in uses:
                    x = words[j]; pa_t = (hi + (x & 0xffff)) if (x >> 26) == 13 else (hi + sx(x)) & 0xffffffff
                    if EXE <= pa_t < 0x80200000:
                        ua_t = s.p.data(pa_t)
                        if (x >> 26) == 13: his.add(ua_t >> 16); out[j] = (x & 0xffff0000) | (ua_t & 0xffff)
                        else: his.add(((ua_t + 0x8000) >> 16) & 0xffff); out[j] = (x & 0xffff0000) | (ua_t & 0xffff)
                    else: his.add(w & 0xffff)
                if len(his) != 1: raise ValueError('lui partagé par des adresses de pages différentes à 0x%08X' % pa)
                out[i] = (w & 0xffff0000) | his.pop()
        return out

def phase1(pal_fs, usa_fs, port):
    """-> [(file, USA address, USA old word, USA new word)]"""
    import importlib
    os.environ['CB2_FS'] = pal_fs
    remix = importlib.import_module('remix')
    P = remix.patches()
    T = Translator(port, usa_fs)
    want = lambda f, a: f == '/INIT.BIN' or (f, a) in {('/MAIN_SEL.BIN', 0x80063ea8), ('/MAIN_SEL.BIN', 0x8005b0c4), ('/MODE_SEL.BIN', 0x8005b81c)} \
        or (f == '/MAIN_SEL.BIN' and a in (0x80069d00, 0x80069d84, 0x80069f74, 0x8006a000, 0x8006a238, 0x8006a2cc, 0x8006a338, 0x8006b4f0, 0x8006bca0, 0x8006c1cc, 0x8006c2b4, 0x8006c5c8, 0x8006c910))
    # Hard + Mirror cave (exe 0x8004F878..0x8004F8A0 in the Remix): placed in the same free zone of the USA exe
    HM_PAL = 0x8004f878; hm = [(a, w) for f, a, o, w in P if f == '/SCES_009.92' and HM_PAL <= a < 0x8004f8a0]
    hm.sort(); words = [w for a, w in hm]
    HM_USA = port.data(HM_PAL)
    for k in range(len(words)):
        if T.usa_word('/SCES_009.92', HM_USA + 4 * k) != 0: raise ValueError('zone libre US occupée à 0x%08X' % (HM_USA + 4 * k))
    T.caves = {HM_PAL: HM_USA}
    # after "hard chosen" the USA code does not resume where the PAL one does: go back where the USA jump went
    ua = T.code('/MODE_SEL.BIN', 0x8005b81c); uo = T.usa_word('/MODE_SEL.BIN', ua)
    assert uo >> 26 == 2, hex(uo)
    T.override = {0x8005b858: (ua & 0xf0000000) | ((uo & 0x3ffffff) << 2)}
    out = [('/SCES_009.92', HM_USA + 4 * k, 0, w) for k, w in enumerate(T.block('/SCES_009.92', HM_PAL, words, HM_USA, '/MODE_SEL.BIN'))]
    for f, a, old, new in P:
        if want(f, a): out.append(T.single(f, a, old if old is not None else 0, new))
    return out

def build_delta(usa_chd, patches, out, version):
    """apply the USA patches to the USA disc -> Remix delta (format CB2D) for that disc"""
    import gzip, zlib, cb2disc
    d = cb2disc.Disc(usa_chd); files = {}
    for f, a, old, new in patches:
        if f not in files: files[f] = bytearray(d.read_file(USA_EXE if f == '/SCES_009.92' else f))
        o = (a - EXE + 0x800) if f == '/SCES_009.92' else (a - USA_OVL)
        cur = struct.unpack_from('<I', files[f], o)[0]
        if cur != old: raise ValueError('%s 0x%08X : %08x au lieu de %08x' % (f, a, cur, old))
        struct.pack_into('<I', files[f], o, new)
    secs = []
    for f, data in sorted(files.items()):
        lba, size, _ = d.files[USA_EXE if f == '/SCES_009.92' else f]
        for k in range(-(-size // 2048)):
            orig = d.user(lba + k); new = bytes(data[k * 2048:(k + 1) * 2048]); new += orig[len(new):]
            if new == orig: continue
            ops = []; i = 0
            while i < 2048:
                j = i
                while j < 2048 and new[j] == orig[j]: j += 1
                if j - i >= 12: ops.append((0, j - i, (lba + k) * 2048 + i)); i = j; continue
                j = i
                while j < 2048 and not (new[j:j + 12] == orig[j:j + 12] and j + 12 <= 2048): j += 1
                j = max(j, i + 1); ops.append((1, new[i:j])); i = j
            secs.append((lba + k, d.img.sector(lba + k)[16:24], ops))
    exe = d.read_file(USA_EXE)
    body = bytearray(b'CB2D' + struct.pack('<IIII', 1, zlib.crc32(exe), len(exe), len(secs)))
    for lba, sub, ops in secs:
        body += struct.pack('<I', lba) + sub + struct.pack('<H', len(ops))
        for o in ops: body += struct.pack('<BHI', 0, o[1], o[2]) if o[0] == 0 else struct.pack('<BH', 1, len(o[1])) + o[1]
    open(out, 'wb').write(gzip.compress(bytes(body), 9, mtime=0))
    return len(secs)

def port_cached(pal_fs, usa_fs, cache=None):
    cache = cache or os.path.join(ROOT, 'work', 'port_usa.pkl')
    if os.path.exists(cache): return pickle.load(open(cache, 'rb'))
    p = Port(pal_fs, usa_fs); os.makedirs(os.path.dirname(cache), exist_ok=True); pickle.dump(p, open(cache, 'wb')); return p

if __name__ == '__main__':
    # usage: remix/usa.py PAL_fs USA_fs [USA.chd out.delta.gz]
    pal_fs, usa_fs = sys.argv[1:3]
    P = phase1(pal_fs, usa_fs, port_cached(pal_fs, usa_fs))
    for f, a, o, n in P: print(f'{f:16s} 0x{a:08X}  {o:08x} -> {n:08x}')
    if len(sys.argv) > 4: print('secteurs modifiés :', build_delta(sys.argv[3], P, sys.argv[4], open(os.path.join(ROOT, 'remix', 'VERSION')).read().strip()))

# ------------------------------------------------------------------ phase 2: air control, MAX stats, Boarder Cross ramming, Big Air Master
def _in(a, *ranges): return any(lo <= a <= hi for lo, hi in ranges)
EXE_CAVES = {   # free zones of the PAL exe used by these features -> overlay their code jumps into
    (0x80028BF4, 0x80028D3C): '/SBC2.BIN',     # kc: Boarder Cross ramming
    (0x8002957C, 0x8002979F): '/MAIN_SEL.BIN', # maxd: MAX stats bars
    (0x8002A030, 0x8002A180): '/MAIN_SEL.BIN', # padx, maxl, help strings
    (0x8004F980, 0x8004F99F): '/SBC2.BIN',     # pad hook (exe only)
    (0x8004F9A0, 0x8004F9DF): '/SBC2.BIN',     # Square = rotations x4
    (0x8004FA10, 0x8004FBFF): '/SBC2.BIN',     # md / ax / rm / inj (air control)
}
OVL_CAVES = {}   # Big Air Master (TM.BIN 0x80094F18..) not ported yet: its code builds table addresses with addu
SKIP = {   # features that also need the data steps of remix.apply() (riders in competition, outfits, plates, voices)
    '/SCES_009.92': [(0x8001003C, 0x8001003C), (0x800100B8, 0x800100B8), (0x8001CEFC, 0x8001D140), (0x8004F800, 0x8004F97F), (0x8004F9E0, 0x8004F9FF)],
    '/MAIN_SEL.BIN': [(0x8005B000, 0x800614B4), (0x800614BC, 0x800626E0), (0x800626E8, 0x8007FFFF)],
    '/SBC1.BIN': [(0x800832DC, 0x800832DC), (0x8008D8C8, 0x8008D910)],
    '/SBC2.BIN': [(0x800847AC, 0x800847AC), (0x800902A8, 0x80090348), (0x80066CB4, 0x80066CB8), (0x800666EC, 0x800666F0), (0x80064D70, 0x80064D70)],
    '/TM.BIN': [(0x80074CFC, 0x80074CFC), (0x80094F18, 0x80095538)],
    '/SCES_009.92 hooks': [],
}
PAD_HOOK = 0x8001B594        # PAL: 'j 0x8001B5A0' after the buttons of port 0 are read (a2)
FLIP_SITES = {'/SBC1.BIN': 0x8006668C, '/TM.BIN': 0x80066380, '/OMT.BIN': 0x800663F4, '/BP.BIN': 0x800662EC}
def phase2(pal_fs, usa_fs, port, log=print):
    import importlib
    os.environ['CB2_FS'] = pal_fs
    remix = importlib.import_module('remix')
    P = [x for x in remix.patches() if not _in(x[1], *SKIP.get(x[0], []))]
    T = Translator(port, usa_fs); T.caves = {}; T.override = {}
    special = []
    # ---- the pad hook: the USA exe reads the buttons without a jump there ('sll v1,v1,8 / nor v0,v0,v1 / andi a2,v0,0xffff'
    #      then falls through). Hook = 'j pad' in place of the andi, the andi in its delay slot, and the instruction it
    #      displaced runs in a small trampoline that jumps back.
    import struct as _s
    U = open(os.path.join(usa_fs, 'SCUS_943.58'), 'rb').read(); W = _s.unpack_from('<%dI' % ((len(U) - 0x800) // 4), U, 0x800)
    hk = [i for i in range(len(W) - 3) if W[i] == 0x00031a00 and W[i + 1] == 0x00431027 and W[i + 2] == 0x3046ffff]
    if len(hk) != 1: raise ValueError('accroche manette US introuvable')
    A = EXE + 4 * (hk[0] + 2); displaced = W[hk[0] + 3]
    TRAMP = port.data(0x8004F800)                      # free zone (the PAL riders' caves, not used by this port)
    for k in range(3):
        if T.usa_word('/SCES_009.92', TRAMP + 4 * k): raise ValueError('zone libre US occupée à 0x%08X' % (TRAMP + 4 * k))
    T.override[0x8001B5A0] = TRAMP                     # where the PAL hook code jumps back to
    P = [x for x in P if not (x[0] == '/SCES_009.92' and x[1] == PAD_HOOK)]
    pad_pal = [n for f, a, o, n in remix.patches() if f == '/SCES_009.92' and a == PAD_HOOK][0]
    pad_tgt = ((pad_pal & 0x3ffffff) << 2) | 0x80000000
    # ---- flip read of the trick overlays: 'lw a0,0x10(s?)' in Europe, 'lw v0,0x10(s?)' in the USA (ax returns both)
    flips = []
    for f, a in FLIP_SITES.items():
        ws = [x for x in P if x[0] == f and x[1] in (a, a + 4)]
        P = [x for x in P if not (x[0] == f and x[1] in (a, a + 4))]
        d = open(os.path.join(usa_fs, f.lstrip('/')), 'rb').read(); WU = _s.unpack_from('<%dI' % (len(d) // 4), d)
        hs = [i for i in range(len(WU) - 4) if (WU[i] & 0xfc1fffff) == 0x8c020014 and WU[i + 1] == 0 and (WU[i + 2] >> 16) == 0x1040 and (WU[i + 3] & 0xffff07ff) == 0x00400021]
        if len(hs) != 1: raise ValueError('lecture du spin introuvable dans %s US' % f)
        hf = [i for i in range(hs[0], hs[0] + 0x100) if (WU[i] & 0xfc1fffff) == 0x8c020010 and WU[i + 1] == 0 and (WU[i + 2] >> 16) == 0x1040]
        if len(hf) != 1: raise ValueError('lecture du flip introuvable dans %s US' % f)
        flips.append((f, USA_OVL + 4 * hf[0], WU[hf[0]], [n for ff, aa, o, n in sorted(ws, key=lambda x: x[1])]))
    # ---- 1. where each free-zone block goes in the USA binaries
    blocks = []   # (file, pal_start, [words], usa_start, ctx)
    def zone(f, a):
        if f == '/SCES_009.92':
            for (lo, hi), ctx in EXE_CAVES.items():
                if lo <= a <= hi: return (lo, hi), ctx
        for lo, hi in OVL_CAVES.get(f, []):
            if lo <= a <= hi: return (lo, hi), f
        return None, None
    cave_words = {}
    for f, a, old, new in P:
        z, ctx = zone(f, a)
        if z: cave_words.setdefault((f, z, ctx), []).append((a, old, new))
    for (f, (lo, hi), ctx), ws in cave_words.items():
        ws.sort()
        if f == '/SCES_009.92' and hi < 0x80045684:          # dead Sony functions: same function in the USA exe
            base = T.code(f, lo); kind = 'fonction morte'
        else:
            base = port.data(lo, f=f if f != '/SCES_009.92' else None); kind = 'zone libre'
        for a, old, new in ws:
            ua = base + (a - lo); T.caves[a] = ua
        blocks.append((f, lo, ws, base, ctx, kind))
    out = []; errors = []
    # ---- 2. the blocks, word by word (gaps keep the USA content)
    for f, lo, ws, base, ctx, kind in blocks:
        span = (ws[-1][0] - lo) // 4 + 1; words = [None] * span
        for a, old, new in ws: words[(a - lo) // 4] = new
        fill = [w if w is not None else T.usa_word(f, base + 4 * k) for k, w in enumerate(words)]
        try: tr = T.block(f, lo, fill, base, ctx)
        except Exception as e: errors.append('%s bloc 0x%08X : %s' % (f, lo, e)); continue
        for a, old, new in ws:
            k = (a - lo) // 4; ua = base + 4 * k; uo = T.usa_word(f, ua)
            if kind == 'zone libre' and uo != 0: errors.append('%s 0x%08X : zone US non vide (%08x)' % (f, ua, uo)); continue
            out.append((f, ua, uo, tr[k]))
    # ---- 3. the game's own instructions
    for f, a, old, new in P:
        if a in T.caves: continue
        try: out.append(T.single(f, a, old or 0, new))
        except Exception as e: errors.append('%s 0x%08X : %s' % (f, a, e))
    # pad hook + trampoline
    pad_us = T.caves[pad_tgt]
    out += [('/SCES_009.92', A, 0x3046ffff, (2 << 26) | ((pad_us >> 2) & 0x3ffffff)), ('/SCES_009.92', A + 4, displaced, 0x3046ffff),
            ('/SCES_009.92', TRAMP, 0, displaced), ('/SCES_009.92', TRAMP + 4, 0, (2 << 26) | (((A + 8) >> 2) & 0x3ffffff)), ('/SCES_009.92', TRAMP + 8, 0, 0)]
    # flip reads: 'jal ax' + 't5 = 1' in its delay slot (the load delay slot of the original)
    for f, ua, uo, (n0, n1) in flips:
        tgt = ((n0 & 0x3ffffff) << 2) | 0x80000000
        out += [(f, ua, uo, (3 << 26) | ((T.caves[tgt] >> 2) & 0x3ffffff)), (f, ua + 4, 0, n1)]
    return out, errors
