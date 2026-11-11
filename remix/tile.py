import numpy as np
from PIL import Image
IMG=20+256*13*2
def load(path):
    d=open(path,'rb').read()
    clut=np.frombuffer(d[20:IMG],dtype='<u2').reshape(13,256)
    img=np.frombuffer(d[IMG:IMG+384*256],dtype='<u2').reshape(256,192)
    tile=img[:,64:128]; pix=np.zeros((256,256),np.uint8)
    for s in range(4): pix[:,s::4]=(tile>>(4*s))&15
    return d,clut,pix
def save(d,pix,path): open(path,'wb').write(dump(d,pix))
def dump(d,pix):
    d=bytearray(d); img=np.frombuffer(bytes(d[IMG:IMG+384*256]),dtype='<u2').reshape(256,192).copy()
    t=np.zeros((256,64),np.uint16)
    for s in range(4): t|=(pix[:,s::4].astype(np.uint16)&15)<<(4*s)
    img[:,64:128]=t; d[IMG:IMG+384*256]=img.tobytes(); return bytes(d)
def render(pix,clut,scale=4):
    pal=clut[5,112:128]
    rgb=np.stack([(pal[pix]&31)<<3,((pal[pix]>>5)&31)<<3,((pal[pix]>>10)&31)<<3],-1).astype(np.uint8)
    rgb[pix==15]=(255,0,255)
    return Image.fromarray(rgb).resize((pix.shape[1]*scale,pix.shape[0]*scale),Image.NEAREST)
