# Remix delta patch: every changed data sector of track 1 rebuilt from COPY ops (bytes of the player's own
# original disc) and LIT ops (new bytes). No raw game sector is shipped.
# format (gzip): 'CB2D' u32 ver | 8 src-check (crc32 of SCES exe user data, size) | u32 nsec |
#   per sector: u32 lba, 8 subheader, u16 nops, ops: u8 kind(0 copy,1 lit) u16 len [u32 src (lba*2048+off) | bytes]
import sys,struct,zlib,gzip,numpy as np
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import iso
SEC=2352; N=65795
class R(iso.Img):
    def __init__(s,src): s.f=open(src,'rb'); s.files={}; s._scan()
def main(SRC,DST,out):
    """SRC / DST: data track (track 1, MODE2/2352) of the original disc and of the Remix build"""
    a=open(SRC,'rb').read(N*SEC); b=open(DST,'rb').read(N*SEC)
    ua=np.frombuffer(a,np.uint8).reshape(N,SEC)[:,24:24+2048].copy()   # user data of every source sector
    flat=ua.reshape(-1)
    im=R(SRC)
    # source index: 8-byte keys at 4-byte stride over the useful files
    pos=[]
    for p,(l,sz,_) in im.files.items():
        if p.startswith('/MOVIE') or p.startswith('/CDDA') or sz>2_000_000 or sz==0: continue
        base=l*2048; pos.append(np.arange(base,base+max(0,sz-8),4,dtype=np.int64))
    pos=np.concatenate(pos)
    keyof=lambda arr,idx: (arr[idx[:,None]+np.arange(8)].astype(np.uint64)<<(np.arange(8,dtype=np.uint64)*8)).sum(1)
    keys=np.zeros(len(pos),np.uint64)
    for i in range(0,len(pos),2_000_000): keys[i:i+2_000_000]=keyof(flat,pos[i:i+2_000_000])
    order=np.argsort(keys,kind='stable'); keys=keys[order]; pos=pos[order]
    print('index',len(pos),flush=True)
    secs=[]; nlit=0; ncopy=0
    for i in range(N):
        x=a[i*SEC:(i+1)*SEC]; y=b[i*SEC:(i+1)*SEC]
        if x[16:24+2048]==y[16:24+2048]: continue
        t=np.frombuffer(y[24:24+2048],np.uint8)
        tk=np.zeros(2048,np.uint64); tk[:2041]=keyof(t,np.arange(2041))
        lo=np.searchsorted(keys,tk[:2041],'left'); hi=np.searchsorted(keys,tk[:2041],'right')
        ops=[]; p=0; lit=bytearray()
        def ext(src,p):  # forward length of match between t[p:] and flat[src:]
            n=0
            while p+n<2048 and src+n<len(flat) and flat[src+n]==t[p+n]: n+=1
            return n
        while p<2048:
            best=(0,0)
            n=ext(i*2048+p,p)                                    # same place in the source disc
            if n>best[0]: best=(n,i*2048+p)
            if p<2041 and hi[p]>lo[p] and n<64:
                for c in range(lo[p],min(hi[p],lo[p]+24)):
                    s=int(pos[c]); n2=ext(s,p)
                    if n2>best[0]: best=(n2,s)
            if best[0]>=12:
                if lit: ops.append((1,bytes(lit))); lit=bytearray()
                ops.append((0,best[0],best[1])); p+=best[0]
            else: lit.append(int(t[p])); p+=1
        if lit: ops.append((1,bytes(lit)))
        secs.append((i,y[16:24],ops))
        nlit+=sum(len(o[1]) for o in ops if o[0]==1); ncopy+=sum(o[1] for o in ops if o[0]==0)
    exe=im.read_file('/SCES_009.92')
    body=bytearray(b'CB2D'+struct.pack('<I',1)+struct.pack('<II',zlib.crc32(exe),len(exe))+struct.pack('<I',len(secs)))
    for lba,sub,ops in secs:
        body+=struct.pack('<I',lba)+sub+struct.pack('<H',len(ops))
        for o in ops:
            if o[0]==0: body+=struct.pack('<BHI',0,o[1],o[2])
            else: body+=struct.pack('<BH',1,len(o[1]))+o[1]
    gz=gzip.compress(bytes(body),9,mtime=0); open(out,'wb').write(gz)
    print('sectors',len(secs),'literal bytes',nlit,'copied bytes',ncopy,'patch',len(body),'gz',len(gz))
if __name__=='__main__': main(*sys.argv[1:4])   # original.bin remix.bin out.delta.gz
