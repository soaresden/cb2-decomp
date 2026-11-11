#!/usr/bin/env python3
"""Decompilation project: split the game's binaries with splat, rebuild them and check they match the originals.
usage: python3 decomp.py split          # iso/*.BIN + iso/SCES_009.92 -> asm/ (splat)
       python3 decomp.py check [main sbc2 ...]   # assemble, link, compare byte for byte (all binaries by default)"""
import hashlib, os, subprocess, sys
AS = ['mips-linux-gnu-as', '-EL', '-march=r3000', '-mtune=r3000', '-no-pad-sections', '-G0', '-Iinclude']
def run(cmd): subprocess.run(cmd, check=True)
def build(name, target):
    objs = []
    for root, _, files in os.walk(f'asm/{name}'):
        for f in sorted(files):
            if not f.endswith('.s'): continue
            src = os.path.join(root, f); obj = os.path.join('build', src + '.o')
            os.makedirs(os.path.dirname(obj), exist_ok=True); subprocess.run(AS + ['-o', obj, src], check=True, stderr=subprocess.DEVNULL); objs.append(obj)
    for root, _, files in os.walk(f'assets/{name}'):
        for f in sorted(files):
            if not f.endswith('.bin'): continue
            src = os.path.join(root, f); obj = os.path.join('build', src + '.o')
            os.makedirs(os.path.dirname(obj), exist_ok=True)
            run(['mips-linux-gnu-objcopy', '-I', 'binary', '-O', 'elf32-tradlittlemips', src, obj]); objs.append(obj)
    elf = f'build/{name}.elf'; out = f'build/{os.path.basename(target)}'
    run(['mips-linux-gnu-ld', '-EL', '-nostdlib', '--no-check-sections', '-T', f'linker/{name}.ld',
         '-T', f'linker/undefined_funcs_auto.{name}.txt', '-T', f'linker/undefined_syms_auto.{name}.txt',
         '-Map', f'build/{name}.map', '-o', elf])
    run(['mips-linux-gnu-objcopy', '-O', 'binary', elf, out])
    a, b = open(out, 'rb').read(), open(target, 'rb').read()
    ok = a == b
    print(f'{name}: {len(objs)} fichiers, {len(a)} octets -> {"IDENTIQUE" if ok else "DIFFÉRENT"} ({hashlib.sha1(a).hexdigest()[:12]})')
    if not ok:
        n = min(len(a), len(b)); i = next((k for k in range(n) if a[k] != b[k]), n)
        print(f'  1re différence à 0x{i:x} (tailles {len(a)} / {len(b)})')
    return ok
def split(names):
    for n in names:
        subprocess.run([sys.executable, '-m', 'splat', 'split', f'config/{n}.yaml'], check=True, stdout=subprocess.DEVNULL)
        print('découpé :', n)
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    targets = {'main': 'iso/SCES_009.92'}
    targets.update({n: f'iso/{n.upper()}.BIN' for n in open('config/overlays.txt').read().split()})
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    names = sys.argv[2:] or list(targets)
    if cmd == 'split': split(names); sys.exit(0)
    res = [build(n, targets[n]) for n in names]
    print(f'{sum(res)}/{len(res)} identiques')
    sys.exit(0 if all(res) else 1)
