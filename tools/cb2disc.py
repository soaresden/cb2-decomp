"""Cool Boarders 2 disc access in pure Python (no chdman needed).

- read a CHD v5 (CD codecs cdlz / cdzl, uncompressed and self-referencing hunks) or a raw BIN (MODE2/2352);
- list and read the ISO9660 files of the data track;
- apply a Remix delta patch (format CB2D, see delta/mkdelta.py in the Remix sources);
- write the result as a new CHD (only the touched hunks are rewritten, uncompressed) or a new BIN.

Same algorithms as the web site's disc.js / chdpatch.js, so both produce the same files.
"""
import lzma, re, struct, zlib

SEC, FRAME = 2352, 2448
SYNC = bytes([0] + [255] * 10 + [0])

# ------------------------------------------------------------------ CD-ROM EDC / ECC (mode 2)
_ecc_f = [0] * 256; _ecc_b = [0] * 256; _edc = [0] * 256
for _i in range(256):
    _j = ((_i << 1) ^ (0x11d if _i & 0x80 else 0)) & 0xff
    _ecc_f[_i] = _j; _ecc_b[_i ^ _j] = _i
    _e = _i
    for _ in range(8): _e = (_e >> 1) ^ (0xd8018001 if _e & 1 else 0)
    _edc[_i] = _e

def edc(d, a, n):
    e = 0; t = _edc
    for x in d[a:a + n]: e = (e >> 8) ^ t[(e ^ x) & 0xff]
    return e

def _ecc_part(sec, majc, minc, majm, mininc, dst):
    size = majc * minc; f = _ecc_f
    for maj in range(majc):
        idx = (maj >> 1) * majm + (maj & 1); a = b = 0
        for _ in range(minc):
            t = sec[0xc + idx]; idx += mininc
            if idx >= size: idx -= size
            a ^= t; b ^= t; a = f[a]
        a = _ecc_b[f[a] ^ b]; sec[dst + maj] = a; sec[dst + maj + majc] = a ^ b

def ecc(sec):
    """mode 2 form 1 parity (the header counts as zero)"""
    hdr = bytes(sec[0xc:0x10]); sec[0xc:0x10] = b'\0\0\0\0'
    _ecc_part(sec, 86, 24, 2, 86, 0x81c); _ecc_part(sec, 52, 43, 86, 88, 0x8c8)
    sec[0xc:0x10] = hdr

def fix_sector(sec):
    """recompute EDC (and ECC for form 1) of a mode 2 sector, in place"""
    if sec[0x12] & 0x20:
        sec[0x92c:0x930] = edc(sec, 0x10, 8 + 2324).to_bytes(4, 'little')
    else:
        sec[0x818:0x81c] = edc(sec, 0x10, 8 + 2048).to_bytes(4, 'little'); ecc(sec)
    return sec

# ------------------------------------------------------------------ CHD v5 map
_CRC = []
for _i in range(256):
    _c = _i << 8
    for _ in range(8): _c = ((_c << 1) ^ 0x1021) & 0xffff if _c & 0x8000 else (_c << 1) & 0xffff
    _CRC.append(_c)

def crc16(d, c=0xffff):
    t = _CRC
    for x in d: c = ((c << 8) & 0xffff) ^ t[(c >> 8) ^ x]
    return c

class _BR:
    def __init__(s, b): s.b = b; s.p = 0
    def read(s, n):
        v = 0
        for _ in range(n):
            by = s.b[s.p >> 3] if (s.p >> 3) < len(s.b) else 0
            v = (v << 1) | ((by >> (7 - (s.p & 7))) & 1); s.p += 1
        return v

class _BW:
    def __init__(s): s.out = bytearray(); s.cur = 0; s.n = 0
    def write(s, v, n):
        for i in range(n - 1, -1, -1):
            s.cur = (s.cur << 1) | ((v >> i) & 1); s.n += 1
            if s.n == 8: s.out.append(s.cur); s.cur = 0; s.n = 0
    def bytes(s):
        o = bytearray(s.out)
        if s.n: o.append((s.cur << (8 - s.n)) & 0xff)
        return bytes(o)

def _canon(lens):
    histo = [0] * 33
    for l in lens: histo[l] += 1
    cur = 0
    for L in range(32, 0, -1):
        nx = (cur + histo[L]) >> 1
        if L != 1 and nx * 2 != cur + histo[L]: raise ValueError('arbre huffman invalide')
        histo[L] = cur; cur = nx
    codes = []
    for l in lens:
        if l > 0: codes.append(histo[l]); histo[l] += 1
        else: codes.append(-1)
    return codes

def _rawmap(typ, ln, off, crc):
    r = bytearray(len(typ) * 12)
    for h in range(len(typ)):
        p = h * 12; r[p] = typ[h]
        r[p + 1:p + 4] = ln[h].to_bytes(3, 'big'); r[p + 4:p + 10] = off[h].to_bytes(6, 'big'); r[p + 10:p + 12] = crc[h].to_bytes(2, 'big')
    return bytes(r)

def decode_map(logical, hunkbytes, m):
    n = -(-logical // hunkbytes)
    mapbytes = int.from_bytes(m[0:4], 'big'); first = int.from_bytes(m[4:10], 'big'); mapcrc = int.from_bytes(m[10:12], 'big')
    lb, sb, pb = m[12], m[13], m[14]
    br = _BR(m[16:16 + mapbytes]); lens = []
    while len(lens) < 16:
        nb = br.read(4)
        if nb != 1: lens.append(nb)
        else:
            nb = br.read(4)
            if nb == 1: lens.append(1)
            else: lens += [nb] * (br.read(4) + 3)
    codes = _canon(lens); table = {(l, codes[s]): s for s, l in enumerate(lens) if l > 0}
    def sym():
        c = 0
        for l in range(1, 17):
            c = (c << 1) | br.read(1)
            if (l, c) in table: return table[(l, c)]
        raise ValueError('code huffman invalide')
    typ = [0] * n; rep = 0; last = 0
    for h in range(n):
        if rep > 0: typ[h] = last; rep -= 1; continue
        v = sym()
        if v == 7: typ[h] = last; rep = 2 + sym()
        elif v == 8: typ[h] = last; rep = 2 + 16 + (sym() << 4); rep += sym()
        else: typ[h] = last = v
    ln = [0] * n; off = [0] * n; crc = [0] * n; cur = first; lastself = 0
    for h in range(n):
        t = typ[h]; o = cur; l = 0; c = 0
        if t <= 3: l = br.read(lb); cur += l; c = br.read(16)
        elif t == 4: l = hunkbytes; cur += l; c = br.read(16)
        elif t == 5: lastself = o = br.read(sb)
        elif t in (9, 10):
            if t == 10: lastself += 1
            t = 5; o = lastself
        else: raise ValueError('type de hunk CHD non géré : %d' % t)
        typ[h] = t; ln[h] = l; off[h] = o; crc[h] = c
    if crc16(_rawmap(typ, ln, off, crc)) != mapcrc: raise ValueError('CRC de la carte CHD incorrect')
    return dict(n=n, first=first, lb=lb, sb=sb, pb=pb, typ=typ, ln=ln, off=off, crc=crc)

def _lzma_raw(src, size):
    d = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[{'id': lzma.FILTER_LZMA1, 'lc': 3, 'lp': 0, 'pb': 2, 'dict_size': 1 << 24}])
    out = d.decompress(bytes(src), max_length=size)
    if len(out) != size: raise ValueError('bloc LZMA incomplet')
    return out

def _inflate(src): return zlib.decompress(bytes(src), -15)


# ------------------------------------------------------------------ FLAC (codec cdfl: CD audio, and some data hunks)
class _FB:
    def __init__(s, b): s.b = b; s.p = 0
    def read(s, n):
        v = 0
        while n:
            i = s.p >> 3
            if i >= len(s.b): raise ValueError('FLAC : fin de données inattendue')
            off = s.p & 7; take = min(8 - off, n)
            v = (v << take) | ((s.b[i] >> (8 - off - take)) & ((1 << take) - 1)); s.p += take; n -= take
        return v
    def signed(s, n):
        v = s.read(n); return v - (1 << n) if n and v >> (n - 1) else v
    def unary(s):
        q = 0
        while True:
            i = s.p >> 3
            if i >= len(s.b): raise ValueError('FLAC : fin de données inattendue')
            off = s.p & 7; byte = (s.b[i] << off) & 0xff
            if byte:
                z = 8 - byte.bit_length(); q += z; s.p += z + 1; return q
            q += 8 - off; s.p += 8 - off
_BS = [0, 192, 576, 1152, 2304, 4608, 0, 0, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
_SS = [16, 8, 12, 0, 16, 20, 24, 0]
def _residual(br, out, n, order):
    method = br.read(2); pb = 4 if method == 0 else 5; esc = 15 if method == 0 else 31; po = br.read(4)
    i = order
    for p in range(1 << po):
        cnt = (n >> po) - (order if p == 0 else 0); k = br.read(pb)
        if k == esc:
            bits = br.read(5)
            for _ in range(cnt): out[i] = br.signed(bits); i += 1
            continue
        for _ in range(cnt):
            u = (br.unary() << k) | (br.read(k) if k else 0); out[i] = -((u + 1) >> 1) if u & 1 else u >> 1; i += 1
def _subframe(br, n, bps):
    br.read(1); typ = br.read(6); wasted = 0
    if br.read(1): wasted = br.unary() + 1
    bps -= wasted; s = [0] * n
    if typ == 0: s = [br.signed(bps)] * n
    elif typ == 1: s = [br.signed(bps) for _ in range(n)]
    elif 8 <= typ <= 12:
        o = typ - 8
        for i in range(o): s[i] = br.signed(bps)
        _residual(br, s, n, o)
        for i in range(o, n):
            if o == 1: s[i] += s[i-1]
            elif o == 2: s[i] += 2*s[i-1] - s[i-2]
            elif o == 3: s[i] += 3*s[i-1] - 3*s[i-2] + s[i-3]
            elif o == 4: s[i] += 4*s[i-1] - 6*s[i-2] + 4*s[i-3] - s[i-4]
    elif typ >= 32:
        o = typ - 31
        for i in range(o): s[i] = br.signed(bps)
        prec = br.read(4) + 1; shift = br.signed(5); c = [br.signed(prec) for _ in range(o)]
        _residual(br, s, n, o)
        for i in range(o, n):
            acc = 0
            for j in range(o): acc += c[j] * s[i-1-j]
            s[i] += acc >> shift
    else: raise ValueError('FLAC : sous-trame inconnue %d' % typ)
    if wasted: s = [x << wasted for x in s]
    return s
def flac_decode(src, total):
    """FLAC frames (no 'fLaC' header) -> (list of int16 samples L R L R ..., bytes consumed)"""
    br = _FB(src); pcm = []
    while len(pcm) < total * 2:
        if br.read(14) != 0x3ffe: raise ValueError('FLAC : synchro de trame introuvable')
        br.read(2); bsc = br.read(4); src_ = br.read(4); ch = br.read(4); ssc = br.read(3); br.read(1)
        x = br.read(8); extra = 0
        while x & 0x80: extra += 1; x = (x << 1) & 0xff
        for _ in range(1, extra): br.read(8)
        n = _BS[bsc]
        if bsc == 6: n = br.read(8) + 1
        elif bsc == 7: n = br.read(16) + 1
        if src_ == 12: br.read(8)
        elif src_ in (13, 14): br.read(16)
        br.read(8)
        if not n or ch > 10: raise ValueError('FLAC : en-tête de trame invalide')
        bps = _SS[ssc] or 16; nch = ch + 1 if ch < 8 else 2
        chans = [_subframe(br, n, bps + (1 if (ch == 8 and c == 1) or (ch == 9 and c == 0) or (ch == 10 and c == 1) else 0)) for c in range(nch)]
        br.p = (br.p + 7) & ~7; br.read(16)
        L = chans[0]; R = chans[1] if nch > 1 else chans[0]
        if ch == 8: R = [a - b for a, b in zip(L, chans[1])]
        elif ch == 9: L = [a + b for a, b in zip(chans[0], chans[1])]
        elif ch == 10:
            L = []; R = []
            for m, sd in zip(chans[0], chans[1]):
                m = (m << 1) | (sd & 1); L.append((m + sd) >> 1); R.append((m - sd) >> 1)
        m = min(n, total - len(pcm) // 2)
        for i in range(m): pcm.append(L[i]); pcm.append(R[i])
    return pcm, br.p >> 3

# ------------------------------------------------------------------ images
class CHD:
    kind = 'chd'
    def __init__(s, path):
        s.path = path; s.f = open(path, 'rb'); h = s.f.read(124); s.head = h
        if h[:8] != b'MComprHD' or struct.unpack('>I', h[12:16])[0] != 5: raise ValueError("ce fichier n'est pas un CHD v5")
        s.logical, s.mapoffset = struct.unpack('>QQ', h[32:48]); s.hunkbytes = struct.unpack('>I', h[56:60])[0]
        s.sha1 = h[84:104]
        s.codecs = [h[16 + 4 * i:20 + 4 * i].decode('latin1') for i in range(4)]
        s.f.seek(s.mapoffset); mh = s.f.read(16); s.f.seek(s.mapoffset)
        s.M = decode_map(s.logical, s.hunkbytes, s.f.read(16 + int.from_bytes(mh[0:4], 'big')))
        if s.hunkbytes % FRAME: raise ValueError("ce CHD n'est pas un CD")
        s.fph = s.hunkbytes // FRAME; s.cache = {}
    def _read(s, a, b): s.f.seek(a); return s.f.read(b - a)
    def _root(s, i):
        t, r, k = s.M['typ'][i], i, 0
        while t == 5 and k < 64: r = s.M['off'][r]; t = s.M['typ'][r]; k += 1
        return r, t
    def hunk(s, i):
        """-> (frames bytes with the data as stored, ecc flags or None, compressed subcode or None, codec)"""
        if i in s.cache: return s.cache[i]
        r, t = s._root(i)
        src = s._read(s.M['off'][r], s.M['off'][r] + s.M['ln'][r])
        if t == 4: out = (src, None, None, None)
        else:
            codec = s.codecs[t]; n = s.fph; hb = s.hunkbytes
            eccb = (n + 7) >> 3; clb = 2 if hb < 65536 else 3; hdrb = eccb + clb
            cbase = int.from_bytes(src[eccb:eccb + clb], 'big')
            if codec == 'cdlz': base = _lzma_raw(src[hdrb:hdrb + cbase], n * SEC)
            elif codec == 'cdzl': base = _inflate(src[hdrb:hdrb + cbase])
            elif codec == 'cdfl':   # FLAC, no ECC flags / length header; samples rebuilt as big-endian bytes
                pcm, used = flac_decode(src, n * SEC // 4)
                base = struct.pack('>%dh' % len(pcm), *pcm)
                fr = bytearray(hb)
                for k in range(n): fr[k * FRAME:k * FRAME + SEC] = base[k * SEC:(k + 1) * SEC]
                out = (bytes(fr), bytes(eccb), src[used:], codec)
                if len(s.cache) > 64: s.cache.clear()
                s.cache[i] = out
                return out
            else: raise ValueError('codec CHD non géré : %s' % codec)
            fr = bytearray(hb)
            for k in range(n): fr[k * FRAME:k * FRAME + SEC] = base[k * SEC:(k + 1) * SEC]
            out = (bytes(fr), src[:eccb], src[hdrb + cbase:], codec)
        if len(s.cache) > 64: s.cache.clear()
        s.cache[i] = out
        return out
    def sector(s, lba):
        h = s.hunk(lba // s.fph)[0]; f = lba % s.fph
        return h[f * FRAME:f * FRAME + SEC]
    def raw_hunk(s, i):
        """the full hunk, frames with sync / ECC rebuilt where the codec stripped them, plus the subcode"""
        fr, flags, sub, codec = s.hunk(i)
        out = bytearray(fr)
        if flags is None: return out
        subd = _inflate(sub)
        for k in range(s.fph):
            out[k * FRAME + SEC:(k + 1) * FRAME] = subd[k * 96:(k + 1) * 96]
            if flags[k >> 3] & (1 << (k & 7)):
                sec = out[k * FRAME:k * FRAME + SEC]; sec[0:12] = SYNC; ecc(sec); out[k * FRAME:k * FRAME + SEC] = sec
        return out

class BIN:
    kind = 'bin'
    def __init__(s, path):
        import os
        s.path = path; s.f = open(path, 'rb'); s.size = os.path.getsize(path)
    def sector(s, lba): s.f.seek(lba * SEC); return s.f.read(SEC)

class Disc:
    """ISO9660 view of the data track of a CHD or BIN"""
    def __init__(s, path):
        with open(path, 'rb') as f: magic = f.read(8)
        s.img = CHD(path) if magic == b'MComprHD' else BIN(path)
        s.kind = s.img.kind
        pvd = s.user(16)
        if pvd[1:6] != b'CD001': raise ValueError("pas de système de fichiers ISO9660 sur ce disque")
        s.files = {}
        s._walk(struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0], '')
    def user(s, lba): return s.img.sector(lba)[24:24 + 2048]
    def _walk(s, lba, size, path):
        for k in range(-(-size // 2048)):
            d = s.user(lba + k); i = 0
            while i < 2048:
                L = d[i]
                if not L: break
                elba, esz = struct.unpack_from('<I', d, i + 2)[0], struct.unpack_from('<I', d, i + 10)[0]
                fl, nl = d[i + 25], d[i + 32]; name = d[i + 33:i + 33 + nl]
                if name not in (b'\0', b'\1'):
                    p = path + '/' + name.decode('latin1').split(';')[0]
                    s.files[p] = (elba, esz, fl & 2 != 0)
                    if fl & 2: s._walk(elba, esz, p)
                i += L
    def read_file(s, p):
        lba, size, _ = s.files[p]
        return b''.join(s.user(lba + k) for k in range(-(-size // 2048)))[:size]
    def read_user(s, addr, n):
        out = bytearray()
        while len(out) < n:
            a = addr + len(out); l, o = divmod(a, 2048); m = min(n - len(out), 2048 - o)
            out += s.user(l)[o:o + m]
        return bytes(out)

# ------------------------------------------------------------------ Remix delta (CB2D v1)
class SourceError(ValueError):
    """the disc is not the original game the patch expects"""

def apply_delta(disc, P, log=lambda m: None):
    """-> {lba: (subheader 8 bytes, user data 2048 bytes)}"""
    if P[:4] != b'CB2D': raise ValueError('patch invalide')
    crc, size, n = struct.unpack_from('<III', P, 8)
    exe = disc.read_file('/SCES_009.92')
    if len(exe) != size or zlib.crc32(exe) != crc: raise SourceError("ce disque n'est pas le Cool Boarders 2 (PAL) d'origine")
    o = 20; mods = {}
    for i in range(n):
        lba = struct.unpack_from('<I', P, o)[0]; sub = P[o + 4:o + 12]; nops = struct.unpack_from('<H', P, o + 12)[0]; o += 14
        data = bytearray()
        for _ in range(nops):
            kind, ln = P[o], struct.unpack_from('<H', P, o + 1)[0]; o += 3
            if kind == 0: data += disc.read_user(struct.unpack_from('<I', P, o)[0], ln); o += 4
            else: data += P[o:o + ln]; o += ln
        assert len(data) == 2048, (lba, len(data))
        mods[lba] = (bytes(sub), bytes(data))
        if i % 256 == 0: log('%d/%d secteurs' % (i, n))
    return mods

def _patch_sector(sec, m):
    s = bytearray(sec)
    if isinstance(m, tuple): s[16:24] = m[0]; s[24:24 + 2048] = m[1]
    else: s[24:24 + 2048] = m
    if s[0] != 0 or s[1] != 255: s[0:12] = SYNC
    return fix_sector(s)

def write_patched(disc, mods, dst, log=lambda m: None, progress=lambda f: None):
    """write a copy of the disc image with the given user-data sectors replaced
    mods: {lba: (subheader8, data2048) | data2048}"""
    img = disc.img; lbas = sorted(mods)
    if img.kind == 'bin':
        with open(dst, 'wb') as out:
            cur = 0
            for l in lbas + [None]:
                end = img.size if l is None else l * SEC
                img.f.seek(cur)
                while cur < end:
                    b = img.f.read(min(1 << 22, end - cur)); out.write(b); cur += len(b); progress(cur / img.size)
                if l is None: break
                out.write(_patch_sector(img.sector(l), mods[l])); cur = (l + 1) * SEC
        return
    hunks = {}
    for l in lbas:
        hi, f = divmod(l, img.fph)
        if hi not in hunks: hunks[hi] = img.raw_hunk(hi)
        h = hunks[hi]; h[f * FRAME:f * FRAME + SEC] = _patch_sector(h[f * FRAME:f * FRAME + SEC], mods[l])
    log('%d blocs CHD réécrits' % len(hunks))
    patch_hunks(img, {i: (crc16(d), bytes(d)) for i, d in hunks.items()}, dst, progress=progress)

def patch_hunks(img, hunks, dst, progress=lambda f: None):
    """new CHD = the source with the given hunks replaced by uncompressed ones (hunks: {i: (crc16, data)})"""
    M = img.M; N = M['n']; hb = img.hunkbytes
    typ = [0] * N; ln = [0] * N; off = [0] * N; crc = [0] * N; parts = []; cur = M['first']
    def root(t):
        k = 0
        while M['typ'][t] == 5 and k < 64: t = M['off'][t]; k += 1
        return t
    for i in range(N):
        if i in hunks:
            c, d = hunks[i]; typ[i] = 4; ln[i] = hb; off[i] = cur; crc[i] = c; parts.append(d); cur += hb; continue
        t = M['typ'][i]; r = i
        if t == 5:
            r = root(M['off'][i])
            if r not in hunks and M['off'][i] not in hunks:
                typ[i] = 5; ln[i] = 0; off[i] = M['off'][i]; crc[i] = 0; continue
            t = M['typ'][r]
        typ[i] = t; ln[i] = M['ln'][r]; crc[i] = M['crc'][r]; off[i] = cur
        a = M['off'][r]; b = a + M['ln'][r]
        if parts and isinstance(parts[-1], list) and parts[-1][1] == a: parts[-1][1] = b
        else: parts.append([a, b])
        cur += M['ln'][r]
    lb, sb = M['lb'], M['sb']
    for i in range(N):
        if typ[i] <= 3:
            while ln[i] >= (1 << lb): lb += 1
        if typ[i] == 5:
            while off[i] >= (1 << sb): sb += 1
    bw = _BW(); bw.write(1, 4); bw.write(4, 4); bw.write(13, 4)   # 16 codes of 4 bits: code == symbol
    for i in range(N): bw.write(typ[i], 4)
    for i in range(N):
        if typ[i] <= 3: bw.write(ln[i], lb); bw.write(crc[i], 16)
        elif typ[i] == 4: bw.write(crc[i], 16)
        else: bw.write(off[i], sb)
    bits = bw.bytes()
    mapcrc = crc16(_rawmap(typ, [hb if typ[i] == 4 else ln[i] for i in range(N)], off, crc))
    mhdr = len(bits).to_bytes(4, 'big') + M['first'].to_bytes(6, 'big') + mapcrc.to_bytes(2, 'big') + bytes([lb, sb, M['pb'], 0])
    prefix = bytearray(img._read(0, M['first'])); prefix[40:48] = cur.to_bytes(8, 'big')
    total = cur; done = 0
    with open(dst, 'wb') as out:
        out.write(prefix)
        for p in parts:
            if isinstance(p, list):
                a, b = p
                while a < b:
                    blk = img._read(a, min(b, a + (1 << 22))); out.write(blk); a += len(blk); done += len(blk); progress(done / total)
            else: out.write(p); done += len(p); progress(done / total)
        out.write(mhdr); out.write(bits)

# ------------------------------------------------------------------ soundtrack swap (music of another disc)
def read_meta(img):
    """CHD metadata entries -> [(tag, flags, data)] in file order"""
    out = []; mo = struct.unpack('>Q', img.head[48:56])[0]
    while mo:
        h = img._read(mo, mo + 16); tag = h[:4]; flags = h[4]; ln = int.from_bytes(h[5:8], 'big'); nxt = struct.unpack('>Q', h[8:16])[0]
        out.append((tag, flags, img._read(mo + 16, mo + 16 + ln))); mo = nxt
    return out

def cht2(data):
    s = data.split(b'\0')[0].decode('latin1')
    return {k: v for k, v in (x.split(':', 1) for x in s.split())}

# Cool Boarders 2: which track of the USA disc plays where the European game expects BGMx (from the play calls of
# both versions: menus 2 and 3 identical, 13/16/17/18 in Europe = 14/17/18/19 in the USA, the race tracks 4..12 in order)
CB2_US_MUSIC = {k: (k if k <= 12 else k + 1) for k in range(2, 21)}

def compose_soundtrack(eu, us, mods, dst, mapping=CB2_US_MUSIC, log=lambda m: None, progress=lambda f: None):
    """New CHD = data track of `eu` (with the user-data sectors `mods` replaced, e.g. the Remix) + all audio tracks of
    `us`, copied as they are (still compressed). The /CDDA/BGMx.DA records of `eu` are pointed at the `us` tracks given
    by `mapping` (European BGM number -> USA track number, BGMA = 2). Both must be CHD (Disc objects)."""
    A, B = eu.img, us.img
    if A.kind != 'chd' or B.kind != 'chd': raise ValueError('les deux disques doivent être des CHD')
    if A.hunkbytes != B.hunkbytes: raise ValueError('CHD de géométries différentes')
    if A.codecs != B.codecs: raise ValueError('CHD compressés différemment (recompresse-les avec la même version de chdman)')
    ma, mb = read_meta(A), read_meta(B)
    ta = [(t, f, cht2(d)) for t, f, d in ma if t in (b'CHT2', b'CHTR')]; tb = [(t, f, cht2(d)) for t, f, d in mb if t in (b'CHT2', b'CHTR')]
    a1 = int(ta[0][2]['FRAMES']); b1 = int(tb[0][2]['FRAMES'])
    start = b1 + (-b1) % 4                                   # first CHD frame of the USA audio
    fph = A.fph
    if start % fph or a1 > b1: raise ValueError('disposition des pistes inattendue (piste de données US %d secteurs)' % b1)
    H0 = start // fph                                        # first audio hunk
    # ---- /CDDA records of the European disc -> USA tracks
    us_rec = {p.split('/')[-1]: (l, s) for p, (l, s, d) in us.files.items() if p.startswith('/CDDA/')}
    mods = dict(mods)
    def user(l):
        m = mods.get(l)
        return bytearray(m[1] if isinstance(m, tuple) else m) if m is not None else bytearray(eu.user(l))
    dlba = eu.files['/CDDA'][0]; dsec = -(-eu.files['/CDDA'][1] // 2048)
    for k in range(dsec):
        d = user(dlba + k); i = 0
        while i < 2048 and d[i]:
            L = d[i]; nl = d[i + 32]; name = d[i + 33:i + 33 + nl].decode('latin1').split(';')[0]
            if name.startswith('BGM') and name.endswith('.DA'):
                n = ord(name[3]) - ord('A') + 2; m = mapping.get(n)
                src = 'BGM%s.DA' % chr(ord('A') + m - 2) if m else None
                if src in us_rec:
                    l, s = us_rec[src]
                    d[i + 2:i + 10] = struct.pack('<I', l) + struct.pack('>I', l); d[i + 10:i + 18] = struct.pack('<I', s) + struct.pack('>I', s)
                    log('%s -> piste US %s' % (name, src))
            i += L
        old = mods.get(dlba + k)
        mods[dlba + k] = (old[0], bytes(d)) if isinstance(old, tuple) else bytes(d)
    # ---- data hunks of the European disc: changed ones rebuilt (uncompressed), the rest copied as stored
    empty = bytearray(SEC)
    new = {}                                                 # hunk -> raw bytes
    for l in sorted(mods):
        hi, f = divmod(l, fph)
        if hi not in new: new[hi] = A.raw_hunk(hi)
        h = new[hi]; h[f * FRAME:f * FRAME + SEC] = _patch_sector(h[f * FRAME:f * FRAME + SEC], mods[l])
    for hi in range(a1 // fph, H0):                          # hunks where the data track grows to the USA length
        h = new.get(hi) or A.raw_hunk(hi); new[hi] = h
        for f in range(fph):
            fr = hi * fph + f
            if fr < a1: continue
            if fr < b1:                                       # empty mode 2 form 1 sector
                s = bytearray(SEC); s[0:12] = SYNC; a = fr + 150
                s[12:16] = bytes([(a // 4500) // 10 * 16 + (a // 4500) % 10, ((a // 75) % 60) // 10 * 16 + (a // 75) % 60 % 10, (a % 75) // 10 * 16 + a % 75 % 10, 2])
                fix_sector(s); h[f * FRAME:f * FRAME + SEC] = s
            else: h[f * FRAME:f * FRAME + SEC] = empty
            h[f * FRAME + SEC:(f + 1) * FRAME] = bytes(FRAME - SEC)
    # ---- the map: hunks 0..H0-1 from A, H0.. from B
    N = B.M['n']; typ = [0] * N; ln = [0] * N; off = [0] * N; crc = [0] * N; parts = []
    hdr = bytearray(A.head); first = len(hdr); cur = first
    def root(M, t):
        k = 0
        while M['typ'][t] == 5 and k < 64: t = M['off'][t]; k += 1
        return t
    for i in range(N):
        if i in new:
            d = bytes(new[i]); typ[i] = 4; ln[i] = A.hunkbytes; off[i] = cur; crc[i] = crc16(d); parts.append(d); cur += len(d); continue
        img, M, lo, hi_ = (A, A.M, 0, H0) if i < H0 else (B, B.M, H0, N)
        t = M['typ'][i]; r = i
        if t == 5:
            r = root(M, M['off'][i])
            if lo <= r < hi_ and r not in new and M['off'][i] < i and lo <= M['off'][i] < hi_:
                typ[i] = 5; off[i] = M['off'][i]; continue
            t = M['typ'][r]
        typ[i] = t; ln[i] = M['ln'][r]; crc[i] = M['crc'][r]; off[i] = cur
        parts.append((img, M['off'][r], M['off'][r] + M['ln'][r])); cur += M['ln'][r]
    # ---- metadata: track 1 from the European disc (grown to the USA length), audio tracks from the USA disc
    meta = []
    t, f, _ = ta[0]
    for tag, flags, data in ma:
        if tag in (b'CHT2', b'CHTR'): continue
        meta.append((tag, flags, data))
    d1 = [d for tg, fl, d in ma if tg in (b'CHT2', b'CHTR')][0].split(b'\0')[0].decode('latin1')
    d1 = re.sub(r'FRAMES:\d+', 'FRAMES:%d' % b1, d1).encode('latin1') + b'\0'
    meta.append((t, f, d1))
    meta += [(tg, fl, d) for tg, fl, d in mb if tg in (b'CHT2', b'CHTR')][1:]
    metablob = bytearray(); metaoff = cur
    for k, (tag, flags, data) in enumerate(meta):
        nxt = 0 if k == len(meta) - 1 else metaoff + len(metablob) + 16 + len(data)
        metablob += tag + bytes([flags]) + len(data).to_bytes(3, 'big') + nxt.to_bytes(8, 'big') + data
    cur += len(metablob)
    # ---- map encoding (16 codes of 4 bits, same as patch_hunks)
    lb, sb = 0, 0
    for i in range(N):
        if typ[i] <= 3:
            while ln[i] >= (1 << lb): lb += 1
        if typ[i] == 5:
            while off[i] >= (1 << sb): sb += 1
    bw = _BW(); bw.write(1, 4); bw.write(4, 4); bw.write(13, 4)
    for i in range(N): bw.write(typ[i], 4)
    for i in range(N):
        if typ[i] <= 3: bw.write(ln[i], lb); bw.write(crc[i], 16)
        elif typ[i] == 4: bw.write(crc[i], 16)
        else: bw.write(off[i], sb)
    bits = bw.bytes()
    mapcrc = crc16(_rawmap(typ, [A.hunkbytes if typ[i] == 4 else ln[i] for i in range(N)], off, crc))
    mhdr = len(bits).to_bytes(4, 'big') + first.to_bytes(6, 'big') + mapcrc.to_bytes(2, 'big') + bytes([lb, sb, B.M['pb'], 0])
    hdr[32:40] = (N * A.hunkbytes).to_bytes(8, 'big'); hdr[40:48] = cur.to_bytes(8, 'big'); hdr[48:56] = metaoff.to_bytes(8, 'big')
    total = cur + 16 + len(bits); done = 0
    with open(dst, 'wb') as out:
        out.write(hdr)
        for p in parts:
            if isinstance(p, tuple):
                img, a, b = p
                while a < b:
                    blk = img._read(a, min(b, a + (1 << 22))); out.write(blk); a += len(blk); done += len(blk)
            else: out.write(p); done += len(p)
            progress(done / total)
        out.write(metablob); out.write(mhdr); out.write(bits)
    log('%d blocs : %d du disque européen, %d du disque américain' % (N, H0, N - H0))
