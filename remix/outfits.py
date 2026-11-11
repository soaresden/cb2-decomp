# Hidden-outfit previews for the WEAR menu (Cindy = rider 2, Irin = rider 3).
# Each outfit = a base menu TIM (jacket / pants j) whose listed regions are recoloured through
#   new_idx = MAP_region[ SH[old_idx] ]     (SH = 16-level luminance of the base palette)
# MAP points either at freed palette slots (recoloured cloth, 16 shades per colour) or at the girl's
# own skin entries (taken from her face).  The game copies the base TIM, applies this, re-uploads it.
import os,struct,numpy as np
# Menu TIMs of Cindy and Irin, read from the player's own TITLE/CHR.DAT (never shipped):
# T[rider]['J'|'P'][j] = ((x,y,w,h,clut u16[256]), (x,y,w,h,pixels u16[h,64]), None)
def load_tims(chr_path=None):
    if chr_path is None:
        fs=os.environ.get('CB2_FS',os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'work','fs'))
        chr_path=os.path.join(fs,'TITLE','CHR.DAT')
    d=open(chr_path,'rb').read(); blocks=[]; o=0
    while o+12<len(d):      # TIM blocks: u32 length, u16 x,y,w,h, then w*h u16 (same scan as the site's menu.js)
        L,x,y,w,h=struct.unpack_from('<IHHHH',d,o)
        if w and h and L==12+w*h*2 and x<1024 and y<512 and L>200: blocks.append((o,x,y,w,h)); o+=L
        else: o+=2
    tims=[]; i=0
    while i+1<len(blocks):
        if blocks[i][3]==256 and blocks[i][4]==1 and blocks[i+1][3]==64: tims.append((blocks[i],blocks[i+1])); i+=2
        else: i+=1
    def arr(b): o,x,y,w,h=b; return np.frombuffer(d,'<u2',w*h,o+12).reshape(h,w) if h>1 else np.frombuffer(d,'<u2',w,o+12)
    T={}
    for r in (2,3):
        mine=[t for t in tims if t[1][1]==512+64*r]
        T[r]={k:[((c[1],c[2],c[3],c[4],arr(c).copy()),(m[1],m[2],m[3],m[4],arr(m).copy()),None) for c,m in mine if m[2]==y]
              for k,y in (('J',0),('P',144))}
        assert all(len(v)==3 for v in T[r].values()),(r,{k:len(v) for k,v in T[r].items()})
    return T
_T=None
class _Lazy:
    def __getitem__(s,k):
        global _T
        if _T is None: _T=load_tims()
        return _T[k]
T=_Lazy()
SKIN='skin'
def rgb555(c):
    c=np.asarray(c,np.uint32); return np.stack([(c&31)<<3,((c>>5)&31)<<3,((c>>10)&31)<<3],-1).astype(np.int32)
def to555(r,g,b):
    r,g,b=[max(8,min(255,int(v))) for v in (r,g,b)]; return (r>>3)|((g>>3)<<5)|((b>>3)<<10)
BLK=(34,32,40); WHT=(236,236,240); NAVY=(34,44,100)
# regions: (x0,y0,x1,y1, colour) in 8bpp TIM pixels
OUT={
 # Cindy: V1 black leather + long gloves + black shorts / V2 green crop top + knee denim / V3 periwinkle blouse + white skirt
 (2,0):{'J':[(0,0,96,48,BLK),(96,40,128,48,BLK),(64,48,128,112,BLK),(32,112,64,144,BLK)],
        'P':[(0,16,96,112,BLK),(96,48,128,57,BLK),(96,57,128,96,SKIN)]},
 (2,1):{'J':[(0,0,96,30,(64,124,46)),(0,30,96,48,SKIN),(96,40,128,48,SKIN),(64,48,128,112,SKIN),(32,112,64,144,SKIN)],
        'P':[(0,16,96,112,(92,114,166)),(96,48,128,74,(92,114,166)),(96,74,128,96,SKIN)]},
 (2,2):{'J':[(0,0,96,48,(132,142,222)),(96,40,128,48,(132,142,222)),(64,48,128,112,(132,142,222)),(32,112,64,144,SKIN)],
        'P':[(0,16,96,112,WHT),(96,48,128,58,WHT),(96,58,128,96,SKIN)]},
 # Irin: V1 sailor (white top, navy collar & skirt, white socks) / V2 mustard pinafore / V3 pink
 (3,0):{'J':[(0,0,96,8,NAVY),(0,8,96,48,WHT),(64,48,128,72,WHT),(64,72,128,112,SKIN),(32,112,64,144,SKIN)],
        'P':[(0,0,96,16,(56,44,40)),(0,16,96,112,NAVY),(96,48,128,61,NAVY),(96,61,128,103,SKIN),(96,103,128,112,WHT)]},
 (3,1):{'J':[(0,0,96,8,WHT),(0,8,96,48,(204,154,44)),(64,48,128,72,WHT),(64,72,128,112,SKIN),(32,112,64,144,SKIN)],
        'P':[(0,16,96,112,(204,154,44)),(96,48,128,61,(204,154,44)),(96,61,128,112,SKIN)]},
 (3,2):{'J':[(0,0,96,48,(236,144,174)),(64,48,128,72,WHT),(64,72,128,112,SKIN),(32,112,64,144,SKIN)],
        'P':[(0,16,96,112,(236,144,174)),(96,48,128,61,(236,144,174)),(96,61,128,112,SKIN)]},
}
FACE={2:(4,62,44,82),3:(4,66,44,86)}      # a patch of each girl's face (upper TIM) = skin palette entries
DELTA=9                                    # brightness step per shade (0..255 units)
def lum(c): return 0.3*c[...,0]+0.59*c[...,1]+0.11*c[...,2]
def tim(r,k,j):
    clut,im,p=T[r][k][j]; h=im[3]; return clut[4].copy(),im[4].view(np.uint8).reshape(h,128).copy()
def choose_base(r,k):
    best=None
    for j in range(3):
        pal,px=tim(r,k,j); m=np.zeros(px.shape,bool)
        for o in range(3):
            for x0,y0,x1,y1,c in OUT[(r,o)][k]: m[y0:y1,x0:x1]=True
        free=len(set(np.unique(px[m]))-set(np.unique(px[~m])))
        sc=np.std(lum(rgb555(pal))[px[m]])
        if free>=64 and (best is None or sc<best[0]): best=(sc,j)
    return best[1]
def build():
    """-> {(girl,part): {'j':..,'sh':bytes256}}, {(girl,outfit,part): {'regs':[(x0,y0,w,h,map16)], 'pal':[(idx,col555)]}}, previews"""
    BASE={}; REC={}; PREV={}
    for r in (2,3):
        for k in 'JP':
            j=choose_base(r,k); pal,px=tim(r,k,j); L=lum(rgb555(pal)); sh=np.clip(L/16,0,15).astype(np.uint8)
            m=np.zeros(px.shape,bool)
            for o in range(3):
                for x0,y0,x1,y1,c in OUT[(r,o)][k]: m[y0:y1,x0:x1]=True
            BASE[(r,k)]={'j':j,'sh':bytes(sh)}
            fpal,fpx=tim(r,'J',0); fx0,fy0,fx1,fy1=FACE[r]; fc=rgb555(fpal)[fpx[fy0:fy1,fx0:fx1]].reshape(-1,3)
            ok=(fc[:,0]>150)&(fc[:,0]>fc[:,1])&(fc[:,1]>fc[:,2]); SKC=tuple(int(v) for v in np.median(fc[ok],0))
            for o in range(3):
                regs=OUT[(r,o)][k]
                pal2=pal.copy(); px2=px.copy()
                mo=np.zeros(px.shape,bool)
                for x0,y0,x1,y1,c in regs: mo[y0:y1,x0:x1]=True
                free=sorted(set(np.unique(px[mo]))-set(np.unique(px[~mo]))-{0})
                regs=[(x0,y0,x1,y1,SKC if c is SKIN else c) for x0,y0,x1,y1,c in regs]
                cols=[]; [cols.append(c) for *_,c in regs if c not in cols]
                assert len(cols)*16<=len(free),(r,k,o,len(cols),len(free))
                slot={c:free[i*16:(i+1)*16] for i,c in enumerate(cols)}
                palpatch=[]
                for c in cols:
                    sel=np.zeros(px.shape,bool)
                    for x0,y0,x1,y1,cc in regs:
                        if cc==c: sel[y0:y1,x0:x1]=True
                    med=float(np.median(sh[px[sel]]))
                    for s in range(16):
                        d=(s-med)*DELTA*(0.6 if c==SKC else 1); v=to555(c[0]+d,c[1]+d,c[2]+d); palpatch.append((slot[c][s],v)); pal2[slot[c][s]]=v
                out=[]
                for x0,y0,x1,y1,c in regs:
                    mp=list(slot[c])
                    out.append((x0,y0,x1-x0,y1-y0,bytes(mp)))
                    blk=px[y0:y1,x0:x1]; px2[y0:y1,x0:x1]=np.array(mp,np.uint8)[sh[blk]]
                REC[(r,o,k)]={'regs':out,'pal':palpatch}
                PREV[(r,o,k)]=rgb555(pal2)[px2].astype(np.uint8)
    return BASE,REC,PREV
if __name__=='__main__':
    from PIL import Image
    B,R,P=build()
    for r in (2,3):
        for o in range(3):
            a=P[(r,o,'J')]; b=P[(r,o,'P')]; im=np.zeros((256,128,3),np.uint8); im[:144]=a; im[144:]=b
            Image.fromarray(im).resize((384,768),Image.NEAREST).save(f'outfit_{r}{o}.png')
    print({k:v['j'] for k,v in B.items()}, sum(4+len(v['regs'])*20+len(v['pal'])*4 for v in R.values()))
