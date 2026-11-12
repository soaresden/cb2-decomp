#!/usr/bin/env python3
# Cool Boarders 2 Remix v__VER__ : patcheur pour Batocera (systeme "Pygame").
# Mets ce fichier dans /userdata/roms/pygame/ puis lance-le depuis le systeme Pygame.
# Il cherche le Cool Boarders 2 (PAL, SCES-00992) d'origine dans /userdata/roms/psx (.chd ou .bin/.cue)
# et ecrit "Cool Boarders 2 Remix (Europe).chd" (ou .bin + .cue) a cote. Rien n'est telecharge.
# En ligne de commande : python3 CB2_Remix_Patcher.pygame source.chd destination.chd [usa.chd]
# Si le CHD de Cool Boarders 2 (USA) est aussi dans roms/psx, il propose de mettre ses musiques dans le Remix.
# Interrupteurs : un ecran liste les mods (croix haut/bas, A = cocher, START = construire). Le code de configuration
# du site (CB2-XXXX-XXXX) peut etre mis dans cb2remix_code.txt a cote de ce fichier : il sert de reglage de depart.
# En ligne de commande : python3 CB2_Remix_Patcher.pygame source.chd destination.chd --code CB2-XXXX-XXXX [--us usa.chd]
import os, sys, gzip, base64, time, json

VERSION = "__VER__"
DELTA_B64 = "__DELTA__"
DELTA_US_B64 = "__DELTA_US__"     # Remix for the USA version (phase 1)
MODS_B64 = "__MODS__"             # modular Remix package (remix/modular.py)
OUT_BASE = "Cool Boarders 2 Remix (Europe)"
SEARCH_DIRS = ["/userdata/roms/psx", "/userdata/roms", os.path.dirname(os.path.abspath(__file__))]

# ================================================================ disc access (tools/cb2disc.py of cb2-decomp)
__DISC__
# ================================================================ modular Remix (remix/modular.py of cb2-decomp)
MODULAR_SRC = r'''__MODULAR__'''
import types; M = {'cb2disc': types.SimpleNamespace(**globals()), '__name__': 'modular'}
exec(compile("import base64, gzip, json, os, struct, sys, zlib\n" + MODULAR_SRC, 'modular', 'exec'), M)
PKG = json.loads(gzip.decompress(base64.b64decode(MODS_B64)))
def _lang():
    try:
        for l in open('/userdata/system/batocera.conf', encoding='utf8', errors='ignore'):
            if l.startswith('system.language='): return l.split('=', 1)[1].strip()[:2].lower()
    except Exception: pass
    return (os.environ.get('LANG') or 'en')[:2].lower()
FR = _lang() == 'fr'
def T(fr, en): return fr if FR else en
CODE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cb2remix_code.txt')
# ================================================================

def is_remix(disc):
    if M['read_config'](disc): return True
    if '/SCUS_943.58' in disc.files:   # USA: the Hard + Mirror code of the US Remix
        exe = disc.read_file('/SCUS_943.58'); o = 0x800 + 0x8004f538 - 0x80010000; return any(exe[o:o + 4])
    exe = disc.read_file('/SCES_009.92'); o = 0x800 + 0x8004f900 - 0x80010000
    return any(exe[o + 4:o + 7])

def find_sources(log):
    """-> [(path, Disc)] originals, [paths] already patched, [(path, Disc)] USA discs (CHD)"""
    orig, done, usa = [], [], []
    for d in SEARCH_DIRS:
        if not os.path.isdir(d): continue
        for root_, dirs, files in os.walk(d):
            if root_.count(os.sep) - d.count(os.sep) > 1: dirs[:] = []
            for fn in sorted(files):
                low = fn.lower()
                if not (low.endswith('.chd') or low.endswith('.bin')): continue
                p = os.path.join(root_, fn)
                if any(p == q for q, _ in orig) or p in done: continue
                try:
                    disc = Disc(p)
                    if '/SCUS_943.58' in disc.files and disc.kind == 'chd': usa.append((p, disc)); continue
                    if '/SCES_009.92' not in disc.files: continue
                except Exception:
                    continue
                if is_remix(disc): done.append(p)
                else: orig.append((p, disc))
    return orig, done, usa

def patch(src, dst, log=print, progress=lambda f: None, us=None, cfg=None):
    """cfg: decode_config() result (European disc); None = the whole Remix"""
    disc = src if isinstance(src, Disc) else Disc(src)
    if is_remix(disc): raise ValueError(T("ce disque a deja le Remix", "this disc already has the Remix"))
    log(T("Calcul du patch...", "Building the patch..."))
    if '/SCUS_943.58' in disc.files: mods = apply_delta(disc, gzip.decompress(base64.b64decode(DELTA_US_B64)), log=log)
    else:
        cfg = cfg or {'mods': M['IDS'], 'us_music': us is not None, 'skins': []}
        mods = M['apply'](disc, PKG, cfg['mods'])
        M['mark'](disc, mods, M['encode_config'](cfg['mods'], cfg['us_music'], cfg['skins']))
    tmp = dst + '.part'
    if us is not None:
        log(T("Musiques de la version americaine...", "USA version music..."))
        compose_soundtrack(disc, us, mods, tmp, log=lambda m: None, progress=progress)
    else:
        write_patched(disc, mods, tmp, log=log, progress=progress)
    os.replace(tmp, dst)
    if disc.kind == 'bin':   # matching .cue next to the new .bin
        base = os.path.splitext(disc.img.path)[0]
        for cue in (base + '.cue', base + '.CUE'):
            if os.path.exists(cue):
                t = open(cue, encoding='latin1').read().replace(os.path.basename(disc.img.path), os.path.basename(dst))
                open(os.path.splitext(dst)[0] + '.cue', 'w', encoding='latin1').write(t)
                break
    return len(mods)

NAMES = {f[0]: (f[1] if FR else f[2]).replace('\u2019', "'") for f in M['FEATURES']}
PRESETS = [(T('Remix complet', 'Full Remix'), list(M['IDS'])), (T('100 % a gagner', '100% to earn'), [f for f in M['IDS'] if f not in ('unlock', 'special')]), (T('Aucun mod', 'No mods'), [])]

def start_config():
    for src in (CODE_FILE,):
        try: return M['decode_config'](open(src).read().strip())
        except Exception: pass
    return {'mods': list(M['IDS']), 'us_music': False, 'skins': []}

def menu(pygame, scr, fonts, cfg, has_us):
    """switch screen: up/down, A (or Enter) = tick, START (or Space) = build, B = back to the full Remix. -> cfg"""
    big, small = fonts; W, H = scr.get_size()
    rows = [('mod', f) for f in M['IDS']] + ([('us', None)] if has_us else []) + [('preset', i) for i in range(len(PRESETS))] + [('go', None)]
    cur = len(rows) - 1; last_axis = 0
    while True:
        scr.fill((16, 22, 30))
        scr.blit(big.render("Cool Boarders 2 Remix v" + VERSION, True, (240, 240, 250)), (W // 20, H // 30))
        code = M['encode_config'](cfg['mods'], cfg['us_music'], cfg['skins'])
        scr.blit(small.render("Code : " + code + T("    (A = cocher, START = construire)", "    (A = tick, START = build)"), True, (143, 211, 255)), (W // 20, H // 30 + big.get_height()))
        y = H // 30 + big.get_height() + small.get_height() + H // 40; lh = (H - y - H // 30) // len(rows)
        for i, (k, v) in enumerate(rows):
            if k == 'mod': txt = ('[x] ' if v in cfg['mods'] else '[ ] ') + NAMES[v]
            elif k == 'us': txt = ('[x] ' if cfg['us_music'] else '[ ] ') + T('Musiques de la version americaine', 'Music of the USA version')
            elif k == 'preset': txt = '>> ' + PRESETS[v][0]
            else: txt = T('>>> CONSTRUIRE LE JEU <<<', '>>> BUILD THE GAME <<<')
            col = (255, 160, 80) if i == cur else (200, 210, 225)
            scr.blit(small.render(txt, True, col), (W // 20 + (0 if k in ('mod', 'us') else W // 40), y + i * lh))
        pygame.display.flip()
        for ev in pygame.event.get():
            mv = 0; act = None
            if ev.type == pygame.KEYDOWN:
                mv = {pygame.K_UP: -1, pygame.K_DOWN: 1}.get(ev.key, 0)
                act = 'ok' if ev.key in (pygame.K_RETURN, pygame.K_a) else 'go' if ev.key == pygame.K_SPACE else None
            elif ev.type == pygame.JOYHATMOTION: mv = -ev.value[1]
            elif ev.type == pygame.JOYAXISMOTION and ev.axis == 1:
                a = -1 if ev.value < -0.6 else 1 if ev.value > 0.6 else 0
                if a != last_axis: mv = a
                last_axis = a
            elif ev.type == pygame.JOYBUTTONDOWN:
                act = 'go' if ev.button in (7, 9, 11) else 'ok' if ev.button in (0, 2) else None
            cur = (cur + mv) % len(rows)
            if act == 'go': return cfg
            if act == 'ok':
                k, v = rows[cur]
                if k == 'mod': cfg['mods'] = [f for f in M['IDS'] if (f in cfg['mods']) != (f == v)]
                elif k == 'us': cfg['us_music'] = not cfg['us_music']
                elif k == 'preset': cfg['mods'] = list(PRESETS[v][1])
                else: return cfg
        time.sleep(0.03)

def choose(pygame, timeout=30):
    """True = with the USA music. Gamepad: button 1 or 3 (B / circle side), keyboard: Space. Default after 30 s: Remix only."""
    if not pygame:
        try: return input("Musiques US ? (o/N) ").strip().lower().startswith('o')
        except EOFError: return False
    t0 = time.time()
    while time.time() - t0 < timeout:
        for ev in pygame.event.get():
            if ev.type == pygame.JOYBUTTONDOWN: return ev.button in (1, 3)
            if ev.type == pygame.KEYDOWN: return ev.key == pygame.K_SPACE
        time.sleep(0.05)
    return False

def main():
    try:
        import pygame
    except ImportError:
        pygame = None
    lines = []; state = {'p': None}
    def say(t):
        lines.append(t); print(t)
        if pygame: draw()
    if pygame:
        pygame.init(); pygame.joystick.init()
        for i in range(pygame.joystick.get_count()): pygame.joystick.Joystick(i).init()
        info = pygame.display.Info()
        scr = pygame.display.set_mode((info.current_w or 1280, info.current_h or 720), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        W, H = scr.get_size(); big = pygame.font.Font(None, max(36, H // 14)); small = pygame.font.Font(None, max(24, H // 26))
        def draw():
            scr.fill((16, 22, 30))
            scr.blit(big.render("Cool Boarders 2 Remix v" + VERSION, True, (240, 240, 250)), (W // 20, H // 14))
            y = H // 14 + big.get_height() + H // 30
            for t in lines[-12:]:
                col = (110, 210, 140) if t.startswith("OK") else (255, 140, 130) if t.startswith(("Erreur", "Error")) else (200, 210, 225)
                scr.blit(small.render(t, True, col), (W // 20, y)); y += small.get_height() + 6
            if state['p'] is not None:
                bw = W - W // 10; pygame.draw.rect(scr, (60, 70, 85), (W // 20, H - H // 6, bw, H // 24), border_radius=8)
                pygame.draw.rect(scr, (90, 170, 255), (W // 20, H - H // 6, int(bw * state['p']), H // 24), border_radius=8)
            pygame.display.flip(); pygame.event.pump()
    say(T("Recherche de Cool Boarders 2 (PAL) d'origine...", "Looking for the original Cool Boarders 2 (PAL)..."))
    orig, done, usa = find_sources(say)
    usa_orig = [(p, d) for p, d in usa if not is_remix(d)]
    if not orig and usa_orig:      # only the USA version: the US Remix
        s, disc = usa_orig[0]; dst = os.path.join(os.path.dirname(s), "Cool Boarders 2 Remix (USA).chd")
        say(T("Source (USA) : ", "Source (USA): ") + s); say(T("Creation : ", "Writing: ") + dst)
        say(T("Remix US, 1re version : tout debloque + Hard/Mirror (L1+R1+X)", "US Remix, 1st version: everything unlocked + Hard/Mirror (L1+R1+X)"))
        try:
            n = patch(disc, dst, log=say, progress=lambda x: (state.__setitem__('p', x), pygame and draw()))
            say(T("OK : termine (%d secteurs modifies). Mets a jour la liste des jeux.", "OK: done (%d sectors changed). Update the game list.") % n)
        except Exception as e:
            say(T("Erreur : ", "Error: ") + str(e))
    elif not orig:
        if done: say(T("OK : le Remix est deja la : ", "OK: Remix is already there: ") + done[0])
        else: say(T("Erreur : Cool Boarders 2 (PAL) d'origine introuvable dans /userdata/roms/psx (.chd ou .bin)", "Error: original Cool Boarders 2 (PAL) not found in /userdata/roms/psx (.chd or .bin)"))
    else:
        s, disc = orig[0]; ext = '.chd' if disc.kind == 'chd' else '.bin'
        has_us = bool(usa_orig) and disc.kind == 'chd'
        cfg = start_config()
        if pygame: cfg = menu(pygame, scr, (big, small), cfg, has_us); lines.clear()
        us = usa_orig[0][1] if has_us and cfg['us_music'] else None
        if cfg['us_music'] and us is None: cfg['us_music'] = False; say(T("(musiques US : il faut le CHD americain dans roms/psx)", "(US music: the USA CHD must be in roms/psx)"))
        code = M['encode_config'](cfg['mods'], cfg['us_music'], cfg['skins'])
        if cfg['skins']: say(T("(les tenues du code se mettent avec le site : ignorees ici)", "(outfits in the code are added by the web site: ignored here)"))
        try: open(CODE_FILE, 'w').write(code + '\n')
        except Exception: pass
        dst = os.path.join(os.path.dirname(s), OUT_BASE.replace('Remix', 'Remix ' + code[4:]) + ext)
        say(T("Code : ", "Code: ") + code + "  (" + (', '.join(NAMES[f] for f in cfg['mods']) or 'no mod') + ")")
        say(T("Source : ", "Source: ") + s); say(T("Creation : ", "Writing: ") + dst)
        last = [0]
        def prog(x):
            state['p'] = x
            if pygame and x - last[0] > 0.01: last[0] = x; draw()
        try:
            n = patch(disc, dst, log=say, progress=prog, us=us, cfg=cfg)
            say(T("OK : termine (%d secteurs modifies). Mets a jour la liste des jeux.", "OK: done (%d sectors changed). Update the game list.") % n)
        except Exception as e:
            say(T("Erreur : ", "Error: ") + str(e))
    say(T("Appuie sur un bouton pour quitter.", "Press a button to quit."))
    if pygame:
        t0 = time.time()
        while time.time() - t0 < 600:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.KEYDOWN, pygame.JOYBUTTONDOWN): pygame.quit(); return
            time.sleep(0.05)
        pygame.quit()

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) >= 2:      # source dest [--code CB2-...] [--us usa.chd]  (or the old form: source dest usa.chd)
        code = a[a.index('--code') + 1] if '--code' in a else None
        usp = a[a.index('--us') + 1] if '--us' in a else (a[2] if len(a) == 3 else None)
        cfg = M['decode_config'](code) if code else None
        if cfg and usp is None: cfg['us_music'] = False
        patch(a[0], a[1], us=Disc(usp) if usp else None, cfg=cfg)
    else: main()
