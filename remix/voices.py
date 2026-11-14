# Gray and Snowman's own voices in the Boarder Cross (part of the mod `riders`, v32).
#
# SBC2 loads one rider voice bank per race: sound sets 35..38 (SBC2ND0..3: Yaggi, Jin, Cindy, Irin; 48 samples, the
# announcer and the noises 0..33, the rider's clips 34..47). The Remix gave Boss a bank of his own (Yaggi's with his
# clips swapped for Boss's: remix.py boss_course_bank, `bsnd` at 0x80090300 overrides set 35's entry, file index and
# offsets, at 0x80047E3C); Gray and Snowman took Jin's and Yaggi's banks: Snowman had Yaggi's voice.
# Here, the same for them: Yaggi's bank with his clips swapped for theirs, taken from their Big Air banks (SBC1ST5 /
# SBC1ST6, the same 47-sample layout as SBC1ST0: 2 cries each, the other clips are silences); the free-ride clip
# (sample 38) is a silence (their free-ride banks have no such clip). Both banks have the same layout (each sample
# padded to the longer of the two), so one offset table serves both.
#   disc: the two banks go just before the last RESERVE sectors of the credits movie STAFFE.STR (kept for MODE_SEL,
#         moved there when it grows), which is cut accordingly (about 1.4 s). Built from copies of the player's disc.
#   SBC2: the call of `bsnd` (0x80066CB4) goes to `vsnd` in the dead function func_80070E9C: Boss as before, Gray and
#         Snowman get their bank (file entry: MSF + size, in the same place) and the shared offset table.
import json, os, struct
from asm import asm
from iso import msf_bcd

OVL = 0x8005AEA8
SITE = 0x80066CB4                      # jal bsnd (Boss's bank, remix.py)
FILE_TABLE = 0x800583E8                # the exe's file table (8-byte entries: MSF, size)
BOSS_FE, BOSS_TB = 0x80090350, 0x80090358
CAVE, CAVE_END = 0x80070EA0, 0x80070E9C + 0x278          # dead function func_80070E9C (entries 8-byte aligned)
ND0 = 0x23                              # sound set of SBC2ND0
ST = {5: 0x21, 6: 0x22}                 # Big Air banks of Gray / Snowman
M = {34: 33, 35: 34, 36: 35, 37: 36, 39: 37, 40: 38, 41: 39, 42: 40, 43: 41, 45: 43, 46: 44, 47: 45}   # as Boss's
FR_CLIP, SILENT = 38, 44               # Yaggi's free-ride clip; a silent sample of SBC2ND0 (48 bytes)
RESERVE = 96                            # last sectors of STAFFE.STR left to MODE_SEL
FILES = {0x23: '/SOUND/SBC/SBC2ND0.VB', 0x21: '/SOUND/SBC/SBC1ST5.VB', 0x22: '/SOUND/SBC/SBC1ST6.VB'}


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)
def J(op, t): return (op << 26) | ((t >> 2) & 0x3ffffff)


def _sets():
    T = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sndsets.json')))
    return {int(k): v for k, v in T.items()}


def banks(disc):
    """-> ({rider: [(disc address, length) or (None, zeros)...]}, sample offsets[49], total size)"""
    T = _sets()
    def samples(s):
        lba, size, _ = disc.files[FILES[s]]; o = T[s][1]
        assert o[-1] == size, (s, o[-1], size)
        return [(lba * 2048 + o[i], o[i + 1] - o[i]) for i in range(len(o) - 1)]
    nd0 = samples(ND0)
    assert nd0[SILENT][1] == 48
    parts = {}
    for r, s in ST.items():
        st = samples(s); p = list(nd0)
        for i, j in M.items(): p[i] = st[j]
        p[FR_CLIP] = nd0[SILENT]
        parts[r] = p
    lens = [max(parts[r][i][1] for r in parts) for i in range(len(nd0))]
    lens = [n + (-n) % 16 for n in lens]                  # ADPCM blocks
    offs = [0]
    for n in lens: offs.append(offs[-1] + n)
    out = {}
    for r, p in parts.items():
        out[r] = [x for (a, n), ln in zip(p, lens) for x in ([(a, n)] + ([(None, ln - n)] if ln > n else []))]
    return out, offs, offs[-1]


def _sectors(pieces, total):
    """pieces -> sector ops ([[0, len, addr] | [1, hex]] per 2048 bytes), zeros up to whole sectors"""
    flat = list(pieces); n = -(-total // 2048); pad = n * 2048 - total
    if pad: flat.append((None, pad))
    secs = []; cur = []; room = 2048
    for a, ln in flat:
        while ln:
            k = min(ln, room)
            if a is None:
                if cur and cur[-1][0] == 1: cur[-1][1] += '00' * k
                else: cur.append([1, '00' * k])
            else:
                if cur and cur[-1][0] == 0 and cur[-1][2] + cur[-1][1] == a: cur[-1][1] += k
                else: cur.append([0, k, a])
                a += k
            ln -= k; room -= k
            if not room: secs.append(cur); cur = []; room = 2048
    assert not cur and len(secs) == n
    return secs


def sbc2_code(fe, tb):
    bidx = (fe - FILE_TABLE) // 8; bboss = (BOSS_FE - FILE_TABLE) // 8
    assert (fe - FILE_TABLE) % 8 == 0 and (BOSS_FE - FILE_TABLE) % 8 == 0 and bidx + 1 < 0x8000
    S = ['vsnd:', 'lui t0, 0x8004', 'addiu t1, zero, 0x38', 'lui t2, 0x8004', 'ori t2, t2, 0x69c4',
         'slti at, v0, 4', 'bnez at, vs0', 'addiu at, zero, 4', 'bne v0, at, vs2', 'nop',
         f'addiu t1, zero, {bboss}', f'lui t2, {BOSS_TB >> 16:#x}', f'ori t2, t2, {BOSS_TB & 0xffff:#x}', 'j vs0', 'nop',
         'vs2:', f'addiu t1, v0, {bidx - 5}', f'lui t2, {tb >> 16:#x}', f'ori t2, t2, {tb & 0xffff:#x}',
         'vs0:', 'sw t1, 0x7e3c(t0)', 'sw t2, 0x7e40(t0)', 'slti at, v0, 4', 'bnez at, vs1', 'nop', 'move v0, zero',
         'vs1:', 'sll v0, v0, 1', 'jr ra', 'addu v0, v0, a0']
    return asm(S, tb + 4 * 49)


def ops(disc, riders_ops):
    """the bank sectors, STAFFE's record, the SBC2 table and code; riders_ops: the call of bsnd is repointed there"""
    parts, offs, total = banks(disc)
    n = -(-total // 2048)
    sl, ss, _ = disc.files['/MOVIE/STAFFE.STR']; sn = ss // 2048
    first = sl + sn - RESERVE - 2 * n
    out = [['rec', '/MOVIE/STAFFE.STR', sl, (sn - RESERVE - 2 * n) * 2048]]
    lbas = {}
    for k, r in enumerate(sorted(parts)):
        lbas[r] = first + k * n
        for i, sec in enumerate(_sectors(parts[r], total)):
            sub = bytes([0, 0, 0x89 if i == n - 1 else 0x08, 0]) * 2
            out.append(['sec', lbas[r] + i, sub.hex(), sec])
    fe = CAVE; tb = fe + 16
    data = b''.join(msf_bcd(lbas[r]) + struct.pack('<I', total) for r in sorted(parts)) + struct.pack('<49I', *offs)
    c, l = sbc2_code(fe, tb)
    sb = disc.read_file('/SBC2.BIN'); ws = lambda a: struct.unpack_from('<I', sb, a - OVL)[0]
    words = [(fe + i, struct.unpack_from('<I', data, i)[0]) for i in range(0, len(data), 4)] + c
    assert words[-1][0] < CAVE_END and ws(0x80070E9C) == 0x27BDFFB0, hex(words[-1][0])
    out += [['w', '/SBC2.BIN', a - OVL, ws(a), x] for a, x in words]
    site = [op for op in riders_ops if op[0] == 'w' and op[1] == '/SBC2.BIN' and op[2] == SITE - OVL]
    assert len(site) == 1 and site[0][4] in (J(3, 0x80090300), J(3, l['vsnd'])), site
    return out, [SITE - OVL, J(3, l['vsnd'])]


def merge(disc, riders_ops):
    """riders' ops with these (again: earlier ones of this module replaced)"""
    vo, (site, new) = ops(disc, riders_ops)
    keys = {(op[0], op[1], op[2]) for op in vo if op[0] in ('w', 'sec')} | {('sec', op[1], None) for op in vo if op[0] == 'sec'}
    out = []
    for op in riders_ops:
        if op[0] == 'w' and ('w', op[1], op[2]) in keys: continue
        if op[0] == 'sec' and ('sec', op[1], None) in keys: continue
        if op[0] == 'rec' and op[1] == '/MOVIE/STAFFE.STR': continue
        if op[0] == 'w' and op[1] == '/SBC2.BIN' and op[2] == site: op = op[:4] + [new]
        out.append(op)
    return out + vo
