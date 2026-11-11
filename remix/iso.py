import struct,shutil,os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'tools'))
from cb2disc import fix_sector as fix_mode2
SEC=2352
class Img:
    def __init__(s,src,dst):
        if not os.path.exists(dst) or os.path.getsize(dst)!=os.path.getsize(src):
            shutil.copyfile(src,dst)
        s.f=open(dst,'r+b'); s.dirty=set()
        s.files={}; s._scan()
    def rd(s,n):
        s.f.seek(n*SEC+24); return s.f.read(2048)
    def _scan(s):
        pvd=s.rd(16)
        def walk(lba,size,path,recloc):
            s.files[path or '/']=(lba,size,recloc)
            nsec=(size+2047)//2048
            for k in range(nsec):
                data=s.rd(lba+k); i=0
                while i<2048:
                    l=data[i]
                    if l==0: break
                    r=data[i:i+l]
                    el,=struct.unpack('<I',r[2:6]); sz,=struct.unpack('<I',r[10:14]); fl=r[25]; nl=r[32]; name=r[33:33+nl]
                    if name not in (b'\0',b'\1'):
                        nm=name.decode().split(';')[0]; p=path+'/'+nm
                        if fl&2: walk(el,sz,p,(lba+k,i))
                        else: s.files[p]=(el,sz,(lba+k,i))
                    i+=l
        r=pvd[156:190]; walk(struct.unpack('<I',r[2:6])[0],struct.unpack('<I',r[10:14])[0],'',None)
    def write_user(s,lba,off,data,subhdr=None):
        """write bytes into user data area starting at sector lba, byte offset off (form1)"""
        pos=0
        while pos<len(data):
            n=lba+(off+pos)//2048; o=(off+pos)%2048; k=min(2048-o,len(data)-pos)
            s.f.seek(n*SEC); sec=bytearray(s.f.read(SEC))
            if subhdr is not None: sec[0x10:0x18]=subhdr*2 if len(subhdr)==4 else subhdr
            sec[24+o:24+o+k]=data[pos:pos+k]
            fix_mode2(sec); s.f.seek(n*SEC); s.f.write(sec)
            pos+=k
    def read_file(s,path):
        lba,size,_=s.files[path]
        return b''.join(s.rd(lba+k) for k in range((size+2047)//2048))[:size]
    def set_record(s,path,lba=None,size=None):
        _,_,(dl,di)=s.files[path]
        sec=bytearray(s.rd(dl))
        if lba is not None: sec[di+2:di+10]=struct.pack('<I',lba)+struct.pack('>I',lba)
        if size is not None: sec[di+10:di+18]=struct.pack('<I',size)+struct.pack('>I',size)
        s.write_user(dl,0,bytes(sec))
        old=s.files[path]; s.files[path]=(lba if lba is not None else old[0], size if size is not None else old[1], old[2])
def msf_bcd(lba):
    a=lba+150; m,sc,f=a//4500,(a//75)%60,a%75
    b=lambda x:(x//10)*16+x%10
    return bytes([b(m),b(sc),b(f),0])
