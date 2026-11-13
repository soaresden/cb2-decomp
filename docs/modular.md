# Remix modulaire : un interrupteur par mod, et un code de configuration

`remix/modular.py` découpe le Remix (v23) en 11 mods indépendants. Le site (onglet Patchs), `make_remix.py --config` et le
patcheur Batocera utilisent le même paquet (`remix/cb2remix_mods.json.gz`, 31 Ko) et donnent **le même fichier, à l'octet
près**.

| id | Mod | Ce que ça touche |
|---|---|---|
| `unlock` | Tout débloqué | INIT (valeurs de départ), MAIN_SEL 0x80063EA8 (riders sélectionnables avec une ancienne sauvegarde) |
| `special` | Planches SPECIAL partout | MAIN_SEL 0x8005B0C4 + lectures de 0x80057442 |
| `hardmirror` | Hard + Mirror | exe 0x8004F878–0x8004F89F, MODE_SEL (dont 0x800647DC : 3e ligne de la télé), étiquette « H+M L1+R1+X » dans `TITLE/MODE_SEL.FBD` |
| `riders` | Boss, Gray et Snowman en championnat | caves de l'exe, MAIN_SEL, SBC1/SBC2, ENEMY1, EFCT_SBC (plaques), LOCTBL, paquets de modèles, voix de Boss (fin du film d'intro coupée) |
| `outfits` | Tenues cachées de Cindy et Irin | MAIN_SEL (grandit : déplacé à la fin de SBCMOVE.STR, coupée), exe |
| `max` | Stats MAX | MAIN_SEL + écrans de course |
| `air` | Figures en l'air | overlays de course |
| `ramming` | Chocs en Boarder Cross | exe 0x80028BF4–0x80028D3C, SBC2 |
| `bam` | Big Air Master | TM |
| `lift` | *Retiré en v25 (le joueur préfère la célébration et le replay d'origine) ; gardé dans les codes.* | (FREE 0x8005D5A4 — voir `freestyle_lift.md`) |
| `progress` | Progression dans le jeu (SELECT sur l'écran des modes) | fin de MODE_SEL (82 secteurs : déplacé à la fin de STAFFE.STR, coupé), crochet 0x800643B4, début du tas de MODE_SEL (exe 0x800100B4) — voir `progression.md` |
| `skipq` | Compétition sans qualifications | exe 0x800291CC–0x8002934B, SBC1 0x8005B058 (docs/competition.md) |

Écran titre : « REMIX » à côté du « 2 » (`remix/title.py`, dans `ETC/CB2T1E.FBD` et `CB2T2E.FBD`) dès qu'un mod est choisi
(`brand`, ajouté automatiquement ; avec `riders` les deux fichiers sont déplacés et leurs copies le portent déjà).

`max` et `air` partagent la lecture de la manette (`input`, ajoutée automatiquement). Sans `air`, les sauts du code
partagé vers la partie « contrôle en l'air » retournent directement au jeu (`input_noair`).

## Vérifications

- tous les mods = build de référence (v22 : 806 secteurs identiques) ; aucun mod = disque d'origine ;
- moteur JS (`disc.js` `applyMods`) = moteur Python sur plusieurs combinaisons ;
- émulateur (Beetle PSX) : chaque mod seul et « tous sauf un » (18 images) démarrent, passent les menus et jouent une
  manche de compétition ;
- « 100 % à gagner » (tout sauf `unlock` et `special`) : 4 riders seulement sur une nouvelle partie (0x80057440 = 0xF),
  miroir et hard verrouillés, R1 : MAX présent (rider), ligne MAX sur l'écran BOARD.

## Le paquet

Opérations par mod, relatives au disque d'origine : mots de 32 bits (`w`, avec la valeur d'origine vérifiée), octets
(`bs` : copiés depuis le fichier d'origine ou nouveaux), ajout à la fin d'un fichier (`append`), entrées de répertoire
(`rec`), secteurs entiers (`sec`, copies depuis le disque + octets nouveaux), image 4 bits recomposée à partir de
rectangles de l'image d'origine (`px4`), portraits décodés d'une vidéo du disque du joueur (`face`, mod `crew`).
Aucune donnée du jeu n'y est stockée : ce qui vient du jeu est copié depuis le disque du joueur.

Régénération (après un changement du Remix) : `make_remix.py --release` (écrit aussi `build/patches.js` avec
`window.REMIX_MODS`), ou :

```
python3 remix/modular.py PAL.chd "Remix v16.chd" PAL_fs remix/cb2remix.delta.gz remix/cb2remix_mods.json.gz
```

## Code de configuration

`CB2-XXXX-XXXX` : 1 octet de version, 2 octets de mods (bit i = i-ème mod du tableau ci-dessus), 1 octet d'options
(bit 0 : musiques US ; bits 1-3 réservés : intro, 60 Hz), jusqu’à 8 octets de tenues du Prêt-à-porter (bit i = entrée i de
`skins/index.json` du site), octets nuls de fin retirés, puis 1 octet de contrôle (crc32 & 255), en base32 Crockford.
Exemples : `CB2-07ZG-FX0` = Remix complet, `CB2-07Y0-EDR` = 100 % à gagner (avec la page de progression et l'arrivée express), `CB2-040B-W` =
aucun mod. Les codes d'avant la v18 (sans le bit `progress`) restent valables.

Le code est écrit dans le disque construit (descripteur de volume, secteur 16, octet 900, zone inutilisée par le jeu) :
le site et le patcheur reconnaissent un jeu déjà patché et affichent son code.

```
python3 make_remix.py original.chd --config CB2-07Y0-6BG      # (les tenues : avec le site)
python3 CB2_Remix_Patcher.pygame source.chd dest.chd --code CB2-07Y0-6BG [--us usa.chd]
```

Sur Batocera, le patcheur ouvre un écran d'interrupteurs (croix haut/bas, A = cocher, START = construire) et part du
code de `cb2remix_code.txt` (à côté du .pygame) s'il existe ; il y enregistre le dernier code utilisé.

## Intro

Les films d'intro européen (`OPMOVIEE.STR`) et américain (`OPMOVIEA.STR`) ont exactement la même taille : c'est le
même film ré-encodé. Le choix de l'intro n'apporte donc rien ; le champ est réservé dans le code (pour « sans intro »
plus tard : le film est lancé par INIT, table de 4 chemins à 0x8005F700).

## Télé du menu : Hard + Mirror (v17)

Sur l'écran de sélection de mode, la télé affiche des aides en images (texture page (704,256) de `TITLE/MODE_SEL.FBD`,
80×24 pixels) : « HARD L1+X » (si le Hard est débloqué), « MIRROR R1+X » (si le Mirror l'est) et une troisième,
« GHOST L2+X », que le jeu n'affiche jamais (`func_80064798`, case 2 : toujours éteinte). La v17 :
- redessine cette 3e image en « H+M L1+R1+X » avec les lettres des deux autres (recette `remix.HM_LABEL`, appliquée au
  fichier du joueur : aucun pixel du jeu n'est stocké) ;
- l'affiche sur Competition comme la ligne HARD (0x800647DC : `j 0x80064820` → `j 0x800647E4`), donc seulement quand le
  Hard est débloqué : en « 100 % à gagner », le Hard + Mirror se débloque avec le Hard.

## Planche MAX (dans le mod `max`, v23, ligne MAX en v24)

Écran BOARD : une ligne **MAX** sous SPECIAL (sous TYPE-3 tant que la SPECIAL du style est verrouillée). Bas sur la
dernière ligne la choisit (le jeu, lui, ne bouge pas), Haut la quitte (Haut est retiré de la manette tant que MAX est
choisie, puis jusqu'à ce qu'il soit relâché, pour que le curseur du jeu reste en place). « MAX » est le début du
graphisme MAXSPEED de l'écran, recadré, orange quand la ligne est choisie ; le libellé du type n'est plus surligné
(le test « planche d'origine » de la boucle des libellés répond oui) ; les barres passent à 10/10/10.
Écran DESIGN : avec MAX, Gauche / Droite parcourent les **21 motifs** du jeu (0-17 : les 6 de chaque style, 18-20 : les
SPECIAL) au lieu des 6 du style, le carrousel montre les voisins dans toute la liste, « MAX : 21 DESIGNS » en bas.
Le numéro de motif est global dans le jeu : une course charge le motif n de BOARD.DAT quelle que soit la planche
(vérifié dans l'émulateur), voir docs/boards.md.

Course : la table des planches (10 octets par planche : vitesse max, réactivité, stabilité × 3 variantes selon le mode ;
0x800988B0 dans FREE, une copie dans chacun des 9 modes de course) reçoit, à l'entrée du mode de course (exe
0x8001228C, appel du point d'entrée de l'overlay), à la ligne de la planche du joueur (0x8005740A), les meilleures
valeurs du jeu : 165/157/196, 100/110/80, 80/88/80. Code dans `func_8002815C` et `func_8001B774` (fonctions mortes de
l'exe), voir remix/boardmax.py. Un concurrent de l'ordinateur qui aurait la même planche en profite aussi.

## Jicchi, Nick et Kelly jouables (`crew`, v26)

Code et données : `remix/crew.py` ; ses opérations sont calculées par `generate()` directement (hors build de
référence et hors delta). Les trois riders sont des **alias** : le jeu garde un numéro de rider normal (BASE : Jicchi
→ Yaggi, Nick → Jin, Kelly → Cindy, pour les animations, voix, etc.) et une variable ALIAS (1 à 3) dit qu'il s'agit
en fait de Jicchi / Nick / Kelly. Modes autorisés (0x80057420) : 2 Free Style, 5 Big Air, 6 Big Air Master,
7 Halfpipe, 8 Board Park (pas 0/1 Compétition, ni 3/4 VS).

| Partie | Accroche |
|---|---|
| liste de l'écran BOARDER | appels de `func_80063E7C` : JICCHI NICK KELLY après IRIN ; curseur alias ACUR (écran BOARDER) copié depuis ALIAS à l'ouverture (`cinit`, 0x80060218) et vers ALIAS à la validation (`ccom`, 0x800605A8) |
| portrait / nom | `func_80063324` / `func_800637A4` appelées normalement, puis la primitive (v0 − 0x28) est dirigée vers les nouvelles images |
| barres de stats | lignes de D_8007B328 : `sll v0, v0, 2` → STATS (affichage seulement) |
| fichiers en course | `func_8001D1B8` (modèle +0x10, texture +0x24) et `func_8001D694` (Halfpipe… : texture +0x20) : `jal func_80013BD0` → nouveaux fichiers |
| paramètres de course | `sll v0, R, 4` avant le pointeur de paramètres des overlays à un joueur (FREE, TM, HP, BP, OMT, COMB) → les paramètres du rider de l'ordinateur (table de SBC2, places 4 à 6) |

- Code dans des fonctions jamais appelées de l'exe (aucun `jal`, aucun pointeur, aucun saut dedans, vérifié dans tous
  les fichiers) ; données à 0x8001FBC4.
- Nouveaux fichiers (modèle et texture des trois riders, `remix/cpurider.py`) : à la fin du film d'intro, juste avant
  les secteurs du mod `riders` (le film est raccourci de 71 secteurs). Table de fichiers dans l'exe (MSF + taille),
  numéro de fichier = (entrée − 0x800583E8) / 8 (négatif). Secteurs : copies depuis PLAYER0.DAT / ENEMY1 / ENEMY2 ;
  seuls les octets recalculés du modèle (palette, page, u) sont écrits.
- Portraits : fiches profil de la vidéo `MOVIE/SBCMOVE.STR` (images 318, 344, 330), décodées par le patcheur
  (`mdec_decode`, MDEC version 2, entiers seulement : `disc.js` donne les mêmes octets), détourées, réduites à 64×64
  (affichées en 64×80), 94 couleurs + un contour sombre (fond blanc ou noir
  rempli depuis les bords, halo de compression rongé sur 2 pixels, points isolés retirés). Écrites dans `TITLE/MAIN_SEL.FBD`, zone que les écrans du menu n'utilisent pas
  (VRAM x 832..1023, y 320..383) : visages à x 832 / 864 / 896, palettes en x 928 lignes 320..322, noms (dessinés
  par le Remix, 48×32, 4 bits, palette des noms du jeu en 768,464) à x 960 / 972 / 984, y 352.
- Limites : dans le menu, l'aperçu 3D reste le modèle de Yaggi / Jin / Cindy (modèles du menu dans TITLE/CHR.DAT,
  chargé en entier, sans place libre) ; voix, animations et nom en course sont ceux du rider de base.
- Vérifié : émulateur (Free Style, Big Air, Halfpipe, Board Park ; crew seul et avec tous les mods) ; JS = Python ;
  patcheur Batocera = build Python.

## Vue arrière (`rear`, v26)

Code : `remix/rear.py` (opérations calculées par `generate()`). Les courses règlent leur caméra à chaque image par
`GsSetView2` (libgs, exe 0x80030984), qui écrit GsWSMATRIX (0x80058E20) ; la vue est relative au rider (l'origine
du monde est le rider). Rond maintenu (0x8004FBF0, bit 0x20) dans un overlay de course (mot 0 de l'overlay = 8, sauf
ENDING) : à la fin de `GsSetView2`, GsWSMATRIX et sa copie de travail (0x80059220) tournent de 180° autour de l'axe
vertical du monde (colonnes X et Z opposées) : la caméra passe devant le rider, même distance et même hauteur, et
regarde derrière lui. Code dans deux fonctions mortes de l'exe (0x800280B8, 0x8002E7D0).
Limite : le jeu ne dessine que la piste devant le rider, des trous blancs peuvent apparaître au loin derrière.
`GsSetRefView2` (0x8002F830) n'est pas la caméra de course : il est appelé des dizaines de fois par image pour
d'autres rendus.
