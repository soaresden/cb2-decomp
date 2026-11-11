# WEAR menu: preview of Cindy/Irin hidden outfits (code + data appended to MAIN_SEL.BIN, see outfits.py)
import struct
from asm import asm
import outfits
BASE=0x8007d18c                     # old end of MAIN_SEL (= old heap start)
BUF=(0x801f2000,0x801f7000)         # copies of the upper / lower TIM (free RAM below the menu stack)
TBL=(0x8007c488,0x8007c4b8)
def hl(a): h=(a+0x8000)>>16; return h,a-(h<<16)
def block():
    B,R,_=outfits.build()
    keys=[(2,'J'),(2,'P'),(3,'J'),(3,'P')]
    OUTV=BASE; SH=BASE+4; RT=SH+4*256; REC0=RT+12*4
    data=bytearray(struct.pack('<i',-1))
    for k in keys: data+=B[k]['sh']
    recs=bytearray(); ptr=[]
    for g in (2,3):
        for o in range(3):
            for k in 'JP':
                ptr.append(REC0+len(recs)); r=R[(g,o,k)]
                recs+=bytes([B[(g,k)]['j'],len(r['regs']),len(r['pal']),keys.index((g,k))])
                for x0,y0,w,h,mp in r['regs']: recs+=bytes([x0,y0,w,h])+mp
                for i,c in r['pal']: recs+=struct.pack('<HH',i,c)
    data+=struct.pack('<12I',*ptr)+recs
    data+=bytes((-len(data))%4)
    CODE=BASE+len(data)
    oh,ol=hl(OUTV); sh_,sl=hl(SH); rh,rl=hl(RT)
    L=[
     # replaces 'lh v0,0(s4)' at the start of the preview: jacket index -> base TIM, remembers the outfit
     'wprv0:','lh v0, 0(s4)','sll t0, s1, 16','sra t0, t0, 16','addiu t0, t0, -2','addiu t1, zero, -1',
     'slti t2, v0, 3','bnez t2, wp9','nop','sltiu t2, t0, 2','beqz t2, wp8','addiu v0, v0, -3',
     'sll t1, t0, 1','addu t1, t1, t0','addu t1, t1, v0',
     'wp8:','nop','wp9:',f'lui at, {oh}','jr ra',f'sw t1, {ol}(at)',
     # end of the preview (replaces 'lw ra,0x182c(sp)', s4 already restored, s0-s3 restored after us)
     'wend:',f'lui at, {oh}',f'lw s0, {ol}(at)','nop','bltz s0, we9','move s1, zero',
     'wpart:','sll t0, s0, 1','addu t0, t0, s1','sll t0, t0, 2',f'lui at, {rh}','addu at, at, t0',f'lw s2, {rl}(at)',
     'slti t1, s0, 3','xori t1, t1, 1','addiu t1, t1, 2',            # rider 2/3
     'sll t2, t1, 3','sll t1, t1, 2','addu t1, t1, t2',               # rider*12
     'lbu t2, 0(s2)','nop','sll t2, t2, 2','addu t1, t1, t2',
     'sll t2, s1, 4','sll t3, s1, 5','addu t2, t2, t3','addu t1, t1, t2',   # + part*0x30
     f'lui at, {hl(TBL[0])[0]}','addu at, at, t1',f'lw t4, {hl(TBL[0])[1]}(at)',  # src TIM
     f'lui s3, {hl(BUF[0])[0]}','beqz s1, wb0',f'addiu s3, s3, {hl(BUF[0])[1]}',
     f'lui s3, {hl(BUF[1])[0]}',f'addiu s3, s3, {hl(BUF[1])[1]}',
     'wb0:','lw t5, 0x214(t4)','move t6, s3','addiu t5, t5, 0x214','addu t5, t5, t4',
     'wcp:','lw t7, 0(t4)','addiu t4, t4, 4','sw t7, 0(t6)','bne t4, t5, wcp','addiu t6, t6, 4',
     # regions
     'lbu t0, 3(s2)',f'lui t9, {sh_}','sll t0, t0, 8','addu t9, t9, t0',f'addiu t9, t9, {sl}',
     'lbu t8, 1(s2)','addiu t7, s2, 4',
     'wrg:','beqz t8, wpal','lbu t0, 1(t7)','lbu t1, 3(t7)','lbu t2, 0(t7)',
     'sll t0, t0, 7','addu t0, t0, t2','addu t0, t0, s3','addiu t0, t0, 0x220',   # row ptr
     'wry:','lbu t3, 2(t7)','move t4, t0',
     'wrx:','lbu t5, 0(t4)','nop','addu t5, t5, t9','lbu t5, 0(t5)','nop','addu t5, t5, t7','lbu t5, 4(t5)','addiu t3, t3, -1','sb t5, 0(t4)','bnez t3, wrx','addiu t4, t4, 1',
     'addiu t1, t1, -1','bnez t1, wry','addiu t0, t0, 128',
     'addiu t8, t8, -1','j wrg','addiu t7, t7, 20',
     # palette entries
     'wpal:','lbu t8, 2(s2)','nop',
     'wpl:','beqz t8, wup','lhu t0, 0(t7)','lhu t1, 2(t7)','sll t0, t0, 1','addu t0, t0, s3','sh t1, 0x14(t0)','addiu t8, t8, -1','j wpl','addiu t7, t7, 4',
     'wup:','jal 0x8005db60','move a0, s3',
     'addiu s1, s1, 1','slti t0, s1, 2','bnez t0, wpart','nop',
     'we9:','lw ra, 0x182c(sp)','j 0x80064218','nop']
    code,lab=asm(L,CODE)
    blk=bytearray(data)
    for a,w in code: blk+=struct.pack('<I',w)
    return bytes(blk),lab
if __name__=='__main__':
    b,l=block(); print(len(b),{k:hex(v) for k,v in l.items() if k in('wprv0','wend')})
