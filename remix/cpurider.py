# CPU-only riders (Jicchi, Nick, Kelly) as player riders: their competition model (low detail, PLAYER0.DAT slot) and
# texture (ENEMY1 / ENEMY2 column) converted to the free-ride player layout (texture page 9 left half, CLUT rows
# 493/494, file like FR/FBD/FRM1_00.FBD). Everything is computed from the player's own disc files.
import struct
from bundle import parse
from pmd import scan

# slot in the competition roster (YAGGI JIN CINDY IRIN JICCHI NICK KELLY BOSS): page, u offset, CLUT row (first of 2)
CPU = {'JICCHI': (4, 6, 0, 503), 'NICK': (5, 6, 128, 505), 'KELLY': (6, 7, 0, 507)}


def model(player0, name):
    """PMD of the CPU rider, texture refs moved to the player's (page 9, u 0..127, CLUT 493/494)"""
    slot, page, du, row = CPU[name]
    b = parse(player0)[slot]; W, pr = scan(b); W = list(W); n = 0
    for i, cmd, uvs, clut, tp in pr:
        if (tp & 0xf) != page or (clut >> 6) not in (row, row + 1): continue
        W[uvs[0]] = (W[uvs[0]] & 0xffff) | (((clut - ((row - 493) << 6)) & 0xffff) << 16)
        W[uvs[1]] = (W[uvs[1]] & 0xffff) | (((tp & ~0xf) | 9) << 16)
        if du:
            for k in uvs: W[k] = (W[k] & ~0xff) | (((W[k] & 0xff) - du) & 0xff)
        n += 1
    assert n > 400, (name, n)
    return struct.pack('<%dI' % len(W), *W)


def texture(enemy1, enemy2, header_fbd, name):
    """player texture file (same layout as FR/FBD/FRM1_00.FBD): 20-byte header, 2 CLUT rows, 32 x 256 halfwords"""
    slot, page, du, row = CPU[name]
    out = bytearray(header_fbd[:20])
    c0 = 20 + (row - 493) * 512; out += enemy1[c0:c0 + 1024]
    if page == 6: src, w, x0 = enemy2, 64, du // 4            # ENEMY2: 64 halfwords wide (VRAM x 384..447)
    else: src, w, x0 = enemy1[16 * 512:], 192, du // 4         # ENEMY1 image after its 16 CLUT rows (x 448..639)
    for y in range(256):
        o = 20 + (y * w + x0) * 2; out += src[o:o + 64]
    assert len(out) == len(header_fbd), (len(out), len(header_fbd))
    return bytes(out)
