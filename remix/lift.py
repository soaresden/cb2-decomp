# Free Style lift: just before the finish line, the rider goes back to the top of the course (the game's own
# instant "Restart" of the pause menu), so runs can be chained without menus.
# Trigger: last section (checkpoint counter player+0xCB6 == 3) and course segment player+0xEC >= nodes - MARGIN
# (White Resort: 148 nodes, finish line at node 145). Action: race exit code 0x8009E234 = 1 (= pause menu "Restart").
# Hook: FREE calls the checkpoint update func_8005FE2C at 0x8005D04C every frame of the run; the call goes through
# the code below, which then jumps to it. Code at the end of FREE.BIN (rest of its last sector); FREE's heap start
# (exe table of overlay heap starts, entry 7) moves after it.
import struct
from asm import asm
ORG = 0x800a4198                 # end of FREE.BIN (0x8005AEA8 + 0x492F0)
HOOK = 0x8005d04c; HOOK_OLD = 0x0c017f8b          # jal func_8005FE2C
HEAP_ENTRY = 0x800100cc; HEAP_OLD = 0x800a4198
MARGIN = 6

def block(margin=None, section=3):
    margin = MARGIN if margin is None else margin
    L = ['lift:', 'lui t0, 0x800a', 'lw t1, 0x3da0(t0)', 'lw t2, 0x3d78(t0)', 'lw t3, -0x1dcc(t0)',
         'lh t4, 0xcb6(t1)', 'lw t5, -4(t2)', 'bnez t3, out', f'addiu t4, t4, -{section}', 'bnez t4, out', 'lh t6, 0xec(t1)',
         f'addiu t5, t5, -{margin}', 'slt t7, t6, t5', 'bnez t7, out', 'addiu t3, zero, 1', 'sw t3, -0x1dcc(t0)',
         'out:', 'j 0x8005fe2c', 'nop']
    code, labs = asm(L, ORG)
    blob = b''.join(struct.pack('<I', w) for _, w in code)
    heap = (ORG + len(blob) + 15) & ~15
    return ORG, blob, (3 << 26) | ((labs['lift'] >> 2) & 0x3ffffff), heap

if __name__ == '__main__':
    o, b, h, hp = block(); print(hex(o), len(b), hex(h), hex(hp))
