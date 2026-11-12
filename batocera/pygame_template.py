#!/usr/bin/env python3
# Cool Boarders 2 Remix v__VER__ : patcheur pour Batocera (systeme "Pygame").
# Mets ce fichier dans /userdata/roms/pygame/ puis lance-le depuis le systeme Pygame.
# Il cherche le Cool Boarders 2 (PAL, SCES-00992) d'origine dans /userdata/roms/psx (.chd ou .bin/.cue)
# et ecrit "Cool Boarders 2 Remix (Europe).chd" (ou .bin + .cue) a cote. Rien n'est telecharge.
# En ligne de commande : python3 CB2_Remix_Patcher.pygame source.chd destination.chd [usa.chd]
# Si le CHD de Cool Boarders 2 (USA) est aussi dans roms/psx, il propose de mettre ses musiques dans le Remix.
import os, sys, gzip, base64, time

VERSION = "__VER__"
DELTA_B64 = "__DELTA__"
DELTA_US_B64 = "__DELTA_US__"     # Remix for the USA version (phase 1)
OUT_BASE = "Cool Boarders 2 Remix (Europe)"
SEARCH_DIRS = ["/userdata/roms/psx", "/userdata/roms", os.path.dirname(os.path.abspath(__file__))]

# ================================================================ disc access (tools/cb2disc.py of cb2-decomp)
__DISC__
# ================================================================

def is_remix(disc):
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

def patch(src, dst, log=print, progress=lambda f: None, us=None):
    disc = src if isinstance(src, Disc) else Disc(src)
    P = gzip.decompress(base64.b64decode(DELTA_US_B64 if '/SCUS_943.58' in disc.files else DELTA_B64))
    if is_remix(disc): raise ValueError("ce disque a deja le Remix")
    log("Calcul du patch...")
    mods = apply_delta(disc, P, log=log)
    tmp = dst + '.part'
    if us is not None:
        log("Musiques de la version americaine...")
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
                col = (110, 210, 140) if t.startswith("OK") else (255, 140, 130) if t.startswith("Erreur") else (200, 210, 225)
                scr.blit(small.render(t, True, col), (W // 20, y)); y += small.get_height() + 6
            if state['p'] is not None:
                bw = W - W // 10; pygame.draw.rect(scr, (60, 70, 85), (W // 20, H - H // 6, bw, H // 24), border_radius=8)
                pygame.draw.rect(scr, (90, 170, 255), (W // 20, H - H // 6, int(bw * state['p']), H // 24), border_radius=8)
            pygame.display.flip(); pygame.event.pump()
    say("Recherche de Cool Boarders 2 (PAL) d'origine...")
    orig, done, usa = find_sources(say)
    usa_orig = [(p, d) for p, d in usa if not is_remix(d)]
    if not orig and usa_orig:      # only the USA version: the US Remix
        s, disc = usa_orig[0]; dst = os.path.join(os.path.dirname(s), "Cool Boarders 2 Remix (USA).chd")
        say("Source (USA) : " + s); say("Creation : " + dst)
        say("Remix US, 1re version : tout debloque + Hard/Mirror (L1+R1+X)")
        try:
            n = patch(disc, dst, log=say, progress=lambda x: (state.__setitem__('p', x), pygame and draw()))
            say("OK : termine (%d secteurs modifies). Mets a jour la liste des jeux." % n)
        except Exception as e:
            say("Erreur : " + str(e))
    elif not orig:
        if done: say("OK : le Remix est deja la : " + done[0])
        else: say("Erreur : Cool Boarders 2 (PAL) d'origine introuvable dans /userdata/roms/psx (.chd ou .bin)")
    else:
        s, disc = orig[0]; ext = '.chd' if disc.kind == 'chd' else '.bin'
        us = None
        if usa_orig and disc.kind == 'chd':   # the player also has the USA disc: offer its soundtrack
            say("Version americaine trouvee : " + os.path.basename(usa_orig[0][0]))
            say("Bouton A (ou Entree) : Remix seul   |   Bouton B (ou Espace) : Remix + musiques US")
            if choose(pygame): us = usa_orig[0][1]
        dst = os.path.join(os.path.dirname(s), OUT_BASE + (' (musiques US)' if us else '') + ext)
        say("Source : " + s); say("Creation : " + dst)
        last = [0]
        def prog(x):
            state['p'] = x
            if pygame and x - last[0] > 0.01: last[0] = x; draw()
        try:
            n = patch(disc, dst, log=say, progress=prog, us=us)
            say("OK : termine (%d secteurs modifies). Mets a jour la liste des jeux." % n)
        except Exception as e:
            say("Erreur : " + str(e))
    say("Appuie sur un bouton pour quitter.")
    if pygame:
        t0 = time.time()
        while time.time() - t0 < 600:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.KEYDOWN, pygame.JOYBUTTONDOWN): pygame.quit(); return
            time.sleep(0.05)
        pygame.quit()

if __name__ == '__main__':
    if len(sys.argv) == 4: patch(sys.argv[1], sys.argv[2], us=Disc(sys.argv[3]))   # source.chd dest.chd usa.chd
    elif len(sys.argv) == 3: patch(sys.argv[1], sys.argv[2])
    else: main()
