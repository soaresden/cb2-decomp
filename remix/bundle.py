import struct
def parse(d):
    n=struct.unpack('<I',d[4:8])[0]
    offs=[n*4]+[x*4 for x in struct.unpack(f'<{n-2}I',d[8:8+4*(n-2)])]+[len(d)]
    return [d[offs[i]:offs[i+1]] for i in range(len(offs)-1)]
def build(parts,magic=0x08524843):
    n=len(parts)+1
    hdr=[magic,n]; off=n*4; offs=[]
    for p in parts[:-1]:
        off+=len(p); offs.append(off//4)
    assert all(len(p)%4==0 for p in parts)
    return struct.pack(f'<{n}I',*(hdr+offs))+b''.join(parts)
