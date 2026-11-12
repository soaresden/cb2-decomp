# Planches : motifs d'origine (`/DATA/CHR/BOARD.DAT`)

Même fichier dans les versions européenne et américaine (227 980 octets). En-tête `TIM*`, 43 entrées, puis des images TIM
qui sont envoyées en VRAM au chargement (INIT, chemin à 0x8005D990).

| Entrées | Format | VRAM | Contenu |
|---|---|---|---|
| 0–2 | 4 bpp, 32×32 | 512,128 | vides |
| 3–20 | 8 bpp, 128×64, CLUT ligne 491+n | 768..1023, 0..383 | 18 motifs : 6 par style (Free Style, All-Around, Alpine) |
| 21–23 | 8 bpp, 128×64 | idem | planches SPECIAL (une par style) |
| 24–41 | 4 bpp, 128×32 | 480,192 / 480,224 | versions basse définition (une face) |

Chaque motif 128×64 : lignes 0–31 = dessus (avec les inserts de fixation), lignes 32–63 = dessous, spatule à gauche ;
couleur 0 = transparent (hors du contour). C'est la même disposition que la planche « Original » de la carte mémoire
(`ORGBOARD`, voir `board.js` du site).

Écran BOARD : 3 styles × (TYPE-1, TYPE-2, TYPE-3, SPECIAL). Sur l'écran DESIGN, les 6 motifs du style sont communs aux trois
types (index courant : halfword 0x8007D040 dans MAIN_SEL, 0..5) ; la SPECIAL n'a que son motif.

Le site lit ce fichier sur le disque du joueur (Atelier → *Motifs d'origine*) : aucun pixel du jeu n'est stocké.
