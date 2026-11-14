# Remix modulaire : un interrupteur par mod, et un code de configuration

`remix/modular.py` découpe le Remix (v23) en 11 mods indépendants. Le site (onglet Patchs), `make_remix.py --config` et le
patcheur Batocera utilisent le même paquet (`remix/cb2remix_mods.json.gz`, 31 Ko) et donnent **le même fichier, à l'octet
près**.

| id | Mod | Ce que ça touche |
|---|---|---|
| `unlock` | Tout débloqué | INIT (valeurs de départ), MAIN_SEL 0x80063EA8 (riders sélectionnables avec une ancienne sauvegarde) |
| `special` | Planches SPECIAL partout | MAIN_SEL 0x8005B0C4 + lectures de 0x80057442 |
| `hardmirror` | Hard + Mirror | exe 0x8004F878–0x8004F89F, MODE_SEL (dont 0x800647DC : 3e ligne de la télé), étiquette « H+M L1+R1+X » dans `TITLE/MODE_SEL.FBD` |
| `riders` | Boss, Gray et Snowman en championnat (Snowman avec ses animations et son squelette, v29 : remix/snowtod.py ; voix de Gray et Snowman en Boarder Cross, v32 : remix/voices.py) | caves de l'exe, MAIN_SEL, SBC1/SBC2, ENEMY1, EFCT_SBC (plaques), LOCTBL, paquets de modèles, voix de Boss (fin du film d'intro coupée) |
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
  les secteurs du mod `riders` (le film est raccourci de 167 secteurs, avec les modèles du menu). Table de fichiers dans l'exe (MSF + taille),
  numéro de fichier = (entrée − 0x800583E8) / 8 (négatif). Secteurs : copies depuis PLAYER0.DAT / ENEMY1 / ENEMY2 ;
  seuls les octets recalculés du modèle (palette, page, u) sont écrits.
- Portraits : fiches profil de la vidéo `MOVIE/SBCMOVE.STR` (images 318, 344, 330), décodées par le patcheur
  (`mdec_decode`, MDEC version 2, entiers seulement : `disc.js` donne les mêmes octets), détourées, réduites à 64×64
  (affichées en 64×80), 94 couleurs + un contour sombre (fond blanc ou noir
  rempli depuis les bords, halo de compression rongé sur 2 pixels, points isolés retirés). Écrites dans `TITLE/MAIN_SEL.FBD`, zone que les écrans du menu n'utilisent pas
  (VRAM x 832..1023, y 320..383) : visages à x 832 / 864 / 896, palettes en x 928 lignes 320..322, noms (dessinés
  par le Remix, 48×32, 4 bits, palette des noms du jeu en 768,464) à x 960 / 972 / 984, y 352.
- Modèle 3D du menu : celui de la fin du jeu (ENDING/S_CHR/ED_CHR41/51/61.DAT : TMD de 16 parties = les 13 du menu,
  mains à part, planche en plus ; texture dans ENDING/ENDING.FBD, Jicchi x 512 palette 485, Nick 576/486, Kelly
  640/487). L'opération `crewmenu` du patcheur en fait un modèle de menu (mains jointes aux avant-bras, planche
  retirée, 3040 plus bas, texture placée dans la colonne du rider de base), déjà « mappé » pour 0x801C2000, avec sa
  texture (64x256, 8 bits) et sa palette : un fichier par rider (64 004 octets) à la fin du film d'intro.
  Dans le menu, 0x801C1E00..0x801EDD00 est libre (copie de MAIN_SEL.FBD déjà envoyée en VRAM). Les deux appels de
  `func_80064A08` (modèle du rider de l'écran BOARDER) passent par `mdl` : pour un alias, le fichier est demandé à
  la file de lecture du jeu (`func_80013C94` = mode données, `func_80013BD0` vers 0x801C2000), suivie chaque image
  (`func_80013CE0`, depuis l'habillage du portrait) ; une fois là (mot de fin), la colonne et la palette du rider de
  base sont sauvées (StoreImage 0x80029BE0, vers 0x801D2000), celles de l'alias envoyées (LoadImage 0x80029B7C) et le
  modèle est construit avec le pointeur de l'alias à la place de celui de la table 0x8007C4E8 ; en revenant à un
  autre rider, la sauvegarde est remise. L'écran WEAR n'envoie pas ses textures tant qu'un alias est affiché.
- Récompense des 100 % : `acomp` reprend la formule de la page de progression (0x80057440 bits 4..6, 0x80057442
  bits 0..2, 0x80057448/4A/4C = 0x3ff, 0x80057444 et 0x80057446 non nuls, 0x8005743C et 0x8005743E ≥ 10) ; `aval`
  et `amode` passent par elle, donc tant que le jeu n'est pas fini les trois alias restent gris dans la rangée de
  têtes et le curseur les saute. Avec `unlock` (mot 0x2403007F en 0x80063EA8), ils sont disponibles d'office.
  L'annonce (CONGRATULATIONS) est faite par le mod `news`.
- Voix : celles du rider de base, jouées plus graves ou plus aiguës. La fonction de son de l'exe `func_80015D18`
  (a0 hauteur, a1 voix SPU, a2 échantillon, a3 volume) passe par `vp` : en course (overlay 8), pour la voix 20
  (0x100000) à la hauteur normale 0x5CE, avec un alias pour ce rider de base dans un mode permis, la hauteur devient
  celle de l'alias (Jicchi −1,5, Nick −4, Kelly +3 demi-tons : 1363, 1179, 1767). Pas `aval` ici : son test du mod
  `unlock` lit MAIN_SEL, absent en course. Vérifié dans l'émulateur (appel forcé : 0x5CE avec Jin, 0x49B avec Nick).
- Classements (`remix/crewrank.py`) : les records gardent le numéro de l'alias (7, 8, 9) et les écrans RANKING montrent
  sa tête. La fonction de record de FREE (0x80089F34), HP (0x80089754) et OMT (0x80087450) copie le rider reçu dans un
  registre à son début : ce « addu sX, aY, zero » saute vers `rr`, qui met 6 + ALIAS quand l'alias est choisi pour ce
  rider de base dans un mode permis. Le dessin d'un record (même code dans FREE, HP, BP, OMT, MODE_SEL ×3, MAIN_SEL ×3) :
  icône 16 × 16 par une table de 7 mots (u, v, palette, sur la pile en sp + 0x38) et page de texture par une autre
  (sp + 0x58, 0x17 = VRAM (448, 256), pleine) ; pour 7..9, `ia` donne le mot d'une table à nous et `tb` la page 7
  (VRAM (448, 0), vide sur ces écrans) où les trois têtes (12 × 16) et leurs palettes (480, 0..2) sont envoyées par
  LoadImage à chaque dessin ; dans MAIN_SEL, les têtes de la rangée BOARDER déjà en VRAM (960, 324), page 0x1F. Le test
  « rider < 5 » (pas d'étiquette de planche pour Boss, Gray, Snowman) passe par `bc`, qui compte les alias comme 0..2.
  Les têtes viennent de TITLE/MAIN_SEL.FBD (opération `icons`), copiées dans chaque overlay par la nouvelle opération
  `fcopy` (octets d'un fichier tel qu'il est déjà modifié). Vérifié : record de half-pipe battu avec Kelly (octet 9,
  sa tête au classement), records forcés à 7/8/9 au classement d'avant course (MAIN_SEL) et de fin de half-pipe.
- 2 joueurs (mode 3, Free Style à deux, overlay VS) : l'écran BOARDER est le même qu'à un joueur, ouvert pour le
  joueur 1 puis pour le joueur 2 (manette 2) ; `func_80060200(a0, a1 = joueur)`, le joueur reste dans s6 jusqu'à la
  validation. ALIAS2 (0x8001FC98) est l'alias du joueur 2 : `cinit` prend le rider 0x80057412 et ALIAS2 quand a1 ≠ 0,
  `ccom` range ACUR dans ALIAS2 quand s6 ≠ 0. Hub à deux : noms du joueur 2 en 0x8005FFF0 / 0x80060080 (`nwH2`),
  changement rapide du joueur 2 en 0x8005FD48 (`navH2`). Course : `LoadRaceRiders` charge en VS le modèle VS/1P du
  joueur 1 (0x8001D3AC, case +0x10), le modèle VS/2P du joueur 2 (0x8001D3E8, +0x14) et sa texture (0x8001D644, +0x28) ;
  `ld` reconnaît la case et prend pour le joueur 2 une copie de modèle à lui (`remix/vs2p.py` : les fichiers VS/2P sont
  ceux de VS/1P avec chaque palette 7 lignes plus bas et u + 128, sauf les polygones de la page 8 à v < 64 : v + 64 ;
  vérifié identique sur les 5 modèles VS et 3 modèles FR du jeu), trois fichiers de plus à la fin du film d'intro
  (ENT3, IDX3). Stats : `vs_initRacers` (VS 0x80064DFC, rider dans s2, numéro du coureur en sp + 0x408 : 0 = joueur 1,
  1 = joueur 2) passe par `rpv`.
- Place dans l'exe : les blocs de code sont répartis dans les fonctions mortes ; `place()` refuse désormais une branche
  conditionnelle vers une autre zone (son décalage 16 bits serait tronqué : c'était le cas de `mdl`, `strip`, `nav`,
  qui ne marchaient que parce que leurs morceaux tombaient côte à côte). 25 petites fonctions mortes de plus (1 280
  octets), vérifiées contre tous les sauts, branches et pointeurs de tous les fichiers.
- Vérifié dans l'émulateur (2 manettes) : joueur 1 Jicchi, joueur 2 Nick (écran BOARDER « 2P », portraits, modèles
  3D du menu, hub « 1P JICCHI / 2P NICK »), course à deux avec les bons modèles et textures, et les paramètres de course
  de chacun (pointeur +0x54 des coureurs) ; Free Style à un joueur inchangé.
- Limites : animations et nom en course sont ceux du rider de base.
- Versus, vérifié dans le code (v28) : la seule « voix » d'une course est le grognement de collision du rider (canal
  0x100000 à 0x5CE, échantillons 0xD / 0xE de la banque de voix : FREE `func_80074768`, SBC2 `func_800746F4`) ; dans
  VS, un seul appel (`func_80073BF0`, collision entre les deux riders, un seul échantillon, sans joueur) : pas de voix
  propre au joueur 2 à transposer (`vp` applique celle de l'alias du joueur 1). Le relais `func_8007E62C` (VS) /
  `func_8007F134` (FREE) n'est appelé par personne. L'écran RESULTS du VS n'a ni noms ni têtes (« 1P / 2P » et scores).
- Vérifié : émulateur (verrouillé / 100 % / `unlock` sans progression), Free Style, Big Air, Halfpipe, Board Park ; crew seul et avec tous les mods) ; JS = Python ;
  patcheur Batocera = build Python.

## Vue arrière (`rear`, v26)

Code : `remix/rear.py` (opérations calculées par `generate()`). Les courses règlent leur caméra à chaque image par
`GsSetView2` (libgs, exe 0x80030984), qui écrit GsWSMATRIX (0x80058E20) ; la vue est relative au rider (l'origine
du monde est le rider). Rond maintenu (0x8004FBF0, bit 0x20) dans un overlay de course (mot 0 de l'overlay = 8, sauf
ENDING) : à la fin de `GsSetView2`, GsWSMATRIX et sa copie de travail (0x80059220) tournent de 180° autour de l'axe
vertical de la caméra passant par le rider (lignes X et Z opposées, v33) : la caméra passe devant le rider et regarde
derrière lui avec le même angle par rapport à la pente. La caméra de course suit la pente (0 à 5° sur le plat,
jusqu'à ~34° dans les descentes) ; la v26 tournait autour de la verticale du monde (colonnes opposées) : dans les
grandes descentes, la caméra devant le rider regardait encore vers le bas et ne montrait que la neige. Vérifié sur la
piste de la manche 2 (descentes, plat, porte de checkpoint visible derrière). Code dans deux fonctions mortes de l'exe
(0x800280B8, 0x8002E7D0).
Limite : le jeu ne dessine que la piste devant le rider, des trous blancs peuvent apparaître au loin derrière.
`GsSetRefView2` (0x8002F830) n'est pas la caméra de course : il est appelé des dizaines de fois par image pour
d'autres rendus.
- Rangée de têtes (v26) : en bas de l'écran BOARDER, 10 têtes 16x16 dans l'ordre de la liste (YAGGI JIN CINDY IRIN
  JICCHI NICK KELLY BOSS GRAY SNOWMAN), celle du curseur plus grande, celles des riders non disponibles en gris
  (bits de 0x80057440, ou tous si le mot du mod `unlock` est là ; Jicchi/Nick/Kelly selon le mode), en 2 rangées de 5
  sous le titre BOARDER. Têtes faites par
  le patcheur à partir des portraits du menu (opération `icons`, 4 bits, VRAM x 960 y 324, palettes x 928 lignes
  340..343) ; dix POLY_FT4 écrits par `strip` et chaînés juste après le nom tagué (le menu dessine avec l'origine au
  centre de l'écran : +160, +120).

## Annonces de déblocage (`news`, v26)

Code et données : `remix/news.py`.

- La boucle principale de l'exe (0x80012260…) charge chaque overlay puis appelle `func_8001B668`, l'entrée de
  l'overlay, `func_8001B718`. Ces deux appels deviennent `npre` / `npost` (exe, fonctions mortes 0x8001E630 et
  suivante, état sur 32 octets : VALID, MASK, CNT, SNAP) :
  - `npost` : en quittant un menu (mot 0 de l'overlay : 5 = MODE_SEL, 6 = MAIN_SEL), SNAP = les mots de progression
    0x8005743C..0x8005744F (ceux de la carte mémoire), VALID = 1 ;
  - `npre` : en entrant dans un menu, ce qui est apparu depuis SNAP (bits passés de 0 à 1) s'ajoute à MASK :
    0x7440 bits 4..6 (Boss, Gray, Snowman), 0x7442 bits 0..2 (planches SPECIAL), 0x7444 / 0x7446 (Mirror, Hard),
    0x743C / 0x743E en hausse (pistes), 0x7448 / 4A / 4C (trophées).
  Ce qui se passe pendant les courses (overlays 8) est donc annoncé ; une carte mémoire chargée dans un menu ne
  l'est pas (SNAP est pris en quittant le menu). Au démarrage, VALID = 0 : rien jusqu'à la première sortie de menu.
- Affichage : le hub de MAIN_SEL (BOARDER / COURSE / BOARD / OPTIONS / START), où l'on revient par SELECT après une
  course (EXIT passe par le titre et MODE_SEL : l'annonce attend le hub). Son appel par image de `func_8005BFD0`
  (0x8005B280) devient `nhub` (fonctions mortes de MAIN_SEL : 0x8007586C, 0x80079F3C, 0x80075118 ; table et textes
  en 0x80077E2C et 0x80078F54). Une ligne par élément, texte du jeu (`func_8005E784`), couleur des lettres qui pulse
  de l'or au blanc (32 images), cadre sombre (TILE) placé comme dans `crew` (la dernière lettre est déplacée),
  pendant 210 images du hub (7 s), puis MASK = 0. Si la progression atteint 100 % (`ncomp`, formule de
  `remix/progress.py`) : CONGRATULATIONS, puis JICCHI NICK KELLY UNLOCKED si `crew` est là (sa table BASE en
  0x8001FBD4), sinon GAME COMPLETED.
- Vérifié : émulateur (Snowman + trophée simulés pendant une course puis SELECT ; tout à 100 % : 11 lignes ;
  premier passage au hub sans annonce) ; JS = Python.

## Notes du half-pipe en direct (`hplive`, v26)

Code : `remix/hplive.py` (HP.BIN seulement).

- Le score du half-pipe vient d'accumulateurs du run (D_8009AC48..D_8009AC6B) changés en cinq notes de 0 à 100 dixièmes
  par `func_8006A81C` (total, pour le classement et le test de Gray ≥ 37,6) et `func_8006A5C4` (panneau de fin) :
  figures = AC5C / 20, amplitude = AC62 / 8, rotation = (min(AC5E, 7000) + AC60) / 95, réception = min(AC48 × 10, 100) −
  AC64, mérite technique = min(somme / 4, 100) − 3 (AC68 + AC69 + AC6A + AC6B), chacune bornée à 0..100.
- Le panneau dessine une ligne par `func_80086E50` (OT, prim, ligne, note, x, y) et le total par `func_800871B8`
  (OT, prim, total, x + 16, y) ; entrée d'OT = *(*(D_8009BE4C) + 4) + 0xC, primitives en D_80058E0C, page de texture
  du panneau (4 bits, x 320, y 0) posée par un DR_MODE chaîné en dernier.
- La boucle principale du run (`func_8005BFF0`) appelle `func_800757EC` à chaque image (0x8005C2FC) : l'appel passe par
  `hpj` (fonction morte `func_8006AFFC`), qui calcule les cinq notes comme le jeu (sans réécrire AC5E), dessine les
  lignes en haut à droite (x 112, y 28, tous les 12 px), le total, un cadre sombre semi-transparent (TILE 0x62, mode
  de mélange du panneau) et le DR_MODE.
- Vérifié dans l'émulateur : le total monte pendant le run (0 → 1,0 → 2,1 → 3,3 → 5,0 → 6,2) et les cinq notes de la
  fin du run sont celles de l'écran de fin (0,4 / 1,4 / 4,4 / 0,0 / 0,0 ; 6,2).

## Options dans le jeu (`options`, v26)

v37 : le panneau (R1 maintenu) devient un écran REMIX, dans le style de l'écran OPTIONS du jeu : entrée « REMIX » sous
le panneau OPTIONS de l'écran des modes (Bas depuis OPTIONS = curseur 5 du jeu, 0x80070B2C ; Haut pour revenir ; X
ouvre), fond noir, titre en haut à gauche, trois onglets RACE / RIDERS / GAME (Gauche / Droite), Haut / Bas, X bascule,
Triangle ou Rond revient. L'entrée de la manette : la routine de MODE_SEL `func_8005CCE4` (appelée en 0x8005CB94) passe
par `pw`, qui garde les mots de la manette (0x800832BA..C5) et les vide tant que REMIX a la main (le menu du jeu ne
bouge pas). `pw` n'agit que si l'écran des modes est dessiné (compteur `alive` remis à 2 par `opt` à chaque image) :
l'écran OPTIONS du jeu n'est pas touché. MODE_SEL grandit d'un secteur (84, toggles.SCREEN : données et code de
l'écran ; son tas commence 0x800 plus loin).

Code : `remix/options.py` (MODE_SEL + six fonctions mortes de l'exe réservées) ; tests dans `rear.py`, `hplive.py`,
`news.py`.

- Les interrupteurs sont des bits de 0x80057438 (bit à 1 = coupé) : 1 vue arrière, 2 notes du half-pipe en direct,
  4 annonces de déblocage, 8 figures en l'air (`air`), 16 chocs en Boarder Cross (`ramming`), 32 écran large (à 1 =
  actif : coupé par défaut), 64 ligne du radar (`radar`), 128 classement (`radar`), puis les autres mods (section
  suivante) et UNLOCK EVERYTHING (bit 18 depuis la v36 ; 17 = FALLS AS A NUMBER) : le mot 0x80057438 entier. Cet octet fait partie
  du bloc 0x80057434..0x8005744D copié dans la sauvegarde mais n'est jamais lu par le jeu (docs/progression.md) : le
  réglage suit la carte mémoire. À 0, tout est actif comme avant.
- `rear`, `hplive`, `news` lisent leur bit. `air` et `ramming` sont coupés là où leur code vit, dans l'exe (toujours
  en mémoire) : à chaque image de l'écran de choix du mode, `oap` donne aux mots de PATCH leur valeur « actif » ou
  « coupé » (air : les branches de md 0x8004FA44, ax 0x8004FAC8, rm 0x8004FB28 rendues inconditionnelles ; ramming :
  l'entrée de `kc` 0x80028BF4 devient un saut vers la réponse de collision du jeu), seulement si le mot vaut déjà l'une
  des deux valeurs (mod absent : rien n'est touché), puis FlushCache.
- Écran large : l'échelle X de la matrice 0x80059288 (identité recopiée par l'init libgs `func_8002DE88`, puis
  seulement lue par les fonctions de vue) passe de 0x1000 à 0xC00 : le jeu calcule lui-même un champ 16:9, à afficher
  étiré en 16:9 (sans le « widescreen hack » de l'émulateur). Valeur reprise du code DuckStation de PeterDelta pour ce
  disque (SCES-00992 : A7059288 10000C00, github.com/PeterDelta/PCSX2). Vérifié : course de Free Style en 16:9.
- UNLOCK EVERYTHING (dernière ligne, bit 256 = fait, affiché ON) : une action, pas un interrupteur. Premier R2 : mot
  `conf` à 1, trois lignes d'avertissement sous le panneau (`owr`) ; second R2 (`ounl`, dans l'exe) : le bloc de
  progression reçoit les valeurs d'une partie à 100 % (0x743C/0x743E = 10, 0x7440 |= 0x7F, 0x7442 |= 7,
  0x7444/0x7446 = 1, 0x7448/0x744A/0x744C = 0x3FF), bit 256 mis, `conf` remis à 0. Bouger le curseur annule
  l'avertissement. La sauvegarde garde le tout (pas de retour arrière). Sert à essayer tous les modes et toutes les
  options d'un coup ; débloque aussi Jicchi, Nick et Kelly (porte 100 % de `crew`).
- Tampon de primitives du panneau : 0x801F8000 + 0x2000 par image (0x801F0000..0x801FF000 n'est pas touché sur cet
  écran). À 0x800 il débordait sur celui de l'autre image (3 images sur 60) ; à 0x1000, l'avertissement (0xB9C
  octets sans lui, plus de 0x1000 avec) figeait le jeu.
- Écran de choix du mode : l'appel de `func_80028BDC` en 0x800643E4 (fonction de la télé, chaque image) passe par
  `opt`. R1 maintenu : panneau REMIX OPTIONS (texte du jeu `func_80012CA0`, cadre sombre) ; L1 descend le curseur
  (ligne dorée), R2 bascule la ligne.
- Vérifié dans l'émulateur : curseur et bascules ; mots de l'exe changés et remis (air, ramming) ; course de Free
  Style avec air et ramming coupés ; notes du half-pipe absentes avec le bit 2 ; vue arrière normale avec le bit 1 ;
  annonce non lancée avec le bit 4. Pas encore vérifié : l'octet relu après un vrai enregistrement puis chargement de
  la carte.

## Tous les mods réglables dans le jeu (`options` + `remix/toggles.py`, v28)

- Le panneau REMIX OPTIONS a 18 lignes (10 visibles, la liste défile avec le curseur) ; ligne i = bit i du mot
  0x80057438 (32 bits : 0x80057438..0x8005743B sont sauvegardés et jamais lus par le jeu). Bits 0..7 : vue arrière,
  notes du half-pipe, annonces, figures en l'air, chocs, 16:9, ligne du radar, classement ; 8..16 : `special`,
  `hardmirror`, `riders`, `outfits`, `max`, `bam`, `progress`, `skipq`, `crew` ; 17 : FALLS AS A NUMBER (v36) ; 18 : UNLOCK EVERYTHING (fait).
- Les « sites » de chaque mod (`remix/toggle_sites.py`, 232 mots) : les mots du jeu qu'il change et que le jeu atteint
  (instructions remplacées, données), pas son code dans des fonctions mortes (que plus rien n'atteint une fois les
  sites remis). Trouvés une fois depuis le désassemblage (fonction morte = aucun appel, saut ni pointeur dans aucun
  fichier ; plus les zones que les mods déclarent). Exclus : les débuts de tas de MAIN_SEL / MODE_SEL (0x8001003C,
  0x800100B8, 0x800100B4 : ces fichiers ont grandi) et l'appel de l'overlay 0x8001228C (déjà pris par `max`, chaîné).
- La table (groupe par mod et par fichier : bit, sorte, nombre, adresse et mot témoins ; entrées : index du mot,
  mot d'origine, et pour l'exe le mot modifié) et la routine `tap` sont à la fin de MODE_SEL, qui grandit d'un
  secteur de plus (`padto` à 83 secteurs d'abord : même adresse avec ou sans la page de progression ; son tas commence
  ensuite, mot 0x800100B4 écrit tel quel). À chaque image de l'écran des modes, `tins` (code des options) copie le
  bloc en 0x801F2000 (RAM libre dans toutes les scènes : vérifié avec un motif à travers les menus, le Free Style, le
  2 joueurs, le half-pipe et la Compétition ; la page de progression dessine donc maintenant en 0x801F4000 / 6000) et
  remplace, dans l'exe en mémoire seulement, l'appel de l'overlay de la boucle principale (0x8001228C) par `jal tap`,
  après avoir gardé l'appel qui y était (celui du jeu, ou celui de `max`) en 0x801F3FFC.
- `tap`, à chaque scène avant l'overlay : groupe d'un overlay, mod coupé, et l'overlay qui vient d'être chargé a
  encore le mot modifié au premier site (il arrive modifié du disque) → mots d'origine remis ; groupe de l'exe, si le
  mod est sur le disque (un mot de son propre code est là) → chaque site reçoit son mot modifié ou d'origine selon
  l'interrupteur ; puis FlushCache et l'appel gardé (ou l'overlay directement si `max` est coupé). Un mod coupé prend
  donc effet en quittant l'écran des modes.
- Restent en place même coupés (sans effet sur le jeu) : les fichiers ajoutés (modèles, voix, textures), les
  couleurs et plaques de nom échangées Boss / Jicchi de `riders` dans ENEMY1 / EFCT_SBC, l'indice de la télé de
  `hardmirror`, le code des mods dans les fonctions mortes.
- Vérifié dans l'émulateur : défilement ; MAX coupé (MAIN_SEL : les 33 mots d'origine, plus de « R1 : MAX ») ;
  SPECIAL, riders et Jicchi/Nick/Kelly coupés (mots de l'exe et de MAIN_SEL d'origine, écran BOARDER du jeu, course
  du Free Style) ; remis (mots modifiés) ; page de progression.

## Classement et radar de course (`radar`, v27)

Code : `remix/radar.py` (SBC2.BIN, deux fonctions mortes : code dans `func_8007D614`, données dans `func_8007BEB8`).

- Boules des chutes (v35) : la rangée de boules du bas à gauche (sprites 8 × 8 du modèle n° 8 de D_8009ABE0, dessinés
  par `func_80078E58`, appelée en 0x8006D12C avec x -0x98, y 0x68) passait sous la ligne. Avec la ligne active,
  `rfall` (dans `func_8007BEB8`, après les données) leur donne y -0x7C : en haut à gauche, à la place de la barre
  d'origine, au-dessus de TIME. Ligne coupée : à leur place d'origine. Trouvé en neutralisant une à une, en mémoire,
  les fonctions qui utilisent ces modèles.
- Les boules comptent le champ rider + 0xCDE (`func_8006D0C0` le passe en a3) : une grosse boule par dizaine, une
  petite par unité. v36 : option FALLS AS A NUMBER (bit 17 des options ; UNLOCK EVERYTHING passe au bit 18) : une seule
  boule et « x13 » dans la police du HUD de SBC2 (`func_8008AFC8`). `rfall` garde HI et LO (le `mult` de l'appelant est
  en cours pendant l'appel : `mfhi` / `mthi`, `mflo` / `mtlo`).

- La barre de progression du Boarder Cross de la Compétition (en haut à gauche, S … F) est dessinée par
  `func_8006D2A4` de SBC2 (appelée en 0x8005F56C avec le tableau des coureurs D_8009146C, 8 × 0x1288 octets) :
  bande translucide (TILE 0x62, x -0x90, y -0x78, 0x70 × 0xD, rectangle en sp + 0x18), puis par coureur un carré 4×4
  à x = -0x90 + (0x70 - 4) × `func_8007E4B0`(piste, coureur + 0) / 255, y = -0x78 + 1 + place, couleur de la table
  D_8008DD88 (rouge, vert, bleu, jaune, magenta, cyan, blanc, noir) selon la place (coureur + 3), chaque carré dans
  sa propre entrée de l'ordering table (3, 4, …, les plus basses dessinées en dernier), celui du joueur clignotant
  (sp + 0x70) ; enfin la bande et les lettres S et F. Coureur + 0x58 = place dans la course (1 à 8).
- Places de l'effectif de la Compétition : YAGGI JIN CINDY IRIN JICCHI NICK KELLY BOSS ; le joueur a la place
  `g_rider` (Boss, Gray ou Snowman joueur remplacent Jicchi, Nick ou Kelly).
- Crochet : 0x8006D410 (« addu s3, zero, zero », début de la boucle) → `rad`. Option coupée (bit 64 de 0x80057438) :
  retour à la boucle d'origine. Sinon : la bande devient une longue ligne sombre en bas de l'écran (x -0x8C, y 112,
  0x110 × 6 ; la place et la vitesse finissent en y 108, l'écran en 123 ; S et F suivent ses bouts ; son gris vient de
  sp + 0x7C, mot libre du cadre de pile, lu en 0x8006D58C à la place du 0xFF d'origine, 0xFF option coupée), les dix
  têtes de la rangée du menu BOARDER (YAGGI JIN CINDY IRIN JICCHI NICK KELLY BOSS GRAY SNOWMAN, faites par les
  opérations `face` et `icons` du mod crew dans TITLE/MAIN_SEL.FBD, recopiées ici par `fcopy` ; le mod les répète
  pour marcher seul) envoyées à chaque image par LoadImage en VRAM (768, 472) (4 bits) et leurs palettes en
  (768.., 490) : zone vide pendant la course, vérifiée sur les 8 pistes de la Compétition. Par coureur : SPRT 16×16
  (ordinateur : tête de sa place ; joueur : tête de `g_rider`, ou de l'alias du mod crew s'il est choisi pour ce
  mode, même test que la voix) posé sur la ligne en y 107, le joueur entouré d'un contour jaune qui clignote comme le carré d'origine, et un DR_TPAGE
  de la page des têtes en tête de chaque entrée (le texte du HUD, S et F compris, change la page dans les mêmes
  entrées). Retour en 0x8006D540 avec s2 (primitives) et s6 (entrée suivante) comme la boucle les laisse.
- Classement (bit 128 coupé), dessiné par `rank` avant la ligne, dans l'entrée 3 de l'ordering table comme le texte
  du HUD : trois rangées (la place devant le joueur, la sienne, celle derrière ; 1er à 3e quand il mène, 6e à 8e quand
  il est dernier ; place = coureur + 0x58) en x 76, y -24, 18 pixels d'écart : la place (« 1ST »…, texte de SBC2
  `func_8008AFC8` avec la police D_8009BBC0, couleur par `func_8008B354` : or, argent, bronze, blanc, qui scintille avec
  VSync(-1)), la tête (contour jaune pour le joueur) et l'écart avec le joueur en secondes (« -1.2 » devant, « +0.8 » derrière,
  rien sur sa rangée, « -- » sans mesure), sur
  un cadre sombre translucide (TILE 0x62 précédé d'une page en mode moitié-moitié). Le texte prend ses primitives à
  D_80058E0C, que la fonction de la barre garde dans s2 et réécrit à la fin : `rtext` les synchronise autour de
  l'appel (sans ça, les deux se recouvraient et le jeu se figeait). Mots libres du cadre de pile pendant `rad` : 0x24,
  0x2C, 0x5C, 0x64, 0x6C, 0x74 (0x7C : gris de la ligne). Ligne coupée (bit 64) : retour à la boucle d'origine avec
  ses registres (s1 = primitive + 0xA, a2 = 0xFF000000, s7 = 0xFFFFFF) ; les deux coupés : rien n'est changé.
- Écarts, chronométrés par portes : coureur + 0 est le segment de la piste (un peu moins d'une seconde chacun) ;
  `rgate` note pour chaque coureur le compteur de VSync (16 bits) à son entrée dans chaque segment, dans un anneau de
  32 mots ((segment + 1) << 16 | compte) par coureur, dans deux fonctions mortes de SBC2 utilisées comme RAM
  (0x8006C488 : coureurs 0 à 3, 0x80074F48 : 4 à 7), vidées quand le panneau n'a pas été dessiné depuis 30 images
  (nouvelle course, recommencer). Devant : (entrée du joueur dans son segment) - (entrée de l'autre dans ce segment) ;
  derrière : (entrée de l'autre dans son segment) - (entrée du joueur dans ce segment) ; en 1/50 s, affiché en
  dixièmes. Précis à l'image, mis à jour à chaque porte, comme les temps intermédiaires d'une vraie course.
- Première version en haut à gauche (barre plus haute, deux rangées) : têtes trop serrées sur 112 pixels ; la ligne du
  bas en fait 272.
- Vérifié dans l'émulateur : têtes et contour en course, option coupée (barre et carrés d'origine en haut), alias
  (tête de Jicchi pour le joueur), zone de VRAM vide sur les 8 pistes. COMB.BIN a une barre du même genre à 2 coureurs
  (`func_8006C884`), pas modifiée.

## Boost de figures (`radar`, v43 : `remix/boost.py`)

À la SSX / Speed Freaks, dans le Boarder Cross de la Compétition. Ligne SSX STYLE BOOST de l'onglet RACE de l'écran
REMIX (bit 19 des options, actif par défaut ; le tableau des onglets passe à 16 octets par onglet, RACE en a 9).

- **Jauge** (0..480) : en l'air (rider + 0x3E ≠ 0), +1 par image de jeu (25 / s), +2 tant qu'une figure joue
  (mouvement + 0x6C4 ≠ 47, le saut simple), +1 tant qu'une touche de figure est tenue (L1 L2 R1 Triangle Rond Carré) ;
  ces points restent « en attente » (en blanc translucide dans la barre) et ne comptent qu'à une réception propre
  (10 images sans chute, + 0x740), avec 25 de bonus après 15 images en l'air ; une chute les perd. Exemple mesuré :
  un saut avec grab de 17 images = 41 + 25.
- **R2 au sol** (jauge > 0, pas de chute) : la vitesse du rider (+ 0x48F0, trois mots, environ 400 × son déplacement par
  image) augmente de 1/32 à chaque image tant que le déplacement reste sous 310 (vitesse de pointe normale ~ 230) :
  une vraie accélération, que la caméra suit (v43..v47 ajoutaient la moitié du déplacement à la position après la
  physique : la caméra le montrait par à-coups). Jauge − 4 par image (une jauge pleine = 120 images, 4,8 s).
  Mesuré (v48) : +35 % de distance sur 120 images, montée de 220 à ~315 par image en une seconde, compteur 123 km/h.
- **Barre** sous les temps (x −140, y −54, 80 × 6, entrée 4 de la table d'ordre) : bord clair, fond noir, jauge à la
  couleur du rider (table par `g_rider`), traits aux quarts ; pleine, elle clignote en blanc ; elle flashe à chaque gain.
- **Traînée** (entrée 12, avant le HUD) : les 8 dernières positions projetées par la vue (GsWSMATRIX 0x80058E20,
  translation 0x80058E34 : le rider est l'origine du monde, mêmes unités que la position ; sx = x · H / z, H = caméra
  + 0xA) ; un ruban translucide (moitié-moitié, DR_TPAGE) qui s'affine en s'éloignant du rider, un cœur plus clair,
  coupé à z = 60. Avec la caméra de poursuite, il part de la planche vers le bas de l'écran (la trace est entre le
  rider et la caméra) ; en vue arrière il s'étire derrière. Plus 10 traits de vitesse (POLY_F3) qui partent du rider.
- Une avance de plus de 4000 en une image (nouvelle course, recommencer) remet tout à zéro.

Où : le code (3,4 Ko) tourne en RAM statique (0x801F3100, au-dessus de l'aide de snowtod ; ses variables en 0x801F3F40,
sous B_PTR). SBC1 l'installe à chaque démarrage (l'appel de func_8001BFD4 en 0x8005AEC0 passe par `bins`, rangé
avec l'image dans quatre fonctions mortes de SBC1 : func_8007E4D8, func_80073F20, func_8005EF1C, func_8006FAD8) :
la 1re épreuve passe toujours avant le Boarder Cross. SBC2 : l'appel de la fonction des chutes (0x8005F33C, une fois
par image, après la physique) passe par `btr` (fin de la fonction morte de données du radar) : `bmain` si l'image
est là (mot MAGIC), sinon la fonction d'origine ; `bmain` garde a0..a3 et finit par elle.

v45 : l'entrée REMIX sous le panneau OPTIONS et le titre de l'écran REMIX sont le REMIX de l'écran titre (`title.word` :
Noto Sans Black Italic, dégradé doré, contour, penché), en petit (taille 16 → 60 × 25), calculé à la construction en
16 couleurs, envoyé chaque image dans la VRAM libre de l'écran des modes (x 448, y 0 ; palette en y 64) et dessiné en
SPRT avec son DR_TPAGE (`dlogo`) ; atténué quand le curseur est ailleurs, il pulse quand le curseur est dessus.

v46 : dans l'écran REMIX, « TRIANGLE BACK » devient un triangle dessiné (deux POLY_F3 : contour vert façon bouton PlayStation, `dtri`, la police du menu n'a pas ce signe) suivi de BACK, et REAR VIEW (CIRCLE) devient REAR VIEW (O).

v47 : l'aide de l'écran REMIX montre des flèches gauche / droite dessinées (deux POLY_F3 de plus dans `dtri`) à la place de « L R » : les onglets se changent avec la croix.
