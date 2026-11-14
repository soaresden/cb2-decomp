# Snowman in the competition (part of the mod `riders`, v29): his own animations (TOD_SM) and his own hierarchy instead
# of the human ones.
#
# The competition loads one human TOD (TOD_MANx, 100 motions) at the 1st stage, at 0x80195394, for every rider; the
# Snowman model (7 objects) then got the first bones of a human ("badly assembled", leaning). Free Style loads TOD_SM
# (46 motions) too and gives the player a motion table (rider + 0x204, 100 words: motion start + 8) whose human motion
# numbers are mapped onto Snowman's (MAP, read in the emulator from a Free Style race with Snowman).
#   exe: the competition loader func_8001CCE0 queues its files with func_80013BD0 (file, dest, &ptr, flags); its call at
#        0x8001D014 goes to `tsm`, which also queues TOD_SM (file 237) into the heap (dest 0) when g_rider = 6, its
#        address into TSM_PTR. That is only the first 1st stage now (v33): SBC1's start (`hins`) copies `hlp` to free
#        RAM and the loader's call goes there: 1st stage (and its 2nd try): TOD_SM whole into the heap (SBC1 has ~600 KB
#        free); Boarder Cross: a packed TOD_SM (`pack`: the motions the race plays, without the packets that repeat the
#        setup's) in two files at the end of the credits movie, A (32 KB) at 0x801F4000 (free RAM, not the heap) and B
#        (5 KB) into the heap. The whole file (82 KB) did not fit in the heap of rounds 3, 6, 7 (the game stops on a
#        `break` in malloc: frozen loading screen); during the loading of round 6 only ~15 KB stay free.
#   SBC1 / SBC2 (OVLS): calls made every frame go to `snw` first (SBC2: the race loop's call of the bar function; SBC1:
#        the calls of the TOD frame player): when g_rider = 6 and TOD_SM is there, it is converted once with the
#        overlay's own routines (header: offsets -> addresses, then every motion, as FREE.BIN's func_8008F878 /
#        func_80095F98 do for its TODs), then every frame:
#        - the player's three motion tables (rider + 0x204: motion + 8, + 0x39C: its frame count, + 0x530: its first
#          frame's number, as the racer init func_80064674 makes them) are written from MAP (with the first table only,
#          the TOD player ran off the end of Snowman's shorter motions: address error at 0x8008C278);
#        - Snowman's hierarchy (HIER) is put back: the rider's objects and bones (list at rider + 0x1E4: 0x18-byte
#          entries, GsCOORDINATE2 at +4, id at +0x14) got their parents from the human TOD's setup motion (motion 0:
#          "create" and "parent" packets for ids 5..0x1C), so TOD_SM's bones 12..18 moved human bones and the 7 pieces
#          flew apart, huge, around the camera. Each object/bone 5..18 gets its parent of Free Style (super, +0x48),
#          bone 12 the rider's root (rider + 0x1D4), and bone 12 is put 100 lower (ROOT_Y, as Free Style does: without it he
#          floated above his shadow). The human bones 19..28 stay, unused, under Snowman's.
import struct
from asm import asm

EXE_BASE, OVL = 0x8000F800, 0x8005AEA8
QUEUE, LOAD_SITE = 0x80013BD0, 0x8001D014
TOD_SM_FILE = 237
EXE_CAVE, EXE_CAVE_END = 0x8003EB30, 0x8003EB80          # end of the dead function func_8003EAC4 (its start: options)
TSM_PTR = EXE_CAVE_END - 4
G_RIDER = 0x80057408
# per overlay: detailed riders ([0] = the player), the TOD conversion routines, a dead function (code + tables),
# the call that goes through `snw` first (site -> tail)
OVLS = {
    # Boarder Cross: the race loop's call of the bar function
    'SBC2': dict(riders=0x8009B9A8, hdr=0x8008655C, mot=0x8008CC7C, cave=0x80062DB4, cave_end=0x8006304C,
                 sites=[0x8005F56C], tail=0x8006D2A4, todf=0x8008C254, packed=True),
    # 1st stage (tricks): the two calls of the TOD frame player func_80089AB8 (its stack arguments stay in place):
    # func_80064ACC (the start of a motion) and the playback of every frame
    'SBC1': dict(riders=0x80090DF0, hdr=0x80083DC0, mot=0x8008A4E0, cave=0x80061018, cave_end=0x800612B0,
                 sites=[0x80064B30, 0x80065150], tail=0x80089AB8, todf=0x80089AB8),
}
MAP = [0, 1, 2, 3, 4, 5, 6, 7, 6, 8, 9, 8, 9, 6, 7, 8, 9, 3, 4, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
       26, 27, 28, 29, 30, 31, 3, 3, 1, 2, 3, 4, 5, 32, 33, 32, 8, 9, 8, 9, 32, 33, 8, 9, 3, 4, 43, 44, 45, 13, 14, 15, 16, 17,
       18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 28, 31, 30, 3, 3, 39, 40, 41, 42, 37, 38, 37, 38, 37, 38, 34, 35, 36, 35, 36]
assert len(MAP) == 100
# his base bone: TOD_SM's setup puts it 119 below the rider's root (y down); Free Style has it 100 lower, on the snow
# (the game puts that height back every frame). In the competition he floated 100 units above his shadow.
ROOT_BONE, ROOT_Y = 12, 219
# Boarder Cross: TOD_SM packed (v33) in two parts, A in free RAM (not the heap), B in the heap: the whole file (82 KB)
# did not fit in the heap of the bigger courses (rounds 3, 6, 7: 62, 40, 51 KB free; the game stops on `break` in its
# malloc func_8001F270 when a file does not fit: frozen loading screen)
PACK_A, PACK_A_MAX = 0x801F4000, 0x8000          # free RAM in every scene (0x801F4000..0x801FC000; the stack: down to 0x801FDBC0)
B_PTR = 0x801F3FF0                               # B's address (heap), written by the loader
HELPER = 0x801F3000                              # `hlp`, copied there by SBC1 (free RAM between the switches' block and NEXT)
# Boarder Cross: Snowman's motions the race never played in the emulator (game motions sampled every 4 frames over
# races with all the buttons, 4 riders and courses: 1..13, 20, 21, 25, 36..57, 63, 65, 78..85, 94, 95) are left out,
# their entries go to kept ones (tricks -> tricks 13 / 15, end poses -> end poses 37 / 38, ...): 82 KB -> 40 KB
DROP = {12: 13, 14: 13, 16: 13, 17: 15, 18: 13, 19: 15, 20: 13, 21: 15, 22: 13, 23: 15, 24: 13, 25: 15,
        28: 30, 29: 31, 34: 37, 35: 38, 36: 37, 39: 38, 40: 38, 41: 37, 42: 37, 43: 44, 45: 44}
FILE_TABLE = 0x800583E8                          # the exe's file table (8 bytes: MSF, size)
INSTALL_SITE, INSTALL_TAIL = 0x8005AF5C, 0x800127C0       # SBC1 entry: jal func_800127C0 (every start of SBC1)
INSTALL_CAVE, INSTALL_CAVE_END = 0x8006AF10, 0x8006B2F4   # dead function of SBC1
FLUSH = 0x8003CB2C


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)
def J(op, t): return (op << 26) | ((t >> 2) & 0x3ffffff)


def exe_code():
    S = ['tsm:', 'addiu sp, sp, -0x18', 'sw ra, 0x10(sp)', f'jal {QUEUE}', 'nop',
         'lui t0, 0x8005', f'lh t0, {G_RIDER & 0xffff:#x}(t0)', 'addiu t1, zero, 6', 'bne t0, t1, ts9', 'nop',
         f'addiu a0, zero, {TOD_SM_FILE}', 'move a1, zero', f'lui a2, {H(TSM_PTR)}', f'addiu a2, a2, {L(TSM_PTR)}', f'jal {QUEUE}', 'addiu a3, zero, 1',
         'ts9:', 'lw ra, 0x10(sp)', 'nop', 'jr ra', 'addiu sp, sp, 0x18']
    c, l = asm(S, EXE_CAVE)
    assert c[-1][0] < TSM_PTR, hex(c[-1][0])
    return c, l


def pack(disc):
    """TOD_SM packed: the setup motion 0 as it is; in the other motions the parent and attribute packets of frame 0
    (the same as the setup's: checked) are left out; DROP motions left out (their entries point to others).
    -> (A pieces, A size, B pieces, B size); pieces: ('c', disc address, length) | ('l', bytes)
    A: 'TP', 1 (not converted yet), count, entries (offset in A, or 0x80000000 | offset in B), then motions"""
    lba, size, _ = disc.files['/DATA/CHR/TOD_SM.DAT']; d = disc.read_file('/DATA/CHR/TOD_SM.DAT'); base = lba * 2048
    n = d[3]; offs = [struct.unpack_from('<I', d, 4 + 4 * i)[0] * 4 for i in range(n)] + [len(d)]
    def frames(o):
        nfr = struct.unpack_from('<I', d, o + 4)[0]; return nfr, [struct.unpack_from('<I', d, o + 8 + 4 * f)[0] for f in range(nfr)]
    def packets(p):
        sz, npk, fno = struct.unpack_from('<HHI', d, p); q = p + 8; out = []
        for _ in range(npk):
            w = struct.unpack_from('<I', d, q)[0]; out.append((q, w >> 24 << 2, w & 0xffff, (w >> 16) & 15)); q += (w >> 24) * 4
        assert q == p + sz * 4
        return fno, out
    _, f0 = frames(offs[0]); _, setup = packets(offs[0] + f0[0])
    sp = {(i, t): d[q:q + ln] for q, ln, i, t in setup}
    motions = {}
    for m in range(n):
        o = offs[m]
        if m in DROP: continue
        if m == 0: motions[m] = ([('c', base + o, offs[1] - o)], offs[1] - o); continue
        nfr, fo = frames(o); fno, pk = packets(o + fo[0])
        keep = [(q, ln) for q, ln, i, t in pk if not (t in (0, 3) and sp.get((i, t)) == d[q:q + ln])]
        cut = sum(ln for q, ln, i, t in pk) - sum(ln for q, ln in keep)
        hdr = d[o:o + 8] + b''.join(struct.pack('<I', x - (cut if f else 0)) for f, x in enumerate(fo))
        f0len = 8 + sum(ln for q, ln in keep)
        pieces = [('l', hdr), ('l', struct.pack('<HHI', f0len // 4, len(keep), fno))]
        for q, ln in keep:
            if pieces[-1][0] == 'c' and pieces[-1][1] + pieces[-1][2] == base + q: pieces[-1] = ('c', pieces[-1][1], pieces[-1][2] + ln)
            else: pieces.append(('c', base + q, ln))
        rest = o + fo[1] if nfr > 1 else offs[m + 1]
        assert fo[0] == 8 + 4 * nfr
        if offs[m + 1] > rest: pieces.append(('c', base + rest, offs[m + 1] - rest))
        motions[m] = (pieces, len(hdr) + f0len + offs[m + 1] - rest)
    hsize = 4 + 4 * n; a_at = hsize; b_at = 0; ent = [0] * n; A = []; B = []
    for m in range(n):
        if m in DROP: continue
        pcs, ln = motions[m]
        if a_at + ln <= PACK_A_MAX: ent[m] = a_at; A += pcs; a_at += ln
        else: ent[m] = 0x80000000 | b_at; B += pcs; b_at += ln
    for m, k in DROP.items(): ent[m] = ent[k]
    A = [('l', b'TP' + bytes([1, n]) + struct.pack('<%dI' % n, *ent))] + A
    return A, a_at, B, b_at


def sectors(pieces, total):
    """pieces -> sector ops ([[0, len, addr] | [1, hex]] per 2048 bytes), zeros up to whole sectors"""
    flat = list(pieces); n = -(-total // 2048); pad = n * 2048 - total
    if pad: flat.append(('l', bytes(pad)))
    secs = []; cur = []; room = 2048
    for p in flat:
        if p[0] == 'c':
            a, ln = p[1], p[2]
            while ln:
                k = min(ln, room)
                if cur and cur[-1][0] == 0 and cur[-1][2] + cur[-1][1] == a: cur[-1][1] += k
                else: cur.append([0, k, a])
                a += k; ln -= k; room -= k
                if not room: secs.append(cur); cur = []; room = 2048
        else:
            b = p[1]
            while b:
                k = min(len(b), room)
                if cur and cur[-1][0] == 1: cur[-1][1] += b[:k].hex()
                else: cur.append([1, b[:k].hex()])
                b = b[k:]; room -= k
                if not room: secs.append(cur); cur = []; room = 2048
    assert not cur and len(secs) == n
    return secs


def helper_code(fa, fb):
    """`hlp` (at HELPER, in place of the loader's queue call at LOAD_SITE; s3 = func_8001CCE0's a3, as given to
    func_8001C748: 0 = 1st stage from the menu, 1 = the 1st stage again (2nd try), 2 = the Boarder Cross): 0 and 1:
    TOD_SM whole into the heap, as `tsm`; 2: packed A at PACK_A and B into the heap.
    fa, fb: the file entries (MSF + size) of A and B, after the code"""
    def code(ea, eb):
        ia = (ea - FILE_TABLE) // 8; ib = (eb - FILE_TABLE) // 8
        return ['hlp:', 'addiu sp, sp, -0x20', 'sw ra, 0x18(sp)', f'jal {QUEUE}', 'nop',
                'lui t0, 0x8005', f'lh t1, {G_RIDER & 0xffff:#x}(t0)', 'addiu at, zero, 6', 'bne t1, at, h9', 'addiu at, zero, 2',
                'beq s3, at, hb', 'nop',
                f'addiu a0, zero, {TOD_SM_FILE}', 'move a1, zero', f'lui a2, {H(TSM_PTR)}', f'addiu a2, a2, {L(TSM_PTR)}',
                f'jal {QUEUE}', 'addiu a3, zero, 1', 'j h9', 'nop',
                'hb:', f'lui a0, {ia >> 16:#x}', f'ori a0, a0, {ia & 0xffff:#x}', f'lui a1, {PACK_A >> 16:#x}', f'ori a1, a1, {PACK_A & 0xffff:#x}',
                f'lui a2, {B_PTR >> 16:#x}', f'ori a2, a2, {(B_PTR + 4) & 0xffff:#x}', f'jal {QUEUE}', 'addiu a3, zero, 1',
                f'lui a0, {ib >> 16:#x}', f'ori a0, a0, {ib & 0xffff:#x}', 'move a1, zero',
                f'lui a2, {B_PTR >> 16:#x}', f'ori a2, a2, {B_PTR & 0xffff:#x}', 'sw zero, 0(a2)', f'jal {QUEUE}', 'addiu a3, zero, 1',
                'h9:', 'lw ra, 0x18(sp)', 'nop', 'jr ra', 'addiu sp, sp, 0x20']
    c0, _ = asm(code(HELPER, HELPER), HELPER)
    ea = (c0[-1][0] + 4 + 7) & ~7; eb = ea + 8
    assert (ea - FILE_TABLE) % 8 == 0
    c, l = asm(code(ea, eb), HELPER)
    words = [w for _, w in c]
    while HELPER + 4 * len(words) < ea: words.append(0)
    words += list(struct.unpack('<4I', fa + fb))
    return words


def install_code(img):
    """`hins` (SBC1, at every start of SBC1): `hlp` copied to HELPER, and the loader's call (jal tsm in the exe) goes
    to it (FlushCache then); the call it replaces (func_800127C0) at the end"""
    tsm_call = J(3, exe_code()[1]['tsm'])
    S = ['hins:', 'addiu sp, sp, -0x20', 'sw ra, 0x18(sp)', 'sw a0, 0x10(sp)', 'sw a1, 0x14(sp)',
         'lui t0, IMGH', 'addiu t0, t0, IMGL', f'lui t1, {HELPER >> 16:#x}', f'ori t1, t1, {HELPER & 0xffff:#x}', f'addiu t2, t0, {4 * len(img)}',
         'hi1:', 'lw t3, 0(t0)', 'addiu t0, t0, 4', 'sw t3, 0(t1)', 'bne t0, t2, hi1', 'addiu t1, t1, 4',
         f'lui t0, {H(LOAD_SITE)}', f'lw t1, {L(LOAD_SITE)}(t0)', f'lui t2, {tsm_call >> 16:#x}', f'ori t2, t2, {tsm_call & 0xffff:#x}',
         'bne t1, t2, hi9', f'lui t2, {J(3, HELPER) >> 16:#x}', f'ori t2, t2, {J(3, HELPER) & 0xffff:#x}', f'sw t2, {L(LOAD_SITE)}(t0)',
         f'jal {FLUSH}', 'nop',
         'hi9:', 'lw a0, 0x10(sp)', 'lw a1, 0x14(sp)', 'lw ra, 0x18(sp)', f'j {INSTALL_TAIL}', 'addiu sp, sp, 0x20']
    c0, _ = asm([x.replace('IMGH', '0').replace('IMGL', '0') for x in S], INSTALL_CAVE)
    ia = c0[-1][0] + 4
    c, l = asm([x.replace('IMGH', str(H(ia))).replace('IMGL', str(L(ia))) for x in S], INSTALL_CAVE)
    c += [(ia + 4 * k, w) for k, w in enumerate(img)]
    assert c[-1][0] < INSTALL_CAVE_END, hex(c[-1][0])
    return c, l


def conv_whole(HDR_RELOC, MOT_RELOC):
    """s0 = TOD_SM (heap, TSM_PTR), converted once with the overlay's routines"""
    return [f'lui t0, {H(TSM_PTR)}', f'lw s0, {L(TSM_PTR)}(t0)', 'nop', 'beqz s0, sn9', 'nop',
            'lhu t0, 0(s0)', 'addiu t1, zero, 0x4f54', 'bne t0, t1, sn9', 'nop',                 # "TO"
            'lbu t0, 2(s0)', 'nop', 'beqz t0, sn2', 'nop',                                       # not converted yet
            f'jal {HDR_RELOC}', 'move a0, s0', 'lbu s1, 3(s0)', 'nop',
            'sn1:', 'sll t0, s1, 2', 'addu t0, t0, s0', 'lw a0, 0(t0)', f'jal {MOT_RELOC}', 'nop', 'addiu s1, s1, -1', 'bnez s1, sn1', 'nop']


def conv_packed(MOT_RELOC):
    """s0 = packed A (PACK_A), B at *B_PTR: entries -> addresses, every motion converted, once (A is loaded again
    for every Boarder Cross)"""
    return [f'lui s0, {PACK_A >> 16:#x}', f'ori s0, s0, {PACK_A & 0xffff:#x}',
            'lhu t0, 0(s0)', 'addiu t1, zero, 0x5054', 'bne t0, t1, sn9', 'nop',                 # "TP"
            f'lui t0, {B_PTR >> 16:#x}', f'lw t0, {B_PTR & 0xffff:#x}(t0)', 'nop', 'beqz t0, sn9', 'nop',
            'lbu t0, 2(s0)', 'nop', 'beqz t0, sn2', 'nop',                                       # not converted yet
            'lbu s1, 3(s0)', 'nop',
            'sn1:', 'sll t0, s1, 2', 'addu t0, t0, s0', 'lw a0, 0(t0)', 'nop', 'bgez a0, snA', 'addu a0, a0, s0',
            'subu a0, a0, s0', 'sll a0, a0, 1', 'srl a0, a0, 1', f'lui t1, {B_PTR >> 16:#x}', f'lw t1, {B_PTR & 0xffff:#x}(t1)', 'nop', 'addu a0, a0, t1',
            'snA:', 'sw a0, 0(t0)', f'jal {MOT_RELOC}', 'nop', 'addiu s1, s1, -1', 'bnez s1, sn1', 'nop', 'sb zero, 2(s0)']


def sbc_code(name):
    o = OVLS[name]
    RIDERS, HDR_RELOC, MOT_RELOC, CAVE, CAVE_END, TAIL, TODF = (o[k] for k in ('riders', 'hdr', 'mot', 'cave', 'cave_end', 'tail', 'todf'))
    S = ['snw:', 'addiu sp, sp, -0x40', 'sw ra, 0x30(sp)', 'sw s0, 0x18(sp)', 'sw s1, 0x1c(sp)', 'sw a0, 0x20(sp)', 'sw a1, 0x24(sp)',
         'sw a2, 0x28(sp)', 'sw a3, 0x2c(sp)',
         'lui t0, 0x8005', f'lh t0, {G_RIDER & 0xffff:#x}(t0)', 'addiu t1, zero, 6', 'bne t0, t1, sn9', 'nop',
         *(conv_packed(MOT_RELOC) if o.get('packed') else conv_whole(HDR_RELOC, MOT_RELOC)),
         # the player's motion table from MAP (its entry 0 = the game's motion 1, played at the start: the setup)
         'sn2:', f'lui t0, {H(RIDERS)}', f'lw s1, {L(RIDERS)}(t0)', 'nop', 'beqz s1, sn9', 'addiu t0, s1, 0x204',
         'lui t1, MAPH', 'addiu t1, t1, MAPL', 'addiu t2, t1, 100',
         'sn3:', 'lbu t3, 0(t1)', 'addiu t1, t1, 1', 'sll t3, t3, 2', 'addu t3, t3, s0', 'lw t3, 4(t3)', 'nop',
         'lw t4, 4(t3)', 'lw t5, 8(t3)', 'addiu t3, t3, 8', 'lw t5, 4(t5)', 'sw t3, 0(t0)', 'sw t4, 0x198(t0)', 'sw t5, 0x32c(t0)',
         'bne t1, t2, sn3', 'addiu t0, t0, 4',
         # still the human setup (bone 17 under the human root instead of object 8)? then TOD_SM's setup frame, with the
         # overlay's TOD frame player and the arguments of the racer init (func_800667CC: object table = rider + 0x1E4)
         'lw t8, 0x1e4(s1)', 'nop', 'beqz t8, sn9', 'nop',
         'jal fnd', 'addiu a0, zero, 8', 'move t6, v0', 'jal fnd', 'addiu a0, zero, 17', 'beqz v0, sn9', 'nop',
         'lw t0, 0x48(v0)', 'nop', 'beq t0, t6, sn5', 'nop',
         'lw t0, 0x1f0(s1)', 'sw zero, 0x14(sp)', 'sw t0, 0x10(sp)', 'lw t0, 0x204(s1)', 'lw a0, 0x530(s1)', 'lw a1, 0(t0)',
         'addiu a2, s1, 0x1e4', f'jal {TODF}', 'lw a3, 0x394(s1)',
         # bone 12 under the rider's root (the setup leaves it without a parent) and as low as in Free Style
         'sn5:', 'lw t8, 0x1e4(s1)', 'nop', 'jal fnd', f'addiu a0, zero, {ROOT_BONE}', 'beqz v0, sn9', 'nop',
         'lw t0, 0x1d4(s1)', f'addiu t1, zero, {ROOT_Y}', 'sw t0, 0x48(v0)', 'sw t1, 0x1c(v0)',
         # and it is the bone whose height the game puts back every frame (rider + 0x6D4: the bone, + 0x6D0: its height;
         # set once after the setup, by func_80066894: the human pelvis, id 17 = Snowman's right arm)
         'sw v0, 0x6d4(s1)', 'j sn9', 'sh t1, 0x6d0(s1)',
         # coordinate of the object/bone a0 in the rider's object list (t8), 0 if none
         'fnd:', 'move t1, t8',
         'fn1:', 'lw t2, 0x14(t1)', 'addiu at, zero, -1', 'beq t2, at, fn9', 'move v0, zero', 'bne t2, a0, fn1', 'addiu t1, t1, 0x18',
         'lw v0, -0x14(t1)', 'fn9:', 'jr ra', 'nop',
         'sn9:', 'lw a0, 0x20(sp)', 'lw a1, 0x24(sp)', 'lw a2, 0x28(sp)', 'lw a3, 0x2c(sp)', 'lw s0, 0x18(sp)', 'lw s1, 0x1c(sp)',
         'lw ra, 0x30(sp)', f'j {TAIL}', 'addiu sp, sp, 0x40']
    c0, _ = asm([x.replace('MAPH', '0').replace('MAPL', '0') for x in S], CAVE)
    mp = c0[-1][0] + 4
    S = [x.replace('MAPH', str(H(mp))).replace('MAPL', str(L(mp))) for x in S]
    c, l = asm(S, CAVE)
    m = bytes(MAP)
    m += bytes((-len(m)) % 4)
    c += [(mp + i, struct.unpack_from('<I', m, i)[0]) for i in range(0, len(m), 4)]
    assert c[-1][0] < CAVE_END, hex(c[-1][0])
    return c, l


def ops(disc):
    exe = disc.read_file('/SCES_009.92')
    we = lambda a: struct.unpack_from('<I', exe, a - EXE_BASE)[0]
    assert we(LOAD_SITE) == J(3, QUEUE)
    tsm = disc.read_file('/DATA/CHR/TOD_SM.DAT'); m0 = struct.unpack_from('<I', tsm, 4)[0] * 4
    assert tsm[:3] == b'TO2' and struct.unpack_from('<I', tsm, m0 + 4)[0] == 1     # the setup motion: one frame (snw plays one)
    ce, le = exe_code()
    out = [['w', '/SCES_009.92', a - EXE_BASE, we(a), x] for a, x in ce + [(LOAD_SITE, J(3, le['tsm'])), (TSM_PTR, 0)]]
    # packed TOD_SM for the Boarder Cross: two files at the end of the credits movie (voices.layout), `hlp` and `hins`
    import voices
    from iso import msf_bcd
    lay = voices.layout(disc); A, la, B, lb = pack(disc)
    for p, ln, lba in ((A, la, lay['tsmA']), (B, lb, lay['tsmB'])):
        secs = sectors(p, ln)
        for i, sec in enumerate(secs):
            out.append(['sec', lba + i, (bytes([0, 0, 0x89 if i == len(secs) - 1 else 0x08, 0]) * 2).hex(), sec])
    img = helper_code(msf_bcd(lay['tsmA']) + struct.pack('<I', la), msf_bcd(lay['tsmB']) + struct.pack('<I', lb))
    assert HELPER + 4 * len(img) <= B_PTR and PACK_A + la <= PACK_A + PACK_A_MAX
    s1 = disc.read_file('/SBC1.BIN'); w1 = lambda a: struct.unpack_from('<I', s1, a - OVL)[0]
    assert w1(INSTALL_SITE) == J(3, INSTALL_TAIL) and w1(INSTALL_CAVE) == 0x27BDFF70, hex(w1(INSTALL_CAVE))
    ci, li = install_code(img)
    out += [['w', '/SBC1.BIN', a - OVL, w1(a), x] for a, x in ci + [(INSTALL_SITE, J(3, li['hins']))]]
    for name, o in OVLS.items():
        f = '/' + name + '.BIN'; sb = disc.read_file(f)
        ws = lambda a: struct.unpack_from('<I', sb, a - OVL)[0]
        assert all(ws(a) == J(3, o['tail']) for a in o['sites']), name
        assert sb[o['hdr'] - OVL:o['hdr'] - OVL + 8] == bytes.fromhex('0200829003008790') and ws(o['mot'] + 8) == 0x24020002, name
        assert ws(o['cave']) == 0x27BDFFC0, name                   # the dead function's addiu sp, sp, -0x40
        cs, ls = sbc_code(name)
        out += [['w', f, a - OVL, ws(a), x] for a, x in cs + [(a, J(3, ls['snw'])) for a in o['sites']]]
    return out


def merge(disc, riders_ops):
    """riders' ops with these (earlier ones of this module replaced)"""
    new = ops(disc)
    wk = {(op[1], op[2]) for op in new if op[0] == 'w'}; sk = {op[1] for op in new if op[0] == 'sec'}
    return [op for op in riders_ops if not ((op[0] == 'w' and (op[1], op[2]) in wk) or (op[0] == 'sec' and op[1] in sk))] + new
