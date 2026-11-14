# Cindy's unused ending outfit as a race model (part of the mod `crew`, v58).
#
# ENDING/S_CHR/ED_CHRCG.DAT is a model of the ending that the game never loads: Cindy (her face, her texture slot of
# the ending, x 384 in ENDING.FBD, palette rows 480 / 481) slimmer, in heels, with a ponytail, no board. It is a
# menu outfit of Cindy (crew.py, menu model 5) and, here, her race model:
#   geometry: the 15 parts of the ending model (standing, about 3300 high, facing +z) put in the pose of Cindy's race
#     model FR/1P/FRFM1.PMD (crouched on the board, about 0.59 of the size, facing +x, legs along z). For each part,
#     the transform that takes Cindy's own ending part (ENDING/M_CHR/ED_CHR21.DAT) onto her race object (a turn of
#     -90 degrees about y and a scale for the whole body, then per part: centre, main axis, length) is applied to the
#     part of ED_CHRCG; computed here (12 small integer matrices, in the package), applied by the patcher.
#   race objects (FRFM1: 12, animated by the game): 0 head, 1 / 2 thigh / shin (z < 0), 3 board + boots, 4 chest,
#     5 hips, 6 / 7 upper arm / forearm + hand (z > 0), 8 / 9 (z < 0), 10 / 11 thigh / shin (z > 0). Her feet (heels)
#     go with the board (object 3, whose boots are left out); the black soles of the ending (18 flat triangles) too.
#   texture: her UVs read Cindy's 8-bit texture of the ending (128 x 256); the race wants 4 bits with 16-colour
#     palettes (2 rows of 16 at x 768, rows 493 / 494, image at x 576). Parts sharing texels are grouped, each group
#     gets its own 16 colours (median cut), each triangle its group's palette.
import struct
import numpy as np

FS_CG = '/ENDING/S_CHR/ED_CHRCG.DAT'
FS_CINDY_END = '/ENDING/M_CHR/ED_CHR21.DAT'
FS_CINDY_RACE = '/DATA/CHR/FR/1P/FRFM1.PMD'
FS_FBD = '/ENDING/ENDING.FBD'
# her part -> race object; None: with the board (object 3)
OBJ = {0: 0, 1: 4, 2: 5, 3: 8, 4: 9, 5: 9, 6: 6, 7: 7, 8: 7, 9: 1, 10: 2, 11: 'fz-', 12: 10, 13: 11, 14: 'fz+'}
LIMB = {3, 4, 6, 7, 9, 10, 12, 13}            # parts aligned on their main axis (the others: centre only)
PAL2 = {2, 9, 10, 11, 12, 13, 14}              # parts on the second palette row (hips, legs), as Cindy's ending model


def tmd_parts(archive):
    """[(verts int16[n,3], prims [(mode, words)])] of an ending CHR archive's TMD"""
    n0 = struct.unpack_from('<I', archive, 4)[0]; t = archive[n0 * 4:4 * struct.unpack_from('<I', archive, 8)[0]]
    n = struct.unpack_from('<I', t, 8)[0]; out = []
    for i in range(n):
        vt, nv, nt, nn, pt, np_, sc = struct.unpack_from('<7I', t, 12 + 28 * i)
        V = np.array([struct.unpack_from('<3h', t, 12 + vt + 8 * j) for j in range(nv)], np.int64)
        P = []; o = 12 + pt
        for _ in range(np_):
            ilen = t[o + 1]; w = struct.unpack_from('<%dI' % (ilen + 1), t, o); P.append((w[0] >> 24, w)); o += 4 + 4 * ilen
        out.append((V, P))
    return out


def pmd_objects(d):
    """Cindy's race model: {object: [(block offset, type, n)]}"""
    pp, vp, nobj = struct.unpack_from('<3I', d, 4); o = 16; objs = []
    for i in range(nobj):
        n = struct.unpack_from('<I', d, o)[0]; objs.append(list(struct.unpack_from('<%dI' % n, d, o + 4))); o += 4 + 4 * n
    return objs


PK = {0x12: (0x50, 3), 0x13: (0x68, 4), 0x11: (0x50, 3)}   # packets (2 buffers) bytes, vertices


def block_verts(d, p):
    n, t = struct.unpack_from('<HH', d, p)
    if t not in PK: return t, []
    pk, nv = PK[t]; q = p + 4; V = []
    for k in range(n):
        V.append([struct.unpack_from('<3h', d, q + pk + 8 * j) for j in range(nv)]); q += pk + 8 * nv
    return t, V


def race_targets(d):
    """vertices of each race object of Cindy (boots split by side: 'fz-' / 'fz+')"""
    objs = pmd_objects(d); R = {}
    for i, ptrs in enumerate(objs):
        for p in ptrs:
            t, V = block_verts(d, p)
            n, ty = struct.unpack_from('<HH', d, p)
            if i == 3:
                if ty != 0x12: continue      # board: its own texture page
                for tri in V:
                    k = 'fz+' if np.mean([v[2] for v in tri]) > 0 else 'fz-'
                    R.setdefault(k, []).extend(tri)
            else: R.setdefault(i, []).extend(v for tri in V for v in tri)
    return {k: np.array(v, float) for k, v in R.items()}


def axis(P):
    c = P.mean(0); u, s, vt = np.linalg.svd(P - c, full_matrices=False); a = vt[0]
    return c, a / np.linalg.norm(a)


def arc(a, b):
    """rotation taking unit a onto unit b"""
    v = np.cross(a, b); c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9: return np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K * (1 / (1 + c))


G_ROT = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)   # ending -> race: +z (face) -> +x, +x -> -z


def transforms(cindy_end, race_d):
    """per part of ED_CHRCG: (3x3 matrix, translation) taking ending coordinates to the race pose"""
    E = tmd_parts(cindy_end)[1:]          # Cindy's ending parts without the board (part 0)
    R = race_targets(race_d)
    allE = np.concatenate([v for v, _ in E]).astype(float); allR = np.concatenate([R[k] for k in R]).astype(float)
    s = (allR[:, 1].max() - allR[:, 1].min()) / (allE[:, 1].max() - allE[:, 1].min())
    out = {}
    for i, (V, _) in enumerate(E):
        if i in (11, 14): continue
        tgt = R[OBJ[i]]
        Pg = (V.astype(float) @ G_ROT.T) * s
        cg, ag = axis(Pg); cr, ar = axis(tgt)
        if i in LIMB:
            if np.dot(ag, ar) < 0: ar = -ar
            Ra = arc(ag, ar)
            lg = np.ptp((Pg - cg) @ ag); lr = np.ptp((tgt - cr) @ ar); k = lr / lg
        else: Ra = np.eye(3); k = 1.0
        M = k * Ra @ G_ROT * s
        t = cr - k * Ra @ cg
        out[i] = (M, t)
    out[11], out[14] = out[10], out[13]       # feet: with the shins (the boots of the race model are much higher)
    return out


def params(cindy_end, race_d):
    """the integer form shipped in the package: per part [m00..m22 (x 4096), tx, ty, tz]"""
    T = transforms(cindy_end, race_d)
    return [[int(round(x * 4096)) for x in M.flatten()] + [int(round(x)) for x in t] for M, t in (T[i] for i in range(15))]


def apply(P, v):
    """integer application (patcher): (M v) >> 12 + t, arithmetic shift"""
    m = P[:9]; t = P[9:]
    return [((m[3 * r] * v[0] + m[3 * r + 1] * v[1] + m[3 * r + 2] * v[2]) >> 12) + t[r] for r in range(3)]


# ---------------------------------------------------------------------------------------- lighter mesh for the race
# The race keeps the player's model in a buffer the size of the largest one of the game (Irin's FRFM2.PMD, 41664
# bytes): the ending model is twice that. Each part is simplified by edge collapses (quadric error, onto an existing
# vertex, edges on the part's border kept, no triangle turned over); the package holds the collapses (vertex index
# pairs), the patcher applies them (modular.cg_parts) before making quads.
TARGET = {0: 84, 1: 40, 2: 34, 3: 26, 4: 20, 5: 22, 6: 26, 7: 20, 8: 22, 9: 24, 10: 24, 11: 20, 12: 24, 13: 24, 14: 20}


def collapses(V, T, target):
    """V: int vertices, T: [(a, b, c, uv0, uv1, uv2)] -> [(u, v)] (u replaced by v), until <= target triangles"""
    V = np.array(V, float); tris = [list(t[:3]) for t in T]
    rep = list(range(len(V)))
    def find(x):
        while rep[x] != x: x = rep[x]
        return x
    def live():
        out = []
        for t in tris:
            a, b, c = (find(x) for x in t)
            if a != b and b != c and a != c: out.append((a, b, c))
        return out
    ops = []
    while True:
        L = live()
        if len(L) <= target: break
        # quadrics
        Q = {}
        ec = {}
        for a, b, c in L:
            n = np.cross(V[b] - V[a], V[c] - V[a]); ln = np.linalg.norm(n)
            if ln == 0: continue
            n = n / ln; d = -n @ V[a]; p = np.append(n, d); K = np.outer(p, p)
            for x in (a, b, c): Q[x] = Q.get(x, 0) + K
            for x, y in ((a, b), (b, c), (c, a)): k = (min(x, y), max(x, y)); ec[k] = ec.get(k, 0) + 1
        border = {x for (x, y), n in ec.items() if n == 1 for x in (x, y)}
        best = None
        for (x, y) in sorted(ec):
            for u, v in ((x, y), (y, x)):
                if u in border: continue
                q = Q.get(u, 0) + Q.get(v, 0); h = np.append(V[v], 1); cost = float(h @ q @ h) if not np.isscalar(q) else 0.0
                if best is None or cost < best[0] - 1e-9:
                    # no flip
                    ok = True
                    for a, b, c in L:
                        if u not in (a, b, c) or v in (a, b, c): continue
                        P0 = [V[t] for t in (a, b, c)]; n0 = np.cross(P0[1] - P0[0], P0[2] - P0[0])
                        P1 = [V[v] if t == u else V[t] for t in (a, b, c)]; n1 = np.cross(P1[1] - P1[0], P1[2] - P1[0])
                        if np.linalg.norm(n1) == 0 or n0 @ n1 <= 0.2 * np.linalg.norm(n0) * np.linalg.norm(n1): ok = False; break
                    if ok: best = (cost, u, v)
        if best is None: break
        rep[best[1]] = best[2]; ops.append([best[1], best[2]])
    return ops


def decimation(cg_archive):
    import modular
    parts = modular.cg_parts(cg_archive)
    return [collapses(V, T, TARGET[i]) for i, (V, T) in enumerate(parts)]
