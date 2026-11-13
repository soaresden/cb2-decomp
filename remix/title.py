# Title screen: a stylised "REMIX" next to the "2" of the logo (ETC/CB2T1E.FBD, and CB2T2E.FBD for the link mode).
# The files are 8-bit images 320x256 (20-byte header, 256-colour CLUT at VRAM 768,511, pixels at 864,0); the word is
# drawn here (Noto Sans Black Italic, gold gradient like the "2", dark outline and shadow, tilted) and each pixel is
# the nearest colour of the image's own palette. No pixel of the game is stored: the word is computed at build time.
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'NotoSans-BlackItalic.ttf')
FILES = ['/ETC/CB2T1E.FBD', '/ETC/CB2T2E.FBD']
HDR, W, H = 532, 320, 256
X0, Y0, SIZE, ANGLE = 206, 121, 27, 8


def word(text='REMIX', size=SIZE, angle=ANGLE):
    f = ImageFont.truetype(FONT, size)
    mask = Image.new('L', (size * len(text), int(size * 1.6)), 0); ImageDraw.Draw(mask).text((8, 0), text, font=f, fill=255)
    bb = mask.getbbox(); pad = 8
    mask = mask.crop((bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad)); w, h = mask.size
    m = np.array(mask) > 127
    ys = np.linspace(0, 1, h)[:, None]
    top, mid, low, bot = (np.array(c) for c in ([255, 246, 170], [250, 196, 40], [214, 110, 20], [120, 60, 10]))
    g = np.where(ys < 0.45, top + (mid - top) * (ys / 0.45), np.where(ys < 0.8, mid + (low - mid) * ((ys - 0.45) / 0.35), low + (bot - low) * ((ys - 0.8) / 0.2)))
    fill = np.broadcast_to(g[:, None, :], (h, w, 3)).copy()
    hl = ((ys > 0.12) & (ys < 0.22))[:, :, None]; fill = np.where(hl, np.minimum(fill + 40, 255), fill)
    out = np.zeros((h, w, 4), np.uint8)
    o1 = np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    sh = np.zeros_like(o1); sh[3:, 3:] = o1[:-3, :-3]
    out[sh] = [20, 10, 30, 255]; out[o1] = [70, 20, 10, 255]; out[m, :3] = fill[m]; out[m, 3] = 255
    a = np.array(Image.fromarray(out, 'RGBA').rotate(angle, resample=Image.BICUBIC, expand=True))
    a[..., 3] = np.where(a[..., 3] > 140, 255, 0)
    return a


def draw(d):
    """d: bytes of CB2T1E/CB2T2E.FBD -> new bytes"""
    d = bytearray(d)
    clut = np.frombuffer(bytes(d[20:HDR]), '<u2')
    pal = np.stack([(clut & 31) << 3, ((clut >> 5) & 31) << 3, ((clut >> 10) & 31) << 3], -1).astype(int)
    ok = np.array([i for i in range(1, 256) if clut[i] != 0]); P = pal[ok]
    pix = np.frombuffer(bytes(d[HDR:HDR + W * H]), np.uint8).reshape(H, W).copy()
    a = word(); h, w = a.shape[:2]
    for y in range(h):
        for x in range(w):
            if a[y, x, 3] and 0 <= Y0 + y < H and 0 <= X0 + x < W:
                pix[Y0 + y, X0 + x] = ok[((P - a[y, x, :3].astype(int)) ** 2).sum(1).argmin()]
    d[HDR:HDR + W * H] = pix.tobytes()
    return bytes(d)
