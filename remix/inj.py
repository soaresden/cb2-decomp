# grab-switch helper: while R1/R2 (alone, no L1/L2 -> not a rail) is held and the d-pad
# changes to a non-overlapping direction, R1/R2 are masked for a few pad reads so the game
# sees a short release -> "X to Y" combos can be done by just changing direction.
from asm import asm
CNT=-0x5fc; PREV=-0x5f8   # 0x8004fa04 / 0x8004fa08 (via lui at,0x8005)
A=0x8004fba0; B=0x8004fa10; BLOCK=1
def inj():
    cb,lb=asm(['blk:','addiu t0, t0, -1',f'sw t0, {CNT}(at)','ori a2, a2, 0xa','xori a2, a2, 0xa',
               'sp:','beqz t2, idn','nop','beq zero, zero, idn',f'sw t2, {PREV}(at)',
               'nog:',f'sw zero, {PREV}(at)',f'sw zero, {CNT}(at)',
               'idn:','j 0x8001b5a0','nop'],B)
    assert cb[-1][0]<0x8004fa40
    L={k:str(v) for k,v in lb.items()}
    ca,la=asm(['inj:','bnez a0, '+L['idn'],'lui at, 0x8005',f'lw t0, {CNT}(at)',
               'andi t4, a2, 0x5','bnez t4, '+L['nog'],'andi t4, a2, 0xa','beqz t4, '+L['nog'],'andi t2, a2, 0xf000',
               f'lw t1, {PREV}(at)','bnez t0, '+L['blk'],'and t4, t1, t2',
               'beqz t2, '+L['idn'],'nop','bnez t4, '+L['sp'],'nop','beqz t1, '+L['sp'],f'addiu t0, zero, {BLOCK+1}',
               'j '+L['blk'],'nop'],A)
    assert ca[-1][0]<0x8004fbf0
    return ca+cb,la['inj']
