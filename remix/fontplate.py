import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
FONT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'fonts','FreeSansBoldOblique.ttf')
def plate(text,clut,size=12,h=12,track=0):
    pal=clut[5,112:128]; lum=[((p&31)+((p>>5)&31)+((p>>10)&31))/3*255/31 for p in pal[:15]]
    f=ImageFont.truetype(FONT,size)
    W=200; im=Image.new('RGBA',(W,h+6),(0,0,0,0)); dr=ImageDraw.Draw(im)
    x=1
    for ch in text:
        dr.text((x,-1),ch,font=f,fill=(255,255,255,255),stroke_width=1,stroke_fill=(16,16,16,255))
        x+=f.getlength(ch)+track
    a=np.array(im)[:h]
    cols=np.where(a[...,3].max(0)>100)[0]; a=a[:,cols.min():cols.max()+1]
    out=np.full(a.shape[:2],15,np.uint8)
    m=a[...,3]>110; g=a[...,:3].mean(-1)
    idx=np.array([min(range(15),key=lambda i:abs(lum[i]-v)) for v in g.flatten()]).reshape(g.shape)
    out[m]=idx[m]
    return out
if __name__=='__main__':
    import os
    from tile import *
    d,clut,pix=load(os.path.join(os.environ.get('CB2_FS','work/fs'),'DATA/EFFECT/EFCT_SBC.FBD'))
    ims=[]
    for s in (11,12,13):
        for t in ('GRAY','SNOWMAN','BOSS'):
            p=plate(t,clut,s); ims.append(render(p,clut,5)); print(s,t,p.shape)
    ims.append(render(pix[176:188,88:128],clut,5))
    H=sum(i.height+4 for i in ims); W=max(i.width for i in ims)
    o=Image.new('RGB',(W,H),(40,40,40)); y=0
    for i in ims: o.paste(i,(0,y)); y+=i.height+4
    o.save('plates_preview.png')
