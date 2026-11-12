# tiny MIPS assembler for the few ops we need
R={n:i for i,n in enumerate('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}
def r(x): return R[x.strip().lstrip('$')]
def I(op,rs,rt,imm): return (op<<26)|(r(rs)<<21)|(r(rt)<<16)|(imm&0xffff)
def Rr(fn,rs,rt,rd,sh=0): return (r(rs)<<21)|(r(rt)<<16)|(r(rd)<<11)|(sh<<6)|fn
def asm(lines,org,syms=None):
    labels=dict(syms or {}); pc=org; prog=[]
    for l in lines:
        l=l.split('#')[0].strip()
        if not l: continue
        if l.endswith(':'): labels[l[:-1]]=pc; continue
        prog.append((pc,l)); pc+=4
    out=[]
    for pc,l in prog:
        m,_,a=l.partition(' '); a=[x.strip() for x in a.split(',')] if a else []
        def imm(x):
            return labels[x] if x in labels else int(x,0)
        def br(x): return ((imm(x)-(pc+4))>>2)&0xffff
        if m=='nop': w=0
        elif m=='addiu': w=I(9,a[1],a[0],imm(a[2]))
        elif m=='slti': w=I(10,a[1],a[0],imm(a[2]))
        elif m=='sltiu': w=I(11,a[1],a[0],imm(a[2]))
        elif m=='andi': w=I(12,a[1],a[0],imm(a[2]))
        elif m=='ori': w=I(13,a[1],a[0],imm(a[2]))
        elif m=='xori': w=I(14,a[1],a[0],imm(a[2]))
        elif m=='lui': w=I(15,'zero',a[0],imm(a[1]))
        elif m in('lw','sw','lh','lhu','sh','lb','lbu','sb'):
            off,base=a[1].rstrip(')').split('(')
            op={'lw':0x23,'sw':0x2b,'lh':0x21,'lhu':0x25,'sh':0x29,'lb':0x20,'lbu':0x24,'sb':0x28}[m]
            w=I(op,base,a[0],imm(off))
        elif m=='beq': w=(4<<26)|(r(a[0])<<21)|(r(a[1])<<16)|br(a[2])
        elif m=='bne': w=(5<<26)|(r(a[0])<<21)|(r(a[1])<<16)|br(a[2])
        elif m=='beqz': w=(4<<26)|(r(a[0])<<21)|br(a[1])
        elif m=='bnez': w=(5<<26)|(r(a[0])<<21)|br(a[1])
        elif m=='blez': w=(6<<26)|(r(a[0])<<21)|br(a[1])
        elif m=='bgtz': w=(7<<26)|(r(a[0])<<21)|br(a[1])
        elif m=='bltz': w=(1<<26)|(r(a[0])<<21)|(0<<16)|br(a[1])
        elif m=='bgez': w=(1<<26)|(r(a[0])<<21)|(1<<16)|br(a[1])
        elif m=='j': w=(2<<26)|((imm(a[0])>>2)&0x3ffffff)
        elif m=='jal': w=(3<<26)|((imm(a[0])>>2)&0x3ffffff)
        elif m=='jr': w=Rr(8,a[0],'zero','zero')
        elif m=='addu': w=Rr(0x21,a[1],a[2],a[0])
        elif m=='subu': w=Rr(0x23,a[1],a[2],a[0])
        elif m=='and': w=Rr(0x24,a[1],a[2],a[0])
        elif m=='or': w=Rr(0x25,a[1],a[2],a[0])
        elif m=='xor': w=Rr(0x26,a[1],a[2],a[0])
        elif m=='slt': w=Rr(0x2a,a[1],a[2],a[0])
        elif m=='sltu': w=Rr(0x2b,a[1],a[2],a[0])
        elif m=='mult': w=Rr(0x18,a[0],a[1],'zero')
        elif m=='mflo': w=Rr(0x12,'zero','zero',a[0])
        elif m=='mfhi': w=Rr(0x10,'zero','zero',a[0])
        elif m=='divu': w=Rr(0x1b,a[0],a[1],'zero')
        elif m=='sllv': w=Rr(4,a[2],a[1],a[0])
        elif m=='srlv': w=Rr(6,a[2],a[1],a[0])
        elif m=='nor': w=Rr(0x27,a[1],a[2],a[0])
        elif m=='sll': w=Rr(0,'zero',a[1],a[0],int(a[2],0))
        elif m=='srl': w=Rr(2,'zero',a[1],a[0],int(a[2],0))
        elif m=='sra': w=Rr(3,'zero',a[1],a[0],int(a[2],0))
        elif m=='move': w=Rr(0x21,a[1],'zero',a[0])
        else: raise Exception('unknown '+l)
        out.append((pc,w))
    return out,labels
