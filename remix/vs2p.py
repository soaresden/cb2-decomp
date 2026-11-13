# Player 2's copy of a race model (2-player mode): same model, its texture where the game puts player 2's
# (VS/2P files = VS/1P files with: every palette 7 rows lower; u + 128, except page 8 polygons with v < 64 (board): v + 64).
import struct
from pmd import scan


def to_p2(b):
    W, pr = scan(b); W = list(W)
    for i, cmd, uvs, cl, tp in pr:
        W[uvs[0]] = (W[uvs[0]] & 0xffff) | (((cl + (7 << 6)) & 0xffff) << 16)
        if tp & 0x1f == 8 and max((W[k] >> 8) & 0xff for k in uvs) < 64:
            for k in uvs: W[k] = (W[k] & ~0xff00) | ((((W[k] >> 8) & 0xff) + 64) << 8)
        else:
            for k in uvs: W[k] = (W[k] & ~0xff) | ((W[k] & 0xff) + 128)
    return struct.pack(f'<{len(W)}I', *W)
