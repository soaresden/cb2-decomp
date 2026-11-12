#!/usr/bin/env python3
"""Build the Batocera patcher: one self-contained .pygame file (template + disc module + Remix delta).
usage: python3 batocera/mkpygame.py [delta.gz] [version] [output]
       defaults: remix/cb2remix.delta.gz, the version in remix/VERSION, build/CB2_Remix_Patcher.pygame"""
import base64, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
delta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'remix', 'cb2remix.delta.gz')
ver = sys.argv[2] if len(sys.argv) > 2 else open(os.path.join(ROOT, 'remix', 'VERSION')).read().strip()
out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, 'build', 'CB2_Remix_Patcher.pygame')
tpl = open(os.path.join(ROOT, 'batocera', 'pygame_template.py'), encoding='utf8').read()
disc = open(os.path.join(ROOT, 'tools', 'cb2disc.py'), encoding='utf8').read()
b64 = base64.b64encode(open(delta, 'rb').read()).decode()
us = os.path.join(ROOT, 'remix', 'cb2remix_usa.delta.gz')
b64us = base64.b64encode(open(us, 'rb').read()).decode() if os.path.exists(us) else ''
page = tpl.replace('__DISC__', disc).replace('__DELTA_US__', b64us).replace('__DELTA__', b64).replace('__VER__', ver)
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf8').write(page)
print(out, len(page), 'octets')
