import sys,struct,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from iso import Img,msf_bcd
from asm import asm
import boardmax as _bm
from bundle import parse,build
# files of the original disc, extracted by make_remix.py (env CB2_FS to override)
FS=os.environ.get('CB2_FS',os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'work','fs'))
OVL=0x8005aea8; EXE=0x80010000
RM=0x8004fb28
FLIP_DELAY=4
PL_V=239; PL_SNOW_U=120; PL_GRAY_U=188; PL_W={'SNOWMAN':61,'GRAY':38}
TL_N=1; TL_X0=int(__import__('os').environ.get('TL_X0','-40')); TL_DX=int(__import__('os').environ.get('TL_DX','84')); TL_Y0=int(__import__('os').environ.get('TL_Y0','-34')); TL_DY=int(__import__('os').environ.get('TL_DY','0')); TL_RX=int(__import__('os').environ.get('TL_RX','156')); TL_LY=int(__import__('os').environ.get('TL_LY','0x48'),0)
FLIP_K=int(__import__('os').environ.get('FLIP_K','0'))
SQ_SH=int(__import__('os').environ.get('SQ_SH','1'))
MAXL_X=int(__import__('os').environ.get('MAXL_X','250')); MAXL_Y=int(__import__('os').environ.get('MAXL_Y','90')); MAXL_W=int(__import__('os').environ.get('MAXL_W','30'))
KD_R=int(__import__('os').environ.get('KD_R','130')); KD_RY=int(__import__('os').environ.get('KD_RY','260')); KD_V=int(__import__('os').environ.get('KD_V','20')); KD_CD=int(__import__('os').environ.get('KD_CD','2'))
HINT_X=int(__import__('os').environ.get('HINT_X','10')); HINT_Y=int(__import__('os').environ.get('HINT_Y','236')); HINT_F=int(__import__('os').environ.get('HINT_F','1')); HINT1=b'R1 : MAX'; HINT2=b'R1 : NORMAL'
AIR_K=int(__import__('os').environ.get('AIR_K','0'))
CAVE_TEX=0x8004f800; CAVE_PL=0x8004f840; CAVE_EN=0x8004f8a0; CAVE_SLOT=0x8004f940; CAVE_PAD=0x8004f980; LOCTBL=0x8004f900
def jal(a): return (3<<26)|((a>>2)&0x3ffffff)
def br(w,src,dst): return (w&0xffff0000)|(((dst-(src+4))>>2)&0xffff)
def idx_for(addr): return (addr-0x800583e8)//8
from pmd import scan
def conv_model(b,page,clut_dy,du=0):
    """relocate a free-ride model's texture refs: tpage 9->page, CLUT rows +clut_dy, u+du"""
    W,pr=scan(b); W=list(W); n=0
    for i,cmd,uvs,clut,tp in pr:
        if (tp&0xf)!=9 or (clut>>6) not in (493,494): continue
        W[uvs[0]]=(W[uvs[0]]&0xffff)|(((clut+(clut_dy<<6))&0xffff)<<16)
        W[uvs[1]]=(W[uvs[1]]&0xffff)|(((tp&~0xf)|page)<<16)
        if du:
            for k in uvs: W[k]=(W[k]&~0xff)|(((W[k]&0xff)+du)&0xff)
        n+=1
    return struct.pack(f'<{len(W)}I',*W),n
def swap_boss_jicchi(e):
    """ENEMY1: swap the CLUT rows of rider 4 (rows 8,9) and rider 7 (rows 14,15): rider 4 gets the tan 'Boss'
    look and rider 7 the dark one, matching the swapped name plates (4 = BOSS, 7 = JICCHI)"""
    e=bytearray(e); c=20
    for r0,r1 in ((8,14),(9,15)):
        a=e[c+r0*512:c+(r0+1)*512]; e[c+r0*512:c+(r0+1)*512]=e[c+r1*512:c+(r1+1)*512]; e[c+r1*512:c+(r1+1)*512]=a
    return e
def swap_name_plates(d):
    """results name-plate table (10-byte entries, rider order YAGGI JIN CINDY IRIN JICCHI NICK KELLY BOSS): 4 <-> 7"""
    d=bytearray(d); sig=bytes([192,24,48,0,12,0]); i=d.find(sig)
    if i<0: return d,False
    t=i-40; assert d[t:t+3]==bytes([208,160,40]) and d[t+70:t+73]==bytes([88,176,40]),hex(t)
    a=d[t+40:t+50]; d[t+40:t+50]=d[t+70:t+80]; d[t+70:t+80]=a
    return d,True
def enemy_variant(fbd_name,col0=0,row0=14):
    """ENEMY1 with columns col0..col0+31 of image and CLUT rows row0,row0+1 replaced by a free-ride FBD"""
    e=swap_boss_jicchi(open(FS+'/DATA/CHR/ENEMY1.FBD','rb').read()); f=open(FS+'/DATA/CHR/FR/FBD3/'+fbd_name,'rb').read()
    clut_e=20; img_e=20+256*16*2; clut_f=20; img_f=20+256*2*2
    for r in range(2): e[clut_e+(row0+r)*512:clut_e+(row0+r+1)*512]=f[clut_f+r*512:clut_f+(r+1)*512]
    for y in range(256): e[img_e+y*384+col0*2:img_e+y*384+col0*2+64]=f[img_f+y*64:img_f+(y+1)*64]
    return bytes(e)
def bundles():
    p0=parse(open(FS+'/DATA/CHR/PLAYER0.DAT','rb').read())
    p1=parse(open(FS+'/DATA/CHR/PLAYER1.DAT','rb').read())
    low=[p1[0],p0[1],p0[2],p0[3],p0[4],p0[5],p0[6],p0[7]]   # all 8 riders, low detail, CPU textures
    rd=lambda n: open(FS+'/DATA/CHR/FR/1P/'+n,'rb').read()
    # Gray player = slot 5 (Kelly CPU skipped). Gray's texture goes to Nick's area (page 7 left, CLUT 507-508),
    # so CPU slot 6 ("Nick") uses Kelly's model whose texture area (page 6 right) is free.
    g,ng=conv_model(rd('GRAY.PMD'),7,14); gray=list(low); gray[5]=g; gray[6]=p0[5]
    # Snow player = slot 6 (Nick CPU skipped) -> Nick's texture area
    sm,ns=conv_model(rd('SNOW.PMD'),7,14); snow=list(low); snow[6]=sm
    assert ng>500 and ns>500,(ng,ns)
    return build(gray),build(snow),enemy_variant('GRAY0.FBD'),enemy_variant('SNOW0.FBD')
def patches():
    P=[]
    # --- MAIN_SEL: competition boarder list 4 -> 7
    P+=[('/MAIN_SEL.BIN',0x80063fc8,0x28420004,0x28420007),
        ('/MAIN_SEL.BIN',0x80063fcc,0x14400031,br(0x14400031,0x80063fcc,0x80063fa4)),
        ('/MAIN_SEL.BIN',0x80064044,0x14620012,br(0x14620012,0x80064044,0x8006401c))]
    # --- pad: in race overlays, Triangle = grind (L1+R1)
    # ---- rider stats MAX (Circle on the BOARDER screen). Code + data live in a dead libc-ish function of the exe
    # (0x8002957c..0x8002979f: never referenced, never executed).
    DZ=0x8002957c; DZ2=0x8002a030; ACT=DZ2; STR1=DZ2+4; STR2=DZ2+0x10; DC2=DZ2+0x20; FLAG=DZ; MAXE=DZ+4; SAVE=DZ+0x14; EDGE=DZ+0x18; DC=DZ+0x1c
    lo=lambda a: a-((a+0x8000)&0xffff0000)
    MX=[  # player's rider param pointer -> MAXE (racer creation in every race overlay)
        *[x for b in ('s3','s0') for x in (
        f'maxc_{b}:','lui at, 0x8003',f'lw at, {lo(FLAG)}(at)','nop',f'beqz at, mn_{b}','lui at, 0x8005','lh at, 0x7408(at)','nop','sll at, at, 4',
        f'bne at, v0, mn_{b}','nop','lui v0, 0x8003',f'j ms_{b}',f'addiu v0, v0, {lo(MAXE)}',f'mn_{b}:','addu v0, v0, v1',f'ms_{b}:','jr ra',f'sw v0, 0x54({b})')],
        # BOARDER screen bars: every stat shown at 10 while MAX is on
        # (+ Circle edge toggles MAX: this runs only while the BOARDER screen shows its bars)
        # (registers: only at/v0/a0 -- the bars loop keeps t0/t1 live across this call)
        'maxd:',f'lui at, {_bm.hi(_bm.MASKV)}','addiu v0, zero, 0x08',f'sw v0, {_bm.lo(_bm.MASKV)}(at)','lui at, 0x8005','lw a0, -0x410(at)','lui at, 0x8003','addiu v0, zero, 8',f'sw v0, {lo(ACT)}(at)','andi a0, a0, 0x08',f'lw v0, {lo(EDGE)}(at)',f'sw a0, {lo(EDGE)}(at)','beqz a0, md0','nop','bnez v0, md0','nop',
        f'lw v0, {lo(FLAG)}(at)','nop','xori v0, v0, 1',f'sw v0, {lo(FLAG)}(at)',
        'md0:','lh a0, 0(a1)',f'lw at, {lo(FLAG)}(at)','nop','beqz at, md1','nop','addiu a0, zero, 10','md1:','jr ra','nop',
        ]
    _ex=open(os.path.join(FS,'SCES_009.92'),'rb').read()
    cmx,lmx=asm(MX,DC); assert cmx[-1][0]<0x800297a0,hex(cmx[-1][0])
    MX2=[
        # pad hook (port 0): while the BOARDER screen is up (ACT refreshed by maxd), R1 is eaten (it is the MAX toggle there)
        'padx:',f'lui at, {_bm.hi(_bm.RAWP)}',f'sw a2, {_bm.lo(_bm.RAWP)}(at)','lui at, 0x8003',f'lw t0, {lo(ACT)}(at)','nop','beqz t0, px9','addiu t0, t0, -1',f'sw t0, {lo(ACT)}(at)',
        f'lui at, {_bm.hi(_bm.MASKV)}',f'lw t0, {_bm.lo(_bm.MASKV)}(at)','nop','nor t0, t0, zero','and a2, a2, t0',
        'px9:',f'j {RM}','nop',
        # BOARDER screen labels: + 'MAX' label under the portrait when on, + the hint text
        'maxl:','addiu sp, sp, -0x30','sw ra, 0x2c(sp)','lw t0, 0x40(sp)','nop','sw t0, 0x10(sp)','jal 0x8005cc78','sw t0, 0x28(sp)',
        'lw t1, 0x28(sp)','lui at, 0x8003','bnez t1, ml9',f'lw t0, {lo(FLAG)}(at)',
        'nop','beqz t0, ml5','nop','move a0, s4','move a1, v0','sw zero, 0x10(sp)',f'addiu a2, zero, {MAXL_X}','jal 0x8005cc78',f'addiu a3, zero, {MAXL_Y}',
        'lh t0, -0x20(v0)','lbu t1, -0x1c(v0)',f'addiu t0, t0, {MAXL_W}',f'addiu t1, t1, {MAXL_W}','sh t0, -0x18(v0)','sh t0, -0x8(v0)','sb t1, -0x14(v0)','sb t1, -0x4(v0)',
        'ml5:','lui at, 0x8003',f'lw t0, {lo(FLAG)}(at)',f'addiu a2, at, {lo(STR1)}','beqz t0, ml6','nop',f'addiu a2, at, {lo(STR2)}',
        'ml6:','move a0, s4','move a1, v0',f'addiu t0, zero, {HINT_Y}','sw t0, 0x10(sp)','sw zero, 0x14(sp)',f'addiu t0, zero, {HINT_F}','sw t0, 0x18(sp)','jal 0x8005e784',f'addiu a3, zero, {HINT_X}',
        'ml9:','lw ra, 0x2c(sp)','addiu sp, sp, 0x30','jr ra','nop']
    cmx2,lmx2=asm(MX2,DC2); assert cmx2[-1][0]<0x8002a180,hex(cmx2[-1][0])
    lmx.update(lmx2)
    for a_,w_ in cmx2: P.append(('/SCES_009.92',a_,struct.unpack_from('<I',_ex,a_-0x8000f800)[0],w_))
    _sb=bytearray(0x1c); _sb[0:len(HINT1)]=HINT1; _sb[0xc:0xc+len(HINT2)]=HINT2
    for i_ in range(0,0x1c,4): P.append(('/SCES_009.92',STR1+i_,struct.unpack_from('<I',_ex,STR1+i_-0x8000f800)[0],struct.unpack_from('<I',_sb,i_)[0]))
    P.append(('/SCES_009.92',ACT,struct.unpack_from('<I',_ex,ACT-0x8000f800)[0],0))
    for a_,w_ in cmx: P.append(('/SCES_009.92',a_,struct.unpack_from('<I',_ex,a_-0x8000f800)[0],w_))
    for a_,w_ in ((FLAG,0),(MAXE,0x1400),(MAXE+4,0x1400),(MAXE+8,(29<<16)|(-136&0xffff)),(MAXE+12,(113<<16)|12),(SAVE,0),(EDGE,0)):
        P.append(('/SCES_009.92',a_,struct.unpack_from('<I',_ex,a_-0x8000f800)[0],w_))
    JL=lambda t:(3<<26)|((t>>2)&0x3ffffff)
    for f,a_,b in (('/SBC1.BIN',0x80063f04,'s3'),('/SBC2.BIN',0x80065be4,'s3'),('/VS.BIN',0x80064e08,'s0'),('/OMT.BIN',0x80063c58,'s0'),('/BP.BIN',0x80063b1c,'s0'),
                   ('/HP.BIN',0x80063d0c,'s0'),('/FREE.BIN',0x8006465c,'s0'),('/TM.BIN',0x80063c38,'s0'),('/COMB.BIN',0x80064b88,'s0')):
        P.append((f,a_,0x00431021,JL(lmx['maxc_'+b])))
    P+=[('/MAIN_SEL.BIN',0x800614b8,0x84a40000,JL(lmx['maxd'])),('/MAIN_SEL.BIN',0x800626e4,0x0c01731e,JL(lmx['maxl']))]
    # ---- board MAX (Circle on the BOARD screen): when on, every race overlay gets, right after it is loaded, the row
    # of the player's board (0x8005740A) in its board table (10 bytes per board: max speed, response, stability x 3
    # variants) replaced by the highest values of the game. Code in another dead function of the exe (func_8002815C, never referenced)
    BZ=0x8002815c; BT=[0x800980ec,0x8008c9fc,0x8008f3dc,0x800988b0,0x8009a9d8,0x800943d4,0x800944e4,0x80093e70,0x80098074]
    BMAX=bytes([165,157,196,100,110,80,80,88,80])
    hb=(BZ+0x8000)>>16; lob=lambda a: a-(hb<<16)
    # ovh: in place of the main loop's call of the overlay entry (exe 0x8001228c, overlay fully loaded by then):
    # if board MAX is on, find which race overlay is in (its board table starts with board 0 = 104, _, 123) and
    # overwrite the row of the player's board, then enter the overlay (a0 untouched, ra = the main loop)
    BX=['ovh:',f'lui at, {hb}','lw t0, FLAGB_LO(at)','lui t3, 0x8005','beqz t0, go','lh t3, 0x740a(t3)','addiu t1, at, TBL_LO','sltiu t2, t3, 14','beqz t2, go','nop',
        'o1:','lw t2, 0(t1)','nop','beqz t2, go','addiu t1, t1, 4','lbu t4, 0(t2)','lbu t5, 2(t2)','addiu t6, zero, 104','bne t4, t6, o1','addiu t6, zero, 123','bne t5, t6, o1','nop',
        'sll t4, t3, 2','addu t4, t4, t3','sll t4, t4, 1','addu t2, t2, t4','addiu t5, at, ROW_LO','addiu t6, zero, 9',
        'o2:','lbu t7, 0(t5)','addiu t6, t6, -1','sb t7, 0(t2)','addiu t5, t5, 1','bnez t6, o2','addiu t2, t2, 1',
        'go:','j 0x8005aeac','nop',
        ]+_bm.maxb('FLAGB_LO','EDGEB_LO',hb)
    def _bx(code_end):
        d={'FLAGB_LO':lob(code_end),'EDGEB_LO':lob(code_end+4),'TBL_LO':lob(code_end+8),'ROW_LO':lob(code_end+8+40)}
        return [x.replace('FLAGB_LO',str(d['FLAGB_LO'])).replace('EDGEB_LO',str(d['EDGEB_LO'])).replace('TBL_LO',str(d['TBL_LO'])).replace('ROW_LO',str(d['ROW_LO'])) for x in BX]
    cb,_=asm(_bx(BZ+0x400),BZ); cend=(cb[-1][0]+4+3)&~3
    cb,lbx=asm(_bx(cend),BZ)
    bdata=struct.pack('<II',0,0)+b''.join(struct.pack('<I',t) for t in BT)+bytes(4)+BMAX+bytes(3)
    words=[(a_,w_) for a_,w_ in cb]+[(cend+i,struct.unpack_from('<I',bdata,i)[0]) for i in range(0,len(bdata),4)]
    assert words[-1][0]<0x80028414,hex(words[-1][0])
    for a_,w_ in words: P.append(('/SCES_009.92',a_,struct.unpack_from('<I',_ex,a_-0x8000f800)[0],w_))
    P+=[('/SCES_009.92',0x8001228c,0x0c016bab,JL(lbx['ovh']))]+[('/MAIN_SEL.BIN',a_,0x0c01731e,JL(lbx['maxb'])) for a_ in (0x8006b68c,0x8006be3c,0x8006caac)]
    # MAX line of the BOARD screen: design screen with the 21 designs, labels (code in the dead func_8001B774)
    P+=_bm.patches(cend,lbx,_ex)
    c4,l4=asm(['pad:','bnez a0, pd','lui at, 0x8005','j %d'%lmx['padx'],'sw a2, -0x410(at)','pd:','j %d'%RM,'nop'],CAVE_PAD)
    assert c4[-1][0]<0x8004f9a0
    # Square held in the air: rotations x4 (the old 'mdr' tail of md lives here)
    csq,_=asm(['lui t7, 0x8005','lw t7, -0x410(t7)','nop','andi t7, t7, 0x80','beqz t7, h1','nop',f'sll v1, v1, {SQ_SH}',
               'h1:','sll at, t5, 2','addu at, at, s0','lw v0, 0x7a4(at)','nop','jr ra','addu v0, v0, v1'],0x8004f9a0)
    assert c4[-1][0]<0x8004f9a0 and csq[-1][0]<0x8004f9e0
    P+=[('/SCES_009.92',a,0,w) for a,w in csq]
    P+=[('/SCES_009.92',0x8001b594,0x08006d68,(2<<26)|((CAVE_PAD>>2)&0x3ffffff))]
    P+=[('/SCES_009.92',a,0,w) for a,w in c4]
    # --- Boarder Cross (SBC2): ramming. The game's racer-vs-racer collision (0x8005ff70 -> response 0x80073714
    # for each racer of a touching pair) could knock both down. Now the faster of the two (movement vectors
    # the game passes in a1/a2) wins: the player gets no response when he is the faster one, and a CPU rammed by
    # a faster player always goes down (game's own stumble countdown +0x740, as after a hard wall hit).
    RESP=0x80073714
    KC=['kc:','addiu sp, sp, -0x20','sw ra, 0x1c(sp)','sw a0, 0x18(sp)',
        'lh t0, 0(a1)','lh t1, 4(a1)','mult t0, t0','mflo t0','nop','nop','mult t1, t1','mflo t1','addu t2, t0, t1',
        'lh t0, 0(a2)','lh t1, 4(a2)','nop','nop','mult t0, t0','mflo t0','nop','nop','mult t1, t1','mflo t1','addu t3, t0, t1',
        'bnez s5, kc2','slt t4, t2, t3',
        'beqz t4, kc9','nop',f'jal {RESP}','nop','j kc9','nop',
        'kc2:','bnez s1, kcl','nop','beqz t4, kcl','nop',f'jal {RESP}','nop',
        'lw t0, 0x18(sp)','nop','lw t1, 0x738(t0)','lh t2, 0x740(t0)','nop','or t1, t1, t2','bnez t1, kc9',f'addiu t1, zero, {KD_CD}','sh t1, 0x740(t0)','j kc9','nop',
        'kcl:',f'jal {RESP}','nop',
        'kc9:','lw ra, 0x1c(sp)','addiu sp, sp, 0x20','jr ra','nop']
    ckd,lkd=asm(KC,0x80028bf4); assert ckd[-1][0]<0x80028d3c,hex(ckd[-1][0])
    for a_,w_ in ckd: P.append(('/SCES_009.92',a_,struct.unpack_from('<I',_ex,a_-0x8000f800)[0],w_))
    P.append(('/SBC2.BIN',0x8005ff70,0x0c01cdc5,(3<<26)|((lkd['kc']>>2)&0x3ffffff)))
    # --- Big Air Master: Exit of the pause menu ends the session as a finish (exit code 5: "YOUR GRADE IS ...", then
    #     the TRICK MASTER ranking) instead of leaving without results (3). Mode 6 only (Master); code in the dead
    #     func_8002934C of the exe. The pause handler stores v0 at 0x8005CCC8 with `at` already set: kept.
    cbx,lbx_=asm(['bx:','lui t0, 0x8005','lw t0, 0x7420(t0)','addiu t1, zero, 6','bne t0, t1, bx9','addiu v0, zero, 3','addiu v0, zero, 5',
                 'bx9:','jr ra','nop'],0x8002934c)
    assert cbx[-1][0]<0x800293f8
    for a_,w_ in cbx: P.append(('/SCES_009.92',a_,struct.unpack_from('<I',_ex,a_-0x8000f800)[0],w_))
    P.append(('/TM.BIN',0x8005ccc0,0x24020003,(3<<26)|((lbx_['bx']>>2)&0x3ffffff)))
    # --- Big Air Master: always show the trick command box (was hidden from level 19)
    P+=[('/TM.BIN',0x80075758,0x10400009,0)]
    # Big Air Master: keys always shown (the game hides them on each new trick until a first failure: flag 0x8009cf2c)
    P+=[('/TM.BIN',0x80075738,0x8463cf2c,0x2403ffff)]          # lh v1,cf2c -> li v1,-1
    # ...and a "next tricks" column (Tetris style): a wrapper around the trick box (0x800756dc) draws the current
    # trick, then the following ones; the primitives each extra call links into the HUD ordering-table slot are
    # shifted afterwards (dx, dy) so they stack up on the right of the screen.
    TL=0x800953b0; NX=TL_N; Y0=TL_Y0; DY=TL_DY; X0=TL_X0; TW=0x800951c0; TM2=0x80094f18; RX=TL_RX
    SB=TM2+0xd0-8; SH=(SB+0x8000)>>16; SL=SB-(SH<<16)
    LBL=[b'NEXT',b' 2nd',b' 3rd',b' 4th',b' 5th',b' 6th',b' 7th']
    tl=['tl:','addiu sp, sp, -0x48','sw ra, 0x44(sp)','sw s0, 0x20(sp)','sw s1, 0x24(sp)','sw s2, 0x28(sp)','sw s3, 0x2c(sp)',
        'sw s4, 0x30(sp)','sw s5, 0x34(sp)','sw s6, 0x38(sp)',
        'move s0, a0','move s1, a1',
        'lw t0, 4(s0)','lui s2, 0x800a','addiu s5, t0, 0xc',
        'lw t0, 0(s5)','move s6, zero','sw t0, 0x18(sp)',
        'jal 0x800756dc','lh s3, -0x30ec(s2)',
        'jal twalk',f'addiu t1, zero, {X0}',                 # current trick: shifted left a bit
        'lh s4, -0x30e0(s2)','sw s3, 0x3c(sp)','sw s4, 0x40(sp)',
        'tlp:','addiu s4, s4, 1','slti t0, s4, 10','bnez t0, tck','nop',
        'tnl:','addiu s3, s3, 1','move s4, zero',
        'tck:','slti t0, s3, 19','beqz t0, tdn',
        'sll t0, s3, 4','subu t0, t0, s3','sll t0, t0, 3',
        'sll t1, s4, 1','addu t1, t1, s4','sll t1, t1, 2','addu t0, t0, t1','lui t1, 0x8009','addu t0, t0, t1',
        'lw t1, 0x6424(t0)','lw t2, 0x6428(t0)','addiu t1, t1, 1','or t1, t1, t2','beqz t1, tnl','nop',
        'sh s3, -0x30ec(s2)','sh s4, -0x30e0(s2)',
        'lw t0, 0(s5)','move a0, s0','sw t0, 0x18(sp)','jal 0x800756dc','move a1, s1',
        'jal tmeas','addiu s6, s6, 1',
        f'addiu t1, zero, {RX}','subu t1, t1, v0',          # dx: right edge flush with RX
        'addu v1, v1, t1','sw v1, 0x1c(sp)',                 # left edge after the shift
        f'addiu t2, zero, {DY}','mult s6, t2','mflo t2',f'addiu t2, t2, {Y0}','sw t2, 0x14(sp)','sll t2, t2, 16',
        'jal twalk','addu t1, t1, t2',
        # rank label (NEXT, 2nd, ...) left of the entry's name line, with the game's font print (0x8008fff4)
        'lw t2, 0x14(sp)','lw a3, 0x1c(sp)',f'addiu t2, t2, {TL_LY}','sw t2, 0x10(sp)','sw zero, 0x14(sp)',
        'addiu a3, a3, -36','move a0, s5','lui a1, 0x800a','lw a1, -0x2084(a1)',
        'sll a2, s6, 3',f'lui t0, {SH:#x}','addu a2, a2, t0',
        'jal 0x8008fff4',f'addiu a2, a2, {SL}',
        f'slti t0, s6, {NX}','bnez t0, tlp','nop',
        'tdn:','lw s3, 0x3c(sp)','lw s4, 0x40(sp)','sh s3, -0x30ec(s2)','sh s4, -0x30e0(s2)',
        'lw ra, 0x44(sp)','lw s0, 0x20(sp)','lw s1, 0x24(sp)','lw s2, 0x28(sp)','lw s3, 0x2c(sp)','lw s4, 0x30(sp)','lw s5, 0x34(sp)','lw s6, 0x38(sp)',
        'jr ra','addiu sp, sp, 0x48']
    tw=['twalk:','lui t9, 0x8000','lw t2, 0x18(sp)','move t5, s5','sll t2, t2, 8',
        # twalk: add t1 (packed y<<16|x) to every vertex of the primitives linked into OT slot s5 since head 0x18(sp)
        'tnp:','lw t4, 0(t5)','nop','sll t4, t4, 8','beq t4, t2, tnx','srl t5, t4, 8','or t5, t5, t9',
        'lbu t6, 7(t5)','addiu t8, t5, 8','addiu t7, t6, -0x60','sltiu t7, t7, 0x20','beqz t7, tpl','addiu t7, t6, -0x20',
        'lw a0, 0(t8)','nop','addu a0, a0, t1','beq zero, zero, tnp','sw a0, 0(t8)',
        'tpl:','sltiu t7, t7, 0x20','beqz t7, tnp','andi t7, t6, 8',
        'sltu t7, zero, t7','addiu t7, t7, 3','move t0, zero',
        'tpv:','beqz t0, tp1','andi a0, t6, 0x10','srl a0, a0, 2','addu t8, t8, a0',
        'tp1:','lw a0, 0(t8)','addiu t0, t0, 1','addu a0, a0, t1','sw a0, 0(t8)','andi a0, t6, 4','addu t8, t8, a0',
        'bne t0, t7, tpv','addiu t8, t8, 4','beq zero, zero, tnp','nop',
        'tnx:','jr ra','nop']
    tms=[# tmeas: v0 = right edge, v1 = left edge of the sprites/rects (+ flat quads) linked since head 0x18(sp)
        'tmeas:','lui t9, 0x8000','lw t2, 0x18(sp)','move t5, s5','sll t2, t2, 8','addiu v0, zero, -1000','addiu v1, zero, 1000',
        'tmn:','lw t4, 0(t5)','nop','sll t4, t4, 8','beq t4, t2, tmx','srl t5, t4, 8','or t5, t5, t9',
        'lbu t6, 7(t5)','lbu t7, 3(t5)','addiu t8, t6, -0x60','sltiu t8, t8, 0x20','beqz t8, tmq','lh t3, 8(t5)',
        'sll t7, t7, 2','addu t7, t7, t5','lh t8, 0(t7)','slt t7, t3, v1','beqz t7, tm1','addu t8, t8, t3','move v1, t3',
        'tm1:','slt t7, v0, t8','beqz t7, tmn','nop','beq zero, zero, tmn','move v0, t8',
        'tmq:','addiu t8, t6, -0x28','sltiu t8, t8, 4','beqz t8, tmn','lh t8, 12(t5)','nop','slt t7, v0, t8','beqz t7, tmn','nop',
        'beq zero, zero, tmn','move v0, t8','tmx:','jr ra','nop']
    cw,lw_=asm(tw,TW); assert cw[-1][0]<0x800952dc,hex(cw[-1][0])
    cm,lm=asm(tms,TM2); assert cm[-1][0]<TM2+0xd0,hex(cm[-1][0]); lw_['tmeas']=lm['tmeas']; cw+=cm
    ct,lt=asm(tl,TL,syms={'twalk':lw_['twalk'],'tmeas':lw_['tmeas']}); assert ct[-1][0]<TL+0x1e8,hex(ct[-1][0])
    P+=[('/TM.BIN',a,0,w) for a,w in ct+cw]
    for i,t in enumerate(LBL):
        bb=(t+b'\0'*8)[:8]
        P+=[('/TM.BIN',TM2+0xd0+8*i+4*j,0,int.from_bytes(bb[4*j:4*j+4],'little')) for j in range(2)]
    P+=[('/TM.BIN',0x80074cfc,0x0c01d5b7,(3<<26)|((TL>>2)&0x3ffffff))]
    # --- air control (Tony Hawk style): in flight, holding the rotation's direction speeds it up x1.5,
    #     the opposite direction slows it x0.5. Spins: LEFT/RIGHT, flips: UP/DOWN. pad copy at 0x8004fbf0
    AIR=0x8004fa40
    import struct as _st
    # md: modulate a rotation delta (v1) with the d-pad: same direction x1.5, opposite x0.5.
    #     t5 = 0 spin (LEFT/RIGHT, acc 0x7a4) / 1 flip (UP/DOWN shifted onto the same bits, acc 0x7a8).
    #     returns v1 = modulated delta, v0 = acc + v1.   (t5-t8 are unused by the host functions)
    md=['mds:','move t5, zero',
        'md:','beqz v1, mdr','lui at, 0x8005','lw t6, -0x410(at)','nop','sllv t6, t6, t5',
        'bgez v1, mp','andi t7, t6, 0x2000','andi t7, t6, 0x8000','andi t6, t6, 0x2000','beq zero, zero, mc','nop',
        'mp:','andi t6, t6, 0x8000',
        'mc:','bnez t7, mf','sra at, v1, 1','beqz t6, mdr','nop','beq zero, zero, mdr','move v1, at',
        'mf:','addu v1, v1, at',
        'mdr:','j 0x8004f9a0','nop','nop','nop','nop','nop']
    # ax: Tony Hawk style rotation start. Hooked on the game's "charged spin" (rider+0x748, t5=0) and
    #     "charged flip" (rider+0x744, t5=1) reads: with no charge, LEFT/RIGHT (UP/DOWN) feed a charge
    #     of +/-K while held. Grab buttons (L/R, circle, square) block it. Also marks "in the air" for
    #     the pad remap (counter at 0x8004fbec). Returns the charge in v0 and a0.
    AK=AIR_K; FK=FLIP_K
    ax=['ax:','lui at, 0x8005','addiu t8, zero, 4','sw t8, -0x414(at)','lw t6, -0x410(at)','sll at, t5, 2','subu at, s0, at',
        'lw v0, 0x748(at)','andi t7, t6, 0xf','bnez t7, rt','sllv t6, t6, t5',
        'beqz t5, k0',f'addiu t7, zero, {AK}',f'addiu t7, zero, {FK}',
        'k0:','beq v0, t7, own','subu t8, zero, t7','beq v0, t8, own','nop','addiu v1, v0, 7','sltiu v1, v1, 15','beqz v1, rt',
        'own:','andi v0, t6, 0x2000','bnez v0, st','move v0, t7','andi v0, t6, 0x8000','bnez v0, st','move v0, t8','move v0, zero',
        'st:','sw v0, 0x748(at)',
        'rt:','lw v0, 0x748(at)','lw a0, 0x748(at)','jr ra','nop']
    # rm: (trick modes, in the air via the ax marker)
    #     UP/DOWN already held at take-off are ignored for flips until released (latch 0x8004fa0c).
    rm=['rm:','bnez a0, 0x8004fba0','lui at, 0x8005','lw t0, -0x414(at)','lw t1, -0x5f4(at)','andi t2, a2, 0x5000',
        'bnez t0, rair','and t1, t1, t2',
        'beq zero, zero, 0x8004fba0','sw t2, -0x5f4(at)',               # ground: latch = held
        'rair:','andi t3, a2, 0xf','beqz t3, r1','addiu t0, t0, -1','or t1, t1, t2',   # grab held: latch up/down
        'r1:','sw t0, -0x414(at)','sw t1, -0x5f4(at)',
        'lw t3, -0x604(at)','nor t4, t1, zero','and t4, t4, t2','bnez t4, rf','addiu t3, t3, 1','move t3, zero',
        'rf:',f'slti t4, t3, {FLIP_DELAY}','beqz t4, rm2','sw t3, -0x604(at)','or t1, t1, t2',  # fresh press: wait a bit
        'rm2:','lw t2, -0x410(at)','nor t1, t1, zero','and t2, t2, t1','sw t2, -0x410(at)']   # falls through to inj (0x8004fba0)
    # hm: MODE_SEL, hard mode chosen (L1+X): if R1 is held too, also switch mirror mode on
    hm=['hm:','lui v0, 0x8008','lhu v0, 0x32ba(v0)','nop','andi v0, v0, 8','beqz v0, 0x8005b858','addiu v0, zero, 1',
        'lui at, 0x8005','j 0x8005b858','sh v0, 0x742e(at)']
    ca,la=asm(md+ax+rm,AIR)
    assert ca[-1][0]<0x8004fb9c
    ch,lh_=asm(hm,0x8004f878); assert ch[-1][0]<0x8004f8a0
    P+=[('/SCES_009.92',a_,0,w) for a_,w in ch]; la['hm']=lh_['hm']
    P+=[('/MODE_SEL.BIN',0x8005b81c,0x08016e16,(2<<26)|((la['hm']>>2)&0x3ffffff))]
    # TV hint of the mode select screen: its 3rd slot (GHOST L2+X, never shown) is shown like HARD on Competition,
    # with the label 'H+M L1+R1+X' (HM_LABEL, drawn in /TITLE/MODE_SEL.FBD by apply())
    P+=[('/MODE_SEL.BIN',0x800647dc,0x08019208,0x080191f9)]
    # in-game progress page (progress.py): SELECT held on the mode select screen. MODE_SEL grows by the page's code
    # (rest of its last sector): its heap now starts after it (exe table of overlay heap starts, entry 1)
    import progress as _pg
    _o,_b,_h=_pg.block()
    P+=[('/MODE_SEL.BIN',_pg.HOOK,_pg.HOOK_OLD,_h),('/SCES_009.92',0x800100b4,0x800832c8,_pg.LIMIT)]
    # Free Style lift (lift.py): the finish counts as usual, no celebration / replay, straight to ranking -> RETRY
    import lift as _lf
    P+=_lf.patches()
    # Competition: skip the qualifying stage (skipq.py): straight to the Boarder Cross, 4th start gap
    import skipq as _sq
    P+=_sq.patches(_ex,open(os.path.join(FS,'SBC1.BIN'),'rb').read())
    P+=[('/SCES_009.92',a,0,w) for a,w in ca]
    assert la['rm']==RM,hex(la['rm'])
    # mdf: flip wrapper (separate small cave): effective delta = a0 ? -s7 : s7, modulated, written back to s7
    cw,lw_=asm(['mdf:','move t8, ra','beqz a0, f1','move v1, s7','subu v1, zero, s7',
                'f1:','jal %d'%la['md'],'addiu t5, zero, 1','move s7, v1','beqz a0, f2','move ra, t8','subu s7, zero, v1',
                'f2:','jr ra','nop'],0x8004f8cc)
    assert cw[-1][0]<0x8004f900
    P+=[('/SCES_009.92',a,0,w) for a,w in cw]
    J=lambda t:(3<<26)|((t>>2)&0x3ffffff)
    spin_sites={'/BP.BIN':(0x80066298,'s2'),'/COMB.BIN':(0x800672bc,'s2'),'/FREE.BIN':(0x80068150,'s2'),'/SBC2.BIN':(0x80068334,'s2'),
                '/TM.BIN':(0x8006632c,'s2'),'/VS.BIN':(0x800675b8,'s2'),'/OMT.BIN':(0x800663a0,'s3'),'/SBC1.BIN':(0x80066638,'s3')}
    for f,(a,r) in spin_sites.items():
        rr={'s2':18,'s3':19}[r]; addu=(2<<21)|(rr<<16)|(2<<11)|0x21
        P+=[(f,a,0x8e0207a4,J(la['mds'])),(f,a+4,0,(rr<<21)|(3<<11)|0x21),(f,a+8,addu,(3<<21)|(rr<<11)|0x21)]
    flip_sites={'/BP.BIN':0x80066380,'/COMB.BIN':0x800673a4,'/FREE.BIN':0x80068238,'/OMT.BIN':0x80066488,'/SBC1.BIN':0x80066720,
                '/SBC2.BIN':0x8006841c,'/TM.BIN':0x80066414,'/VS.BIN':0x800676a0}
    for f,a in flip_sites.items():
        P+=[(f,a,0x8e0207a8,J(lw_['mdf'])),(f,a+4,0x10800003,0),(f,a+8,0,0),(f,a+0xc,None,0),(f,a+0x10,0x00571023,0),(f,a+0x14,0x00571021,0)]
    T5_0=(9<<26)|(13<<16); T5_1=T5_0|1     # addiu t5, zero, 0/1
    for f in ['/SBC1.BIN','/TM.BIN','/OMT.BIN','/BP.BIN']:
        d=open(FS+f,'rb').read(); W=lambda i:_st.unpack('<I',d[i:i+4])[0]
        hs=[i for i in range(0,len(d)-16,4) if (W(i)&0xfc1fffff)==0x8c020014 and W(i+4)==0 and (W(i+8)>>16)==0x1040 and (W(i+12)&0xffff07ff)==0x00400021]
        hf=[i for i in range(0,len(d)-16,4) if (W(i)&0xfc1fffff)==0x8c040010 and W(i+4)==0 and (W(i+8)>>16)==0x1080 and W(i+12)==0x3c0351eb]
        assert len(hs)==1 and len(hf)==1,(f,hs,hf)
        P+=[(f,0x8005aea8+hs[0],W(hs[0]),J(la['ax'])),(f,0x8005aea8+hs[0]+4,0,T5_0),
            (f,0x8005aea8+hf[0],W(hf[0]),J(la['ax'])),(f,0x8005aea8+hf[0]+4,0,T5_1)]
    # --- SBC2 (Boarder Cross): the player's free-ride texture is uploaded at x=512+32*char. For chars>=4
    #     (Boss/Gray/Snow) that lands on the sky texture; their race models use the CPU image -> upload the CLUT only.
    FIX=0x8004f820
    cf,lf=asm(['fx:','slti at, s6, 4','bnez at, go','nop','sh zero, 0x10(a0)','go:','j 0x8001f0b4','nop'],FIX)   # image width 0 -> CLUT only
    assert cf[-1][0]<0x8004f840
    P+=[('/SCES_009.92',a,0,w) for a,w in cf]
    P+=[('/SBC2.BIN',0x80064d70,0x0c007c2d,jal(FIX))]
    # --- results name plates: player Gray -> rider 5 shows GRAY, player Snowman -> rider 6 shows SNOWMAN
    for f,join,cave,e5 in (('/SBC1.BIN',0x800832dc,0x8008d8c8,0x5a),('/SBC2.BIN',0x800847ac,0x800902a8,0x62)):
        uvg=PL_GRAY_U|(PL_V<<8); uvs=PL_SNOW_U|(PL_V<<8)
        cn,ln=asm(['gc:','lui at, 0x8005','lh at, 0x7408(at)','addiu v0, zero, 5','bne at, v0, g6','addiu v0, zero, 6',
                   f'addiu at, zero, {uvg-0x10000}',f'sh at, {e5}(sp)',f'addiu at, zero, {PL_W["GRAY"]}','j gb',f'sb at, {e5+2}(sp)',
                   'g6:','bne at, v0, gb','nop',f'addiu at, zero, {uvs-0x10000}',f'sh at, {e5+10}(sp)',f'addiu at, zero, {PL_W["SNOWMAN"]}',f'sb at, {e5+12}(sp)',
                   'gb:','lui a1, 0x8009',f'j {join+4}','nop'],cave)
        P+=[(f,a,0,w) for a,w in cn]
        P+=[(f,join,0x3c058009,(2<<26)|((cave>>2)&0x3ffffff))]
    # --- grab switch helper (pad cave tail -> inj): changing d-pad direction while holding R1/R2
    import inj as _inj
    ci,ia=_inj.inj(); assert ia==0x8004fba0
    P+=[('/SCES_009.92',a,0,w) for a,w in ci]
    # --- "X to Y" combos: the 2nd grab is also accepted during the return phase of the 1st (c48==1)
    #     -> window ~16 -> ~32 frames. Registering it resets c48 so the game switches to slot 2.
    import struct as _st
    for f in ['/SBC1.BIN','/TM.BIN','/OMT.BIN','/BP.BIN']:
        d=open(FS+f,'rb').read(); W=lambda i:_st.unpack('<I',d[i:i+4])[0]
        hits=[i for i in range(0,len(d)-20,4) if W(i)==0x86020c48 and W(i+4)==0 and (W(i+8)>>16)==0x1440 and W(i+12)==0 and W(i+16)==0x84820c3c]
        assert len(hits)==1,f
        i=hits[0]; a=0x8005aea8+i+8; t=a+4+((W(i+8)&0xffff)<<2)
        c=[k for k in range(i,i+0x180,4) if (W(k)&0xffe0ffff)==0xa6000c3e][0]
        assert W(c-4)==0
        P+=[(f,a,W(i+8),0x28420002),(f,a+4,0,0x10400000|(((t-a-8)>>2)&0xffff)),(f,0x8005aea8+c-4,0,0xa6000c48)]
    # --- INIT defaults: everything unlocked (new save)
    P+=[('/INIT.BIN',0x8005b1d4,0x24020003,0x2402000a),   # tracks
        ('/INIT.BIN',0x8005b1e0,0x2402000f,0x2402007f),   # boarders
        ('/INIT.BIN',0x8005b258,0x3c018005,0x240300ff),   # v1=7 (at still 0x80050000)
        ('/INIT.BIN',0x8005b25c,0xa4207442,0xa4237442),   # boards
        ('/INIT.BIN',0x8005b260,0x3c018005,0x24030001),   # v1=1
        ('/INIT.BIN',0x8005b264,0xa4207444,0xa4237444),   # mirror mode
        ('/INIT.BIN',0x8005b274,0xa420744a,0xa422744a),   # awards
        ('/INIT.BIN',0x8005b27c,0xa420744c,0xa422744c),
        ('/INIT.BIN',0x8005b250,0x3c018005,0x2403000a),   # v1=10 (at still 0x80050000)
        ('/INIT.BIN',0x8005b254,0xa420743e,0xa423743e),   # tracks available in mirror mode
        ('/INIT.BIN',0x8005b26c,0xa4207446,0xa4237446)]   # hard mode unlocked (v1=1)
    # --- all boarders selectable even with an old memory-card save
    P+=[('/MAIN_SEL.BIN',0x80063ea8,0x95030000,0x2403007f)]
    # special boards also in competition (the game hid them there by clearing 0x7442 on entry)
    P+=[('/MAIN_SEL.BIN',0x8005b0c4,0xa4207442,0)]
    # Cindy/Irin hidden outfits = jacket choices 4-6 on the WEAR screen (b314 = 3..5). On validation the
    # jacket goes back to 0..2 and the game's own 'alternative outfit' flag 0x742a is set. The caves reuse the
    # game's old 'locked outfit' menu paths (flag + free mode), which are disabled below.
    R1=['wlim:','lhu t1, 0(s3)','addiu t0, zero, 3','bne v1, s6, w1','addiu t1, t1, -2','sltiu t1, t1, 2','beqz t1, w1','nop','addiu t0, zero, 6',
        'w1:','jr ra','slt v0, v0, t0',
        'wprv:','lh v0, 0(s4)','nop','slti t0, v0, 3','bnez t0, w5','nop','addiu v0, v0, -3','w5:','jr ra','nop']
    R2=['wwrap:','lhu t1, 0(s3)','addiu v0, zero, 2','bne v1, s6, w2','addiu t1, t1, -2','sltiu t1, t1, 2','beqz t1, w2','nop','addiu v0, zero, 5',
        'w2:','j 0x80062184','sh v0, 0(v1)',
        'wcom:','sltiu t0, v1, 3','xori t0, t0, 1','beqz t0, w3','sltiu t1, a2, 3','addiu v1, v1, -3',
        'w3:','xori t1, t1, 1','beqz t1, w4','or t0, t0, t1','addiu a2, a2, -3',
        'w4:','sh t0, 0x742a(at)','j 0x800605bc','sh v1, 0x740c(at)']
    c1,l1=asm(R1,0x80062034); assert c1[-1][0]<0x80062088
    c2_,l2_=asm(R2,0x80062104); assert c2_[-1][0]<0x80062160
    lw2=dict(l1); lw2.update(l2_)
    _ms2=open(os.path.join(FS,'MAIN_SEL.BIN'),'rb').read()
    for a_,w_ in c1+c2_: P.append(('/MAIN_SEL.BIN',a_,struct.unpack_from('<I',_ms2,a_-0x8005aea8)[0],w_))
    J=lambda op,t:(op<<26)|((t>>2)&0x3ffffff)
    import wearprev as _wp
    _wb,_wl=_wp.block()
    P+=[('/MAIN_SEL.BIN',0x8006209c,0x00021400,J(3,lw2['wlim'])),('/MAIN_SEL.BIN',0x800620a0,0x00021403,0),('/MAIN_SEL.BIN',0x800620a4,0x28420003,0),
        ('/MAIN_SEL.BIN',0x80062180,0xa4620000,J(2,lw2['wwrap'])),
        ('/MAIN_SEL.BIN',0x800605b4,0xa423740c,J(2,lw2['wcom'])),
        ('/MAIN_SEL.BIN',0x800640ec,0x86820000,J(3,_wl['wprv0'])),('/MAIN_SEL.BIN',0x80064210,0x8fbf182c,J(2,_wl['wend'])),
        ('/SCES_009.92',0x8001003c,0x8007d18c,_wp.BASE+len(_wb)),('/SCES_009.92',0x800100b8,0x8007d18c,_wp.BASE+len(_wb)),('/MAIN_SEL.BIN',0x80064184,0x86820000,J(3,lw2['wprv'])),
        # the game's old 'locked outfit' menu paths (flag + free mode) are no longer wanted
        ('/MAIN_SEL.BIN',0x80062004,0x10400020,0x10000020),('/MAIN_SEL.BIN',0x800620d4,0x10400022,0x10000022)]
    # special boards always offered (a memory-card save can bring 0x7442 back to 0): lhu rt,0x7442 -> ori rt,zero,0xffff
    import struct as _st
    _ms=open(os.path.join(FS,'MAIN_SEL.BIN'),'rb').read()
    for a in (0x80069d00,0x80069d84,0x80069f74,0x8006a000,0x8006a238,0x8006a2cc,0x8006a338,0x8006b4f0,0x8006bca0,0x8006c1cc,0x8006c2b4,0x8006c5c8,0x8006c910):
        w=_st.unpack_from('<I',_ms,a-0x8005aea8)[0]; assert w&0xfc00ffff==0x94007442
        P.append(('/MAIN_SEL.BIN',a,w,0x3400ffff|(w&0x001f0000)))
    # Cindy/Irin hidden outfits (SELECT) also in competition: the competition rider loader (exe 0x8001d140)
    # always loaded the normal texture; free mode loads 0xde/0xe1 + wear when 0x742a is set.
    A=['lui t0, 0x8005','lh t1, 0x742a(t0)','lh t2, 0x7408(t0)','beqz t1, 0x8004f9e8','lw a0, 0xc0(sp)','addiu t2, t2, -2','j 0x8004f96c','sltiu at, t2, 2']
    Bk=['beqz at, 0x8004f9e8','sll t1, t2, 1','addu t1, t1, t2','j 0x8004f9e0','lh t3, 0x740c(t0)']
    Ck=['addiu a0, t1, 0xde','addu a0, a0, t3','jr ra','nop']
    for code,org,lim in ((A,0x8004f920,0x8004f940),(Bk,0x8004f96c,0x8004f980),(Ck,0x8004f9e0,0x8004f9f0)):
        cc,_=asm(code,org); assert cc[-1][0]<lim
        P+=[('/SCES_009.92',a,0,w) for a,w in cc]
    P+=[('/SCES_009.92',0x8001d140,0x8fa400c0,(3<<26)|((0x8004f920>>2)&0x3ffffff))]
    # races (SBC2): only 4 rider voice banks (SBC2ND0-3); Boss/Gray/Snowman (slots 4-6) read past the table
    # and loaded the SE bank as voice bank (no announcer/voices, looping noises) -> use Yaggi/Jin banks
    BFE=0x80090350; BTB=0x80090358; BIDX=(BFE-0x800583e8)//8
    cb,lb=asm(['bsnd:','lui t0, 0x8004','addiu t1, zero, 0x38','lui t2, 0x8004','ori t2, t2, 0x69c4','addiu at, zero, 4','bne v0, at, bs0','nop',
               f'addiu t1, zero, {BIDX}',f'lui t2, {BTB>>16:#x}',f'ori t2, t2, {BTB&0xffff:#x}',
               'bs0:','sw t1, 0x7e3c(t0)','sw t2, 0x7e40(t0)',
               'slti at, v0, 4','bnez at, bs1','nop','andi v0, v0, 1','bs1:','sll v0, v0, 1','jr ra','addu v0, v0, a0'],0x80090300)
    assert cb[-1][0]<BFE and 0<BIDX<0x8000
    P+=[('/SBC2.BIN',a,0,w) for a,w in cb]
    P+=[('/SBC2.BIN',0x80066cb4,0x00021040,(3<<26)|((0x80090300>>2)&0x3ffffff)),('/SBC2.BIN',0x80066cb8,0x00441021,0)]
    # --- main exe: model index 0x9c+char
    P+=[('/SCES_009.92',0x8001d078,0x8c440078,0x2684009c)]
    # --- texture index for chars>=4
    c,l=asm(['tex:','slti at, s4, 5','bnez at, td','addiu t4, s4, -4','sll t5, t4, 3','subu t5, t5, t4','subu v1, v1, t5','td:','jr ra','sw v1, 0xc0(sp)'],CAVE_TEX)
    P+=[('/SCES_009.92',0x8001cefc,0x00651821,jal(CAVE_TEX)),('/SCES_009.92',0x8001cf00,0xafa300c0,0x00651821)]
    P+=[('/SCES_009.92',a,0,w) for a,w in c]
    # --- boarder-cross bundle for chars>=4
    i5=idx_for(LOCTBL)
    c,l=asm(['pl:','slti at, s4, 4','beqz at, sp_','sll v0, s4, 2','addu v0, sp, v0','jr ra','lw a0, 0xa0(v0)',
             'sp_:','addiu at, zero, 4','bne s4, at, gs','nop','jr ra','addiu a0, zero, 0x8c',   # Boss: PLAYER0.DAT
             'gs:','addiu a0, s4, %d'%(i5-5),'jr ra','nop'],CAVE_PL)
    # ENEMY1 (CPU textures + CLUTs) variant for Gray/Snow
    c2,l2=asm(['en:','addiu a0, zero, 0x90','addiu at, zero, 5','bne s4, at, e6','nop','addiu a0, zero, %d'%idx_for(LOCTBL+16),
               'e6:','addiu at, zero, 6','bne s4, at, ed','nop','addiu a0, zero, %d'%idx_for(LOCTBL+24),'ed:','jr ra','nop'],CAVE_EN)
    P+=[('/SCES_009.92',0x8001cfe0,0x24040090,jal(CAVE_EN))]
    # --- SBC2 (Boarder Cross): Boss as player (rider 4) uses Boss's model, bundle slot 7
    c3,l3=asm(['sl:','addiu at, zero, 0x14','bne a2, at, go','lui t0, 0x8005','lh t0, 0x7408(t0)','addiu at, zero, 4','bne t0, at, go','nop','addiu a2, a2, 12',
               'go:','addu a2, a2, v0','jr ra','lw a2, 0(a2)'],CAVE_SLOT)
    P+=[('/SBC2.BIN',0x800666ec,0x00c23021,jal(CAVE_SLOT)),('/SBC2.BIN',0x800666f0,0x8cc60000,0)]
    P+=[('/SCES_009.92',a,0,w) for a,w in c3]
    P+=[('/SCES_009.92',a,0,w) for a,w in c2]
    P+=[('/SCES_009.92',0x8001d104,0x00141080,jal(CAVE_PL)),('/SCES_009.92',0x8001d108,0x03a21021,0),('/SCES_009.92',0x8001d10c,0x8c4400a0,0)]
    P+=[('/SCES_009.92',a,0,w) for a,w in c]
    return P
def write_blob(im,lba,blob):
    blob=blob+bytes((-len(blob))%2048); n=len(blob)//2048
    for k in range(n):
        im.write_user(lba+k,0,blob[k*2048:(k+1)*2048],subhdr=bytes([0,0,0x89 if k==n-1 else 0x08,0]))
    return n

SND_SETS=None
def boss_course_bank():
    """SBC2ND0 (Yaggi's course voice bank, 48 samples) with Yaggi's own voice clips swapped for Boss's
    (Big Air bank SBC1ST4 + free-ride bank FR1P4A). Returns (vb bytes, offsets[49])."""
    import json
    T={int(k):v for k,v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'sndsets.json'))).items()}
    D=FS+'/SOUND/'
    def smp(s,n):
        d=open(D+n+'.VB','rb').read(); o=T[s][1]; return [d[o[i]:o[i+1]] for i in range(len(o)-1)]
    nd0=smp(0x23,'SBC/SBC2ND0'); st0=smp(0x1c,'SBC/SBC1ST0'); st4=smp(0x20,'SBC/SBC1ST4')
    fr0=smp(0x5,'FR/FR1P0A'); fr4=smp(0xd,'FR/FR1P4A')
    M={34:33,35:34,36:35,37:36,39:37,40:38,41:39,42:40,43:41,45:43,46:44,47:45}
    new=list(nd0)
    for i,j in M.items(): assert nd0[i]==st0[j]; new[i]=st4[j]
    assert nd0[38]==fr0[28]; new[38]=fr4[28]
    offs=[0]
    for x in new: offs.append(offs[-1]+len(x))
    return b''.join(new),offs
def layout(im,blobs):
    F=im.files
    vs_hole=F['/DATA/CRS/VS/VS_CS1.DAT'][0]            # 8435, 161 sectors (dup of CRS_CS1)
    tail=65645                                          # 150 free sectors at end of data track
    ed=F['/ENDING/S_CHR/ED_CHRCG.DAT'][0]               # 17606..17658 unused file
    etcdir=F['/ETC'][0]; loaddir=F['/LOAD'][0]
    assert ed+53==etcdir
    small=['/ETC/CB2T1E.FBD','/ETC/CB2T2E.FBD','/ETC/NENTRY.NEP','/ETC/PRESENTS.DAT','/ETC/SPBRD.TMD','/ETC/UEPLOGO.DAT']
    data={p:im.read_file(p) for p in small}
    import title as _tt
    for p in _tt.FILES: data[p]=_tt.draw(data[p])   # title screen: stylised REMIX (title.py)
    im.set_record('/DATA/CRS/VS/VS_CS1.DAT',lba=F['/DATA/CRS/CRS_CS1.DAT'][0])
    pos={}
    def put(p,a,lim):
        im.set_record(p,lba=a); a+=write_blob(im,a,data[p]); assert a<=lim,(p,a,lim); return a
    def blob(k,b,a,lim):
        pos[k]=a; a+=write_blob(im,a,b); assert a<=lim,(k,a,lim); return a
    a=vs_hole; a=put('/ETC/CB2T2E.FBD',a,vs_hole+161); a=blob('eg',blobs[2],a,vs_hole+161); a=blob('es',blobs[3],a,vs_hole+161)
    a=ed; a=put('/ETC/CB2T1E.FBD',a,etcdir); a=put('/ETC/NENTRY.NEP',a,etcdir)
    a=etcdir+1
    for p in ['/ETC/PRESENTS.DAT','/ETC/SPBRD.TMD','/ETC/UEPLOGO.DAT']: a=put(p,a,loaddir)
    a=blob('snow',blobs[1],a,loaddir)
    a=blob('gray',blobs[0],tail,65795)
    return pos
# 'H+M L1+R1+X' label for the TV hint: glyphs of the HARD and MIRROR hints copied over the unused GHOST hint.
# 4-bit image of MODE_SEL.FBD (20-byte header, 512 halfwords wide = VRAM x 512..1023); the hints are in the texture
# page (704,256), at u 0x50, v 0x60 (HARD) / 0x78 (MIRROR) / 0x90 (GHOST), 80x24 pixels, transparent index 12.
_PX0=(704-512)*4+0x50
def _hm_blits():
    H,M=256+0x60,256+0x78; parts=[(H,8,15),(H,51,58),(M,5,13),None,(H,40,58),(M,40,50),(H,51,58),(H,59,75)]
    out=[]; x=2
    for p in parts:
        if p is None: x+=2; continue
        sy,a,b=p; out.append([_PX0+a,sy,b-a,24,_PX0+x,256+0x90]); x+=b-a
    return out
HM_LABEL=['px4','/TITLE/MODE_SEL.FBD',20,512,[_PX0,256+0x90,80,24,12],12,_hm_blits()]
def px4(d,op):
    """['px4', file, header, width (halfwords), [x,y,w,h,fill] cleared first, transparent index, [[sx,sy,w,h,dx,dy]...]]:
    copies the non-transparent 4-bit pixels of rectangles of the original image (d is modified in place)"""
    _,_,hdr,W,(cx,cy,cw,ch,fill),tr,blits=op
    import numpy as _n
    img=_n.frombuffer(bytes(d[hdr:hdr+W*2*512]),'<u2').reshape(-1,W)
    pix=_n.zeros((img.shape[0],W*4),_n.uint8)
    for k in range(4): pix[:,k::4]=(img>>(4*k))&15
    src=pix.copy(); pix[cy:cy+ch,cx:cx+cw]=fill
    for sx,sy,w,h,dx,dy in blits:
        g=src[sy:sy+h,sx:sx+w]; m=g!=tr; pix[dy:dy+h,dx:dx+w][m]=g[m]
    o=_n.zeros(img.shape,_n.uint16)
    for k in range(4): o|=(pix[:,k::4].astype(_n.uint16)&15)<<(4*k)
    d[hdr:hdr+o.size*2]=o.tobytes()
def apply(src,dst,verbose=True):
    im=Img(src,dst)
    blobs=bundles()
    files={}
    def get(p):
        if p not in files: files[p]=bytearray(im.read_file(p))
        return files[p]
    def off(p,a): return (0x800+a-EXE) if p=='/SCES_009.92' else (a-OVL)
    for p,a,old,new in patches():
        d=get(p); o=off(p,a); cur=struct.unpack('<I',d[o:o+4])[0]
        assert old is None or cur==old,(p,hex(a),hex(cur),hex(old))
        d[o:o+4]=struct.pack('<I',new)
    # Boss <-> Jicchi identities (player Boss = rider 4 is shown as BOSS; the CPU rider 7 becomes Jicchi)
    px4(get(HM_LABEL[1]),HM_LABEL)
    e=get('/DATA/CHR/ENEMY1.FBD'); e[:]=swap_boss_jicchi(e)
    for f in ['/SBC1.BIN','/SBC2.BIN','/OMT.BIN','/COMB.BIN']:
        d=get(f); nd,ok=swap_name_plates(d); assert ok,f; d[:]=nd
    # GRAY / SNOWMAN name plates drawn into EFCT_SBC (over the unused "1P WIN 2P WIN" graphics, VS uses another file)
    import tile as _tile, fontplate as _fp
    import numpy as _np
    e=get('/DATA/EFFECT/EFCT_SBC.FBD')
    _d,_clut,_pix=_tile.load(FS+'/DATA/EFFECT/EFCT_SBC.FBD'); _pix=_pix.copy()
    _pix[238:252,120:227]=15
    for txt,u in (('SNOWMAN',PL_SNOW_U),('GRAY',PL_GRAY_U)):
        g=_fp.plate(txt,_clut,11 if txt=='SNOWMAN' else 12); assert g.shape[1]<=PL_W[txt],(txt,g.shape)
        _pix[PL_V:PL_V+12,u:u+g.shape[1]]=_np.where(g==15,_pix[PL_V:PL_V+12,u:u+g.shape[1]],g)
    e[:]=_tile.dump(_d,_pix)
    pos=layout(im,blobs)
    # Boss course voice bank: stored over the last sectors of the opening movie (cut by ~0.8 s)
    bvb,boffs=boss_course_bank(); nb=(len(bvb)+2047)//2048
    olba,osz,_=im.files['/MOVIE/OPMOVIEE.STR']; on=osz//2048; blba=olba+on-nb
    im.set_record('/MOVIE/OPMOVIEE.STR',size=(on-nb)*2048)
    write_blob(im,blba,bvb)
    d2=get('/SBC2.BIN'); o2=off('/SBC2.BIN',0x80090350); assert d2[o2:o2+8+4*49]==bytes(8+4*49)
    d2[o2:o2+8]=msf_bcd(blba)+struct.pack('<I',len(bvb)); d2[o2+8:o2+8+4*49]=struct.pack('<49I',*boffs)
    tbl=b''.join(msf_bcd(pos[k])+struct.pack('<I',len(b)) for k,b in zip(['gray','snow','eg','es'],blobs))
    d=get('/SCES_009.92'); o=off('/SCES_009.92',LOCTBL); assert d[o:o+32]==bytes(32); d[o:o+32]=tbl
    # WEAR outfit previews: code + data appended to MAIN_SEL (the menu heap starts after it, see patches);
    # the grown file moves to the last sectors of the info movie SBCMOVE.STR (cut)
    import wearprev as _wp
    ms=get('/MAIN_SEL.BIN'); o=_wp.BASE-OVL; assert len(ms)<=o; ms+=bytes(o-len(ms))+_wp.block()[0]
    nms=(len(ms)+2047)//2048
    slba,ssz,_=im.files['/MOVIE/SBCMOVE.STR']; sn=ssz//2048; mlba=slba+sn-nms
    im.set_record('/MOVIE/SBCMOVE.STR',size=(sn-nms)*2048)
    write_blob(im,mlba,bytes(ms)); im.set_record('/MAIN_SEL.BIN',lba=mlba,size=len(ms)); del files['/MAIN_SEL.BIN']
    # progress page code at the end of MODE_SEL (same sectors, larger size)
    import progress as _pg
    m2=get('/MODE_SEL.BIN'); assert _pg.ORG==OVL+len(m2); org_,blob_,_=_pg.block(); m2+=blob_
    n2=(len(m2)+2047)//2048
    if n2>(im.files['/MODE_SEL.BIN'][1]+2047)//2048:     # one more sector: moves to the end of the credits movie (cut)
        slba,ssz,_=im.files['/MOVIE/STAFFE.STR']; sn=ssz//2048; mlba=slba+sn-n2
        im.set_record('/MOVIE/STAFFE.STR',size=(sn-n2)*2048)
        write_blob(im,mlba,bytes(m2)); im.set_record('/MODE_SEL.BIN',lba=mlba,size=len(m2)); del files['/MODE_SEL.BIN']
    else: im.set_record('/MODE_SEL.BIN',size=len(m2))
    for p,d in files.items():
        lba,size,_=im.files[p]; assert len(d)==size; im.write_user(lba,0,bytes(d))
    im.f.close()
    if verbose: print('built',dst,[len(b) for b in blobs],pos)
if __name__=='__main__':
    # usage: remix.py original_track1.bin remix_track1.bin  (make_remix.py does it all from the CHD)
    apply(sys.argv[1],sys.argv[2])
