#!/usr/bin/env python3
"""Build Cool Boarders 2 Remix from your own original disc, in one command.

    python3 make_remix.py "Cool Boarders 2 (Europe).chd"            -> build/Cool Boarders 2 Remix (Europe).chd
    python3 make_remix.py original.chd -o my_remix.chd --release     -> also the delta patch, the Batocera patcher
    python3 make_remix.py original.chd --us-music "Cool Boarders 2 (USA).chd"   -> with the music of the USA version
    python3 make_remix.py original.chd --config CB2-05G0-0008-KG       -> only the mods of a configuration code (site)
                                                                        and patches.js for the web site

Input: CHD (v5, cdlz/cdzl) or BIN (MODE2/2352, single file) of Cool Boarders 2 PAL (SCES-00992), unmodified.
Steps: extract the data track and its files into work/, run the Remix build (remix/remix.py), then write the result
(only the changed sectors are rewritten; a CHD output keeps the original's compression for everything else).
"""
import argparse, base64, gzip, os, struct, sys, time, zlib
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import cb2disc

ORIG_EXE_CRC = 0x60DC7C87          # SCES_009.92 of the original PAL disc
WORK = os.path.join(ROOT, 'work')

def log(*a): print(*a, flush=True)

def extract(disc, fs_dir, track_bin):
    """all ISO9660 files -> fs_dir, data track (as stored, MODE2/2352) -> track_bin; returns the sector count"""
    n = struct.unpack_from('<I', disc.user(16), 80)[0]          # volume space size (BIN source)
    if disc.kind == 'chd':                                      # CHD: length of track 1 from the track list
        n = next(int(cb2disc.cht2(dt)['FRAMES']) for tg, _, dt in cb2disc.read_meta(disc.img) if tg in (b'CHT2', b'CHTR'))
    for p, (lba, size, is_dir) in sorted(disc.files.items()):
        dst = os.path.join(fs_dir, p.lstrip('/'))
        if is_dir: os.makedirs(dst, exist_ok=True); continue
        if p.startswith('/CDDA/'): continue                      # entries pointing at the audio tracks
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f: f.write(disc.read_file(p))
    with open(track_bin, 'wb') as f:
        for lba in range(n):
            s = bytearray(disc.img.sector(lba))
            if s[0] != 0 or s[1] != 255: s[0:12] = cb2disc.SYNC   # CHD strips the sync of plain sectors
            f.write(s)
            if lba % 8192 == 0: log('  piste de données : %d / %d secteurs' % (lba, n))
    return n

def changed_sectors(a_path, b_path, n):
    """{lba: (subheader, user data)} of the sectors whose subheader or data differ"""
    mods = {}; SEC = cb2disc.SEC
    with open(a_path, 'rb') as a, open(b_path, 'rb') as b:
        for lba in range(n):
            x = a.read(SEC); y = b.read(SEC)
            if x[16:24 + 2048] != y[16:24 + 2048]: mods[lba] = (y[16:24], y[24:24 + 2048])
    return mods

def main():
    ap = argparse.ArgumentParser(description='Construit Cool Boarders 2 Remix à partir de ton disque d\'origine.')
    ap.add_argument('source', help='CHD ou BIN de Cool Boarders 2 (Europe) [SCES-00992], non modifié')
    ap.add_argument('-o', '--output', help='fichier de sortie (.chd si la source est un CHD, sinon .bin)')
    ap.add_argument('--release', action='store_true', help='produit aussi le patch delta, le patcheur Batocera et patches.js')
    ap.add_argument('--keep', action='store_true', help='garde work/ (fichiers extraits) pour une prochaine fois')
    ap.add_argument('--config', metavar='CODE', help='code de configuration du site (CB2-…) : seulement les mods choisis')
    ap.add_argument('--us-music', metavar='USA.chd', help='met les musiques de ta version américaine (CHD de Cool Boarders 2 USA)')
    a = ap.parse_args()
    t0 = time.time()
    disc = cb2disc.Disc(a.source)
    exe = disc.read_file('/SCES_009.92')
    if zlib.crc32(exe) != ORIG_EXE_CRC:
        sys.exit("Ce disque n'est pas Cool Boarders 2 (PAL) d'origine (exécutable différent : déjà patché ?).")
    ext = '.chd' if disc.kind == 'chd' else '.bin'
    out = a.output or os.path.join(ROOT, 'build', 'Cool Boarders 2 Remix (Europe)' + ext)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if a.config:                                              # modular build: no extraction needed
        sys.path.insert(0, os.path.join(ROOT, 'remix')); import modular
        c = modular.decode_config(a.config); code = modular.encode_config(c['mods'], c['us_music'], c['skins'])
        log('Code %s : %s' % (code, ', '.join(c['mods']) or 'aucun mod'))
        if c['skins']: log('   (les tenues du code se mettent avec le site ou skins/ : ignorées ici)')
        if c['us_music'] and not a.us_music: sys.exit('Ce code demande les musiques US : ajoute --us-music USA.chd')
        mods = modular.apply(disc, modular.load(os.path.join(ROOT, 'remix', 'cb2remix_mods.json.gz')), c['mods'])
        modular.mark(disc, mods, code)
        if not a.output: out = os.path.join(ROOT, 'build', 'Cool Boarders 2 Remix %s (Europe)%s' % (code[4:], ext))
        tmp = out + '.part'
        if a.us_music: cb2disc.compose_soundtrack(disc, cb2disc.Disc(a.us_music), mods, tmp, log=lambda m: log('   ' + m))
        else: cb2disc.write_patched(disc, mods, tmp, log=lambda m: log('   ' + m))
        os.replace(tmp, out); log('Terminé en %.0f s : %s' % (time.time() - t0, out)); return
    fs_dir = os.path.join(WORK, 'fs'); orig_bin = os.path.join(WORK, 'track1_original.bin'); remix_bin = os.path.join(WORK, 'track1_remix.bin')
    os.makedirs(fs_dir, exist_ok=True)
    log('1/3 Extraction du disque dans work/ ...')
    n = extract(disc, fs_dir, orig_bin)
    log('2/3 Construction du Remix (remix/remix.py) ...')
    os.environ['CB2_FS'] = fs_dir
    sys.path.insert(0, os.path.join(ROOT, 'remix'))
    import remix
    if os.path.exists(remix_bin): os.remove(remix_bin)     # Img only copies the source when the destination is missing
    remix.apply(orig_bin, remix_bin, verbose=False)
    mods = changed_sectors(orig_bin, remix_bin, n)
    log('   %d secteurs modifiés' % len(mods))
    log('3/3 Écriture de %s ...' % out)
    tmp = out + '.part'
    if a.us_music:
        if disc.kind != 'chd': sys.exit('Les musiques US demandent un jeu européen en .chd.')
        us = cb2disc.Disc(a.us_music)
        if '/SCUS_943.58' not in us.files: sys.exit("%s n'est pas Cool Boarders 2 USA (SCUS-94358)." % a.us_music)
        cb2disc.compose_soundtrack(disc, us, mods, tmp, log=lambda m: log('   ' + m))
    else:
        cb2disc.write_patched(disc, mods, tmp, log=lambda m: log('   ' + m))
    os.replace(tmp, out)
    if ext == '.bin':
        open(os.path.splitext(out)[0] + '.cue', 'w').write('FILE "%s" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n' % os.path.basename(out))
        log('   (attention : une source BIN ne contient que la piste de données si ton .cue a plusieurs fichiers)')
    if a.release:
        ver = open(os.path.join(ROOT, 'remix', 'VERSION')).read().strip()
        import mkdelta
        delta = os.path.join(ROOT, 'build', 'cb2remix.delta.gz')
        log('Patch delta ...'); mkdelta.main(orig_bin, remix_bin, delta)
        sys.path.insert(0, os.path.join(ROOT, 'remix')); import modular, shutil
        log('Paquet des mods (remix/modular.py) ...')
        mpath = os.path.join(ROOT, 'build', 'cb2remix_mods.json.gz')
        modular.save(modular.generate(orig_bin, remix_bin, fs_dir, delta), mpath)
        for f in (mpath, delta): shutil.copy(f, os.path.join(ROOT, 'remix', os.path.basename(f)))   # sources of the patchers
        import subprocess
        subprocess.run([sys.executable, os.path.join(ROOT, 'batocera', 'mkpygame.py'), delta, ver,
                        os.path.join(ROOT, 'build', 'CB2_Remix_Patcher.pygame')], check=True)
        b64 = base64.b64encode(open(delta, 'rb').read()).decode()
        m64 = base64.b64encode(open(mpath, 'rb').read()).decode()
        open(os.path.join(ROOT, 'build', 'patches.js'), 'w').write(
            "// Remix delta patch (format CB2D, see remix/mkdelta.py), generated by make_remix.py --release\n"
            "window.REMIX = { version: '%s', delta: '%s' };\n"
            "// modular Remix (remix/modular.py): one switch per mod\n"
            "window.REMIX_MODS = { version: '%s', pkg: '%s' };\n" % (ver, b64, ver, m64))
        log('build/ : cb2remix.delta.gz, CB2_Remix_Patcher.pygame, patches.js (à copier dans le site)')
    if not a.keep:
        for f in (orig_bin, remix_bin):
            if os.path.exists(f): os.remove(f)
    log('Terminé en %.0f s : %s' % (time.time() - t0, out))

if __name__ == '__main__':
    main()
