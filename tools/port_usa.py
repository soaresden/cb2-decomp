#!/usr/bin/env python3
"""Map addresses of Cool Boarders 2 PAL (SCES-00992) to the USA version (SCUS-94358).

Both versions share 93 % of their code (see docs/pal_vs_usa.md). Functions are paired (same order in the overlays,
by content in the executable), then the instructions of each pair are aligned; this gives
  - code(file, addr): the USA address of a PAL instruction,
  - data(addr): the USA address of a PAL variable, learnt from the lui/addiu, lui/lw... pairs of the aligned code.
usage: python3 tools/port_usa.py PAL_fs USA_fs        (prints a summary)
"""
import bisect, difflib, hashlib, struct, sys, collections

OVL = 0x8005AEA8; EXE = 0x80010000
USA_OVL = 0x8005AB68           # the USA executable loads its overlays 0x340 bytes lower
FILES = [('SCES_009.92', 'SCUS_943.58', EXE, EXE, 0x800)] + [(f, f, OVL, USA_OVL, 0) for f in
         ['INIT.BIN', 'MAIN_SEL.BIN', 'MODE_SEL.BIN', 'SBC1.BIN', 'SBC2.BIN', 'VS.BIN', 'OMT.BIN', 'BP.BIN', 'HP.BIN',
          'FREE.BIN', 'TM.BIN', 'COMB.BIN', 'BDEDIT.BIN', 'ENDING.BIN']]

def words(path, hdr):
    d = open(path, 'rb').read()[hdr:]; d += bytes((-len(d)) % 4)
    return list(struct.unpack('<%dI' % (len(d) // 4), d))

def norm(w):
    op = w >> 26
    if op == 0: return w
    if op in (2, 3): return op << 26
    if op in (1, 4, 5, 6, 7): return w                       # branches: offsets stay the same in identical code
    return w & 0xffff0000                                    # immediates (addresses) differ between versions

def functions(W):
    st = [i for i, w in enumerate(W) if (w >> 16) == 0x27bd and (w & 0x8000)]
    return [(s, st[k + 1] if k + 1 < len(st) else len(W)) for k, s in enumerate(st)]

class Port:
    def __init__(s, pal_fs, usa_fs):
        s.cmap = {}            # (pal file, pal addr) -> usa addr
        s.pairs = collections.Counter()   # (pal data addr, usa data addr) seen in aligned code
        s.W = {}
        for pf, uf, base, ubase, hdr in FILES:
            P = words(f'{pal_fs}/{pf}', hdr); U = words(f'{usa_fs}/{uf}', hdr); s.W[pf] = (P, U, base)
            fp, fu = functions(P), functions(U)
            hp = [hashlib.sha1(bytes(str([norm(w) for w in P[a:b]]), 'ascii')).digest() for a, b in fp]
            hu = [hashlib.sha1(bytes(str([norm(w) for w in U[a:b]]), 'ascii')).digest() for a, b in fu]
            if len(fp) == len(fu): fpairs = list(zip(fp, fu))
            else:
                sm = difflib.SequenceMatcher(None, hp, hu, autojunk=False); fpairs = []
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1): fpairs += list(zip(fp[i1:i2], fu[j1:j2]))
            # also the stretch before the first function (start-up code / overlay header)
            fpairs.append(((0, fp[0][0]), (0, fu[0][0])))
            for (a, b), (c, d) in fpairs:
                np_, nu = [norm(w) for w in P[a:b]], [norm(w) for w in U[c:d]]
                if np_ == nu: ops = [('equal', 0, b - a, 0, d - c)]
                else: ops = difflib.SequenceMatcher(None, np_, nu, autojunk=False).get_opcodes()
                for tag, i1, i2, j1, j2 in ops:
                    if tag != 'equal': continue
                    for k in range(i2 - i1):
                        s.cmap[(pf, base + 4 * (a + i1 + k))] = ubase + 4 * (c + j1 + k)
                    s._learn(P[a + i1:a + i2], U[c + j1:c + j2])
        # data map: sorted list of PAL addresses with their USA counterpart (most frequent pairing)
        best = {}
        for (pa, ua), n in s.pairs.items():
            if pa not in best or n > best[pa][1]: best[pa] = (ua, n)
        s.dkeys = sorted(best); s.dval = [best[k][0] for k in s.dkeys]

    def _learn(s, P, U):
        hi_p, hi_u = {}, {}
        for x, y in zip(P, U):
            op = x >> 26; rs = (x >> 21) & 31; rt = (x >> 16) & 31
            if op == 0x0f: hi_p[rt] = (x & 0xffff) << 16; hi_u[rt] = (y & 0xffff) << 16; continue
            if op in (9, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2b) and rs in hi_p and rs in hi_u:
                sx = lambda v: (v & 0xffff) - ((v & 0x8000) << 1)
                pa = (hi_p[rs] + sx(x)) & 0xffffffff; ua = (hi_u[rs] + sx(y)) & 0xffffffff
                if 0x80010000 <= pa < 0x80200000: s.pairs[(pa, ua)] += 1
                if op == 9 and rt == rs: hi_p.pop(rs, None); hi_u.pop(rs, None)
            if op in (0, 8, 9, 10, 11, 12, 13, 0x20, 0x21, 0x23, 0x24, 0x25):
                rd = ((x >> 11) & 31) if op == 0 else rt
                if not (op == 9 and rt == rs) and rd in hi_p and op != 0x0f: hi_p.pop(rd, None); hi_u.pop(rd, None)

    def code(s, f, addr):
        return s.cmap.get((f, addr))

    def data(s, addr, exact=False):
        """USA address of a PAL variable: exact when seen in the code, else same offset from the nearest known one"""
        i = bisect.bisect_right(s.dkeys, addr) - 1
        if i >= 0 and s.dkeys[i] == addr: return s.dval[i]
        if exact: return None
        cands = [j for j in (i, i + 1) if 0 <= j < len(s.dkeys)]
        if not cands: return None
        j = min(cands, key=lambda j: abs(s.dkeys[j] - addr))
        return s.dval[j] + (addr - s.dkeys[j])

if __name__ == '__main__':
    p = Port(sys.argv[1], sys.argv[2])
    tot = collections.Counter(f for f, _ in p.cmap)
    for pf, uf, base, ubase, hdr in FILES:
        print(f'{pf:12s} instructions PAL alignées : {tot[pf]:6d} / {len(p.W[pf][0])}')
    print('variables appariées :', len(p.dkeys))
    for n, a in [('g_rider', 0x80057408), ('g_mirror', 0x8005742E), ('déblocages', 0x8005743E), ('planches SPECIAL', 0x80057442), ('g_fileTable', 0x800583E8), ('g_padButtons', 0x8004FBF0)]:
        print(f'  {n:16s} PAL 0x{a:08X} -> USA 0x{p.data(a):08X}' + (' (vu dans le code)' if p.data(a, True) else ' (déduit)'))
