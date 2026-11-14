# Signature on the title screen (mod `sign`, v83, on by default): remix/title.py `sign`. Two sets of operations, as the
# title files are at their place without the mod riders ('bs' on the files, after BRAND's word) and moved (to the end
# of a movie, by 'riders', whose sectors already carry the word) with it: 'sign_r' rewrites those moved sectors whole
# (the riders version + the signature: copies from the player's disc, the new pixels only as bytes). apply() takes
# 'sign_r' instead of 'sign' when 'riders' is on.
import title


def _sector_data(disc, segs):
    return b''.join(disc.read_user(s[2], s[1]) if s[0] == 0 else bytes.fromhex(s[1]) for s in segs)


def ops(disc, pkg):
    import modular, crew
    sign, sign_r = [], []
    for p in title.FILES:
        o = disc.read_file(p); a = title.draw(o); b = title.sign(a)
        i = 0
        while i < len(a):                                        # without riders: on the file (BRAND's word already there)
            if a[i] == b[i]: i += 1; continue
            j = i
            while j < len(a) and (a[j] != b[j] or (j + 8 < len(a) and a[j:j + 8] != b[j:j + 8])): j += 1
            sign.append(['bs', p, i, modular.segments(bytes(b[i:j]), o)]); i = j
        # with riders: its moved copy (directory record and whole sectors in pkg['ops']['riders'])
        rec = [op for op in pkg['ops']['riders'] if op[0] == 'rec' and op[1] == p]
        assert len(rec) == 1, p
        lba, size = rec[0][2], rec[0][3]; n = -(-size // 2048)
        secs = {op[1]: op for op in pkg['ops']['riders'] if op[0] == 'sec' and lba <= op[1] < lba + n}
        assert len(secs) == n, (p, len(secs), n)
        moved = b''.join(_sector_data(disc, secs[lba + k][3]) for k in range(n))[:size]
        assert moved[:532] == a[:532]
        new = title.sign(moved)
        src = [(disc.files[p][0] * 2048, o)]
        for k in range(n):
            if new[k * 2048:(k + 1) * 2048] == moved[k * 2048:(k + 1) * 2048]: continue
            chunk = new[k * 2048:(k + 1) * 2048]; chunk += bytes(2048 - len(chunk))
            sign_r.append(['sec', lba + k, secs[lba + k][2], crew._segments(chunk, src)])
    return sign, sign_r
