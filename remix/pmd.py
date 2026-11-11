import struct
# PSX GPU textured primitive sizes (words incl. command) for gouraud/flat textured tri/quad
SIZES={0x24:7,0x25:7,0x26:7,0x27:7,0x2c:9,0x2d:9,0x2e:9,0x2f:9,0x34:9,0x35:9,0x36:9,0x37:9,0x3c:12,0x3d:12,0x3e:12,0x3f:12}
def scan(b):
    """heuristic: find GPU textured prims: word w with (w>>24) in SIZES, then clut/tpage fields"""
    W=list(struct.unpack(f'<{len(b)//4}I',b)); prims=[]
    i=0
    while i<len(W):
        cmd=W[i]>>24
        if cmd in SIZES:
            n=SIZES[cmd]; g=cmd&0x10; q=cmd&0x08
            # layout: cmd/col, xy0, clut|uv0, [col1], xy1, tpage|uv1, [col2], xy2, uv2, ...
            if g: idx_uv=[i+2,i+5,i+8]+([i+11] if q else [])
            else: idx_uv=[i+2,i+4,i+6]+([i+8] if q else [])
            if i+n<=len(W):
                clut=W[idx_uv[0]]>>16; tp=W[idx_uv[1]]>>16
                if tp<0x200:
                    prims.append((i,cmd,idx_uv,clut,tp)); i+=n; continue
        i+=1
    return W,prims
