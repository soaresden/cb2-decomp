# The end of the Competition with Boss, Gray or Snowman (part of the mod `riders`, v85).
#
# The ending (ENDING.BIN) announces the champion with the sound bank VOENDING (sound set 42, file 0x3F, played at
# 16 kHz: pitch 0x5CE of the set table 0x80047C0C): samples 0..3 the names Yaggi, Jin, Cindy, Irin, 4..6 "first",
# "second", "third", 7..10 the riders' celebrations ("yaaah", "yoshaa", "what did you expect", "yahoo"). It plays
# sample g_rider (0x8005C650) then sample g_rider + 7 (0x8005C6D8) with func_80015EA4 (sample of the second bank, at the
# bank's pitch D_80058300). For Boss, Gray, Snowman (riders 4..6) that gave "first / second / third" and then samples
# 11..13 that do not exist.
# Now: VOENDING gets four more samples at its end, copied from the player's disc: the announcer's "great" (SBC2ND0,
# sample 12) and a cry of Boss, Gray, Snowman (their Big Air banks SBC1ST4 / 5 / 6), all played at 6 kHz (pitch
# 0x22D, their banks'). The bank is sent to the sound memory up to the last offset of its table: that word of the exe
# (0x80046D34 + 4 * 11) becomes the new size; the playing code (`endn` / `endc`, in the dead function func_80061544 of
# ENDING; their data in func_80062664) plays them with func_80015EA4 too, its offset table D_800592E0 and pitch D_80058300 swapped for its own
# around the call: the name -> "great", the celebration -> the rider's cry.
# The longer file goes before Snowman's packed TOD at the end of the credits movie (remix/voices.py layout), its
# directory record moved there; the movie is cut accordingly (about 0.2 s more).
import json, os, struct
from asm import asm

OVL, EXE_BASE = 0x8005AEA8, 0x8000F800
SET_TABLE = 0x80047C0C                   # 16 bytes a set: file index, offset table, count, pitch
VO_SET = 42                              # VOENDING
SITE_NAME, SITE_CELEB = 0x8005C650, 0x8005C6D8
EA4 = 0x80015EA4
PITCH_VAR, OFFS_VAR = 0x80058300, 0x800592E0
CAVE, CAVE_END = 0x80061544, 0x80061544 + 168          # dead function of ENDING (no call, jump or pointer to it or its labels)
DCAVE, DCAVE_END = 0x80062664, 0x80062664 + 140        # another: the extras' offsets and pitches
# (sound set, sample): the announcer's "great", then Boss, Gray, Snowman's cries (riders 4, 5, 6)
EXTRA = [(35, 12), (32, 38), (33, 33), (34, 33)]   # v85: Boss's « yeah » 38, Gray's and Snowman's 33 (chosen by ear)
PITCH = 0x22D                            # 6 kHz, the pitch of those sets


def H(a): return (a + 0x8000) >> 16
def L(a): return a - (H(a) << 16)
def J(op, t): return (op << 26) | ((t >> 2) & 0x3ffffff)


def _sets():
    T = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sndsets.json')))
    return {int(k): v for k, v in T.items()}


def _name(disc, i):
    init = disc.read_file('/INIT.BIN')
    p = struct.unpack_from('<I', init, 0x8005F6C8 - OVL + 4 * i)[0]
    return init[p - OVL:p - OVL + 40].split(b'\0')[0].decode().split(';')[0].replace('\\', '/')


def bank(disc):
    """-> (path of VOENDING, its original bytes, the new bytes, [disc address, bytes] sources, offsets of the extras,
    new end)"""
    T = _sets()
    vo_path = _name(disc, T[VO_SET][0]); vo = disc.read_file(vo_path)
    end = T[VO_SET][1][-1]; assert end == len(vo), (end, len(vo))
    new = bytearray(vo); xoff = []; srcs = [(disc.files[vo_path][0] * 2048, vo)]
    for s, i in EXTRA:
        p = _name(disc, T[s][0]); d = disc.read_file(p); o = T[s][1]
        xoff.append(len(new)); new += d[o[i]:o[i + 1]]
        srcs.append((disc.files[p][0] * 2048, d))
    return vo_path, vo, bytes(new), srcs, xoff, len(new)


def code(xoff):
    D = DCAVE                                             # data: offsets, then pitches, then the saved pitch / table
    XO, PT, SV = D, D + 4 * len(xoff), D + 6 * len(xoff) + 2
    SV = (SV + 3) & ~3
    S = ['endn:', 'slti t0, a1, 4', 'bnez t0, eap', 'nop', 'j exp', 'move t1, zero',
         'endc:', 'slti t0, a1, 11', 'bnez t0, eap', 'nop', 'addiu t1, a1, -10',
         # no stack frame: the ending's stack runs down to the data under it (Snowman's packed TOD at 0x801F4000,
         # remix/snowtod.py): 32 bytes more crashed the podium with Snowman (checked in the emulator)
         'exp:', f'lui t8, {H(SV)}', f'sw ra, {L(SV) + 8}(t8)', f'lui t2, {H(PITCH_VAR)}', f'lhu t3, {L(PITCH_VAR)}(t2)', f'lui t4, {H(OFFS_VAR)}',
         f'lw t5, {L(OFFS_VAR)}(t4)', f'lui t8, {H(SV)}', f'sw t3, {L(SV)}(t8)', f'sw t5, {L(SV) + 4}(t8)',
         f'lui t6, {H(PT)}', f'addiu t6, t6, {L(PT)}', 'sll t7, t1, 1', 'addu t6, t6, t7', 'lhu t6, 0(t6)', f'lui t7, {H(XO)}',
         f'addiu t7, t7, {L(XO)}', f'sh t6, {L(PITCH_VAR)}(t2)', f'sw t7, {L(OFFS_VAR)}(t4)',
         f'jal {EA4:#x}', 'move a1, t1',
         f'lui t8, {H(SV)}', f'lw t3, {L(SV)}(t8)', f'lw t5, {L(SV) + 4}(t8)', f'lui t2, {H(PITCH_VAR)}', f'sh t3, {L(PITCH_VAR)}(t2)', f'lui t4, {H(OFFS_VAR)}',
         f'sw t5, {L(OFFS_VAR)}(t4)', f'lw ra, {L(SV) + 8}(t8)', 'nop', 'jr ra', 'nop',
         'eap:', f'j {EA4:#x}', 'nop']
    c, l = asm(S, CAVE)
    assert c[-1][0] < CAVE_END and SV + 12 <= DCAVE_END, hex(c[-1][0])
    data = struct.pack(f'<{len(xoff)}I', *xoff) + struct.pack(f'<{len(xoff)}H', *[PITCH] * len(xoff))
    data += bytes(SV - D - len(data)) + bytes(12)
    return c + [(D + i, struct.unpack_from('<I', data, i)[0]) for i in range(0, len(data), 4)], l


def ops(disc):
    import crew, voices
    vo_path, vo, new, srcs, xoff, end = bank(disc)
    n = -(-len(new) // 2048)
    lay = voices.layout(disc)
    first = lay['tsmA'] - n
    sl = disc.files['/MOVIE/STAFFE.STR'][0]
    out = [['rec', '/MOVIE/STAFFE.STR', sl, (first - sl) * 2048], ['rec', vo_path, first, len(new)]]
    pad = new + bytes(n * 2048 - len(new))
    for k in range(n):
        sub = bytes([0, 0, 0x89 if k == n - 1 else 0x08, 0]) * 2
        out.append(['sec', first + k, sub.hex(), crew._segments(pad[k * 2048:(k + 1) * 2048], srcs)])
    # the exe: the bank's end (last word of its offset table)
    ex = disc.read_file('/SCES_009.92'); we = lambda a: struct.unpack_from('<I', ex, a - EXE_BASE)[0]
    tab = we(SET_TABLE + 16 * VO_SET + 4); cnt = we(SET_TABLE + 16 * VO_SET + 8)
    assert we(tab + 4 * cnt) == len(vo)
    out.append(['w', '/SCES_009.92', tab + 4 * cnt - EXE_BASE, len(vo), end])
    # ENDING: the code, the two calls
    en = disc.read_file('/ENDING.BIN'); wn = lambda a: struct.unpack_from('<I', en, a - OVL)[0]
    words, l = code(xoff)
    assert wn(SITE_NAME) == J(3, EA4) and wn(SITE_CELEB) == J(3, EA4)
    out += [['w', '/ENDING.BIN', a - OVL, wn(a), w] for a, w in words]
    out += [['w', '/ENDING.BIN', SITE_NAME - OVL, J(3, EA4), J(3, l['endn'])],
            ['w', '/ENDING.BIN', SITE_CELEB - OVL, J(3, EA4), J(3, l['endc'])]]
    return out


def merge(disc, riders_ops):
    """riders' ops (after voices.merge) with these; earlier ones of this module and voices' STAFFE record replaced"""
    new = ops(disc)
    secs = {op[1] for op in new if op[0] == 'sec'}
    words = {(op[1], op[2]) for op in new if op[0] == 'w'}
    vo_path = new[1][1]
    mine = lambda op: op[0] == 'w' and op[1] == '/ENDING.BIN' and (CAVE <= op[2] + OVL < CAVE + 184 or DCAVE <= op[2] + OVL < DCAVE_END)
    out = [op for op in riders_ops if not ((op[0] == 'sec' and op[1] in secs) or (op[0] == 'w' and (op[1], op[2]) in words) or mine(op)
                                          or (op[0] == 'rec' and op[1] in ('/MOVIE/STAFFE.STR', vo_path)))]
    return out + new
