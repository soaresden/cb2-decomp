# Rider en course : ce qu'on sait

Notes rassemblées pendant le Remix (tests dans l'émulateur et accroches du code). À compléter au fil de la décompilation ;
chaque ligne dit d'où vient l'information.

## Structure d'un rider (overlays de course)

Les riders d'une course sont rangés les uns après les autres, tous les **0x4BE0 octets** (test Boarder Cross : joueur à
0x8012BD30, premier adversaire à 0x8012BD30 + 0x4BE0 ; adresses en RAM pendant une partie, pas dans les fichiers).

| Offset | Taille | Sens | Source |
|---|---|---|---|
| +0x002C | 3 × s32 | position (x, y, z) | téléportation dans l'émulateur |
| +0x0084, +0x0134, +0x4A74, +0x00DC | 3 × s32 | positions précédentes : à recopier avec +0x2C pour déplacer un rider sans qu'il tombe | idem |
| +0x06C0 | u32 | animation en cours | test des chutes |
| +0x0734, +0x0738 | u32 | états (en l'air, chute…) ; le Remix ne fait pas chuter un rider dont +0x738 ou +0x740 est déjà non nul | `kc` du Remix |
| +0x0740 | s16 | compte à rebours de chute (« stumble ») ; 2 = chute comme après un choc contre un mur | `kc` du Remix |
| +0x0744 | s32 | rotation flip « chargée » | `ax` du Remix |
| +0x0748 | s32 | rotation spin « chargée » | `ax` du Remix |
| +0x07A4 | s32 | vitesse de rotation spin | `<overlay>_playerAirControl` |
| +0x07A8 | s32 | vitesse de rotation flip | idem |
| +0x07B0 | s16 | vitesse | test des chutes |

## Variables globales (exécutable)

Voir `config/symbols.main.txt` : rider choisi (`g_rider`), veste, tenue cachée, miroir, déblocages, table des fichiers,
boutons de la manette (`g_padButtons`, bits actifs : 0x10 Triangle, 0x20 Rond, 0x40 Croix, 0x80 Carré, 0x1 L2, 0x2 R2,
0x4 L1, 0x8 R1, 0x1000 Haut, 0x2000 Droite, 0x4000 Bas, 0x8000 Gauche).

## Fonctions repérées

| Fonction | Rôle |
|---|---|
| `ReadPads` (exe) | lecture des manettes, copie des boutons du port 0 |
| `LoadRaceRiders` (exe) | charge modèle, texture, paquet basse définition et variante ENEMY1 de chaque rider |
| `<overlay>_initRacers` | prépare les riders d'une course, dont le pointeur vers les paramètres du rider (stats) |
| `<overlay>_playerAirControl` | figures en l'air : spin et flip |
| `sbc2_racerCollisions` | Boarder Cross : collisions entre riders, appelle `sbc2_racerBumpResponse` pour chaque rider d'une paire |
| `sbc2_racerBumpResponse` | réaction d'un rider à un choc ; a1 / a2 = vecteurs de déplacement des deux riders |
| `sbc2_loadRacerModels`, `sbc2_loadRacerTextures`, `sbc2_loadVoiceBanks` | chargement des riders et de leurs voix en Boarder Cross |

## Pièges connus (assembleur)

- Les zones libres réutilisées par le Remix commencent parfois juste après un *delay slot* (0x8002A02C, 0x80028BF0).
- *Load delay* MIPS : une valeur lue par `lw` n'est utilisable qu'une instruction plus tard.
- t0 / t1 sont souvent encore utilisés par l'appelant (boucle des barres de stats de MAIN_SEL).

## Riders du joueur et riders de l'ordinateur (test sur le jeu d'origine, v25)

- `g_rider` (0x80057408) du joueur : 0 Yaggi, 1 Jin, 2 Cindy, 3 Irin, 4 Boss, 5 Gray, 6 Snowman. Forcé à 7 avant une
  course de Free Style, rien ne se charge (retour au classement) : **Jicchi, Nick et Kelly n'ont pas de place de joueur**.
- Modèles du joueur (`DATA/CHR/FR/1P` et `2P`) : 4 corps (FRM1, FRM2, FRFM1, FRFM2) + BOSS, GRAY, SNOW, et une texture
  par veste / pantalon dans `FR/FBD*` (FRMx_jp.FBD, 17 428 octets).
- Riders de l'ordinateur (Compétition, ordre YAGGI JIN CINDY IRIN JICCHI NICK KELLY BOSS) : modèles basse définition
  dans `PLAYER0.DAT` / `PLAYER1.DAT` (paquets de 8), textures en colonnes de 32 pixels dans `ENEMY1.FBD`.
- Les rendre jouables demande : une place dans la liste de l'écran BOARDER (nom, portrait, stats), des numéros de rider
  au-delà de 6 acceptés par les tables indexées par rider (stats, animations, voix, plaques de nom…), et un modèle +
  une texture de joueur (le modèle basse définition de l'ordinateur, ou un corps FRM/FRFM avec sa texture agrandie).

### Fichiers du rider du joueur (Free Style et modes à un joueur) — `func_8001D1B8` (exe)

- Arguments : contexte, structure du menu (0x80057408 : +0 rider, +4 veste, +6 pantalon, +0xA / +0xE / +0x10 joueur 2).
- Modèle : table 0x80011158 = numéros de fichiers 156..162 (FR/1P FRM1, FRM2, FRFM1, FRFM2, BOSS, GRAY, SNOW), indexée par
  le rider (copiée sur la pile : 7 entrées seulement, un rider 7 lirait n'importe quoi) ; 0x80011174 = 170..174 (VS/1P).
- Texture : fichier 180 + rider × 9 + veste × 3 + pantalon (FR/FBD FRM1_00..FRM2_22, FR/FBD2 FRFM1/2) ; Boss, Gray et
  Snowman (FR/FBD3 BOSS0/1, GRAY0/1, SNOW0/1) passent par un autre chemin.
- Table des fichiers de l'INIT (0x8005F6C8, 323 chemins) : 140..143 PLAYER0..3.DAT, 144 ENEMY1.FBD, 156..169 FR/1P et
  FR/2P (*.PMD), 170..179 VS/1P et VS/2P, 180..227 textures FR, 228 BOARD.DAT, 229..236 TOD_MAN0..7, 237 TOD_SM.
- Une texture de joueur (FR/FBD, 17 428 octets = 20 + 2 lignes de CLUT + 128 × 256 en 4 bits) a la même taille qu'une
  colonne de rider de l'ordinateur dans ENEMY1.FBD : la texture de Jicchi / Nick / Kelly peut servir telle quelle.

### Riders de l'ordinateur convertis en joueur (`remix/cpurider.py`, v25 — essai)

- `PLAYERk.DAT` (k = 0..3) : 8 modèles, un par place de la Compétition (YAGGI JIN CINDY IRIN JICCHI NICK KELLY BOSS) ;
  place k = modèle détaillé du joueur k, les autres = modèles simplifiés des adversaires.
- Textures des adversaires : place 0-1 page 8, 2-3 page 9 (ENEMY1, x 512..639), 4-5 page 6 (ENEMY2.FBD, x 384..447),
  6-7 page 7 (ENEMY1, x 448..511) ; moitié gauche (u 0..127) pour les places paires, droite pour les impaires ;
  palettes 493/494, 495/496, 497/498, 499/500, 503/504 (Jicchi), 505/506 (Nick), 507/508 (Kelly), 501/502.
- Conversion : page → 9, u − 128 pour une moitié droite, palettes → 493/494 ; texture = 2 lignes de palette + la
  colonne de 128 × 256, au format de FR/FBD/FRM1_00.FBD. Essai : Jicchi à la place du modèle et des textures de Yaggi
  roule normalement en Free Style avec les animations de Yaggi (capture dans l'émulateur).

### Jicchi, Nick et Kelly jouables (mod `crew`, v26)

Fait en « alias » d'un rider existant (voir `docs/modular.md`) : l'écran BOARDER les propose après Irin, la course
charge leur modèle et leur texture (fichiers ajoutés) et leurs paramètres de course de la Compétition (SBC2
0x8008F1F8, 16 octets par place : Jicchi 4, Nick 5, Kelly 6). Le second chargeur de fichiers du joueur,
`func_8001D694` (Halfpipe, Big Air…), range la texture en +0x20 du contexte (au lieu de +0x24 pour `func_8001D1B8`).

## Snowman en Compétition (corrigé en v29, `remix/snowtod.py`, mod `riders`)

- Symptôme : en Compétition (mod `riders`), Snowman est « mal assemblé » et penché ; en Free Style il est bon.
- Modèle : SNOW.PMD (7 objets, contre 12 pour un humain), mis par `riders` à la place 6 du paquet PLAYER.
  Chaque objet a son GsCOORDINATE2 (0x50 octets, `super` = 0) et un bloc d'animation propre au jeu (pointeur `param`,
  rotation de type quaternion en unités de 4096) ; Free Style : les 7 objets de Snowman ont des rotations nulles et
  leurs positions dans le repère du rider (0x8009E2CC…, objets 0x18 octets : attribut, coord, pmd, objet, base, n°) :
  (-47,-762,-10) (-92,-821,-116) (0,-1326,46) (1,-2088,18) (-19,-491,83, échelle 696) (277,-1474,55) (-224,-1445,33).
- Animations : fichiers TOD (format libgs) — TOD_MAN0..7 (fichiers 229..236, humains, ~377 Ko) et TOD_SM (237, Snowman,
  82 Ko). Le Free Style charge les deux (`LoadRaceRiders` : TOD_MANx tiré au hasard dans une table par rider
  D_80010CE4, puis TOD_SM) et anime Snowman avec TOD_SM. La Compétition (`func_8001CE..`, appel 0x8001D05C) ne charge
  qu'un TOD_MANx, dans un tampon commun (0x80195394, pointeur en +0x14 du contexte) : les 7 objets de Snowman reçoivent
  les 7 premiers os d'un humain (posture penchée, morceaux décalés).
- Essai : charger TOD_SM à la place pour Snowman (0x8001D05C → petite fonction) bloque l'écran d'étape : le même TOD
  sert aussi aux adversaires simulés, et TOD_SM n'a pas leurs mouvements. Piste : un second tampon (82 Ko) pour le
  joueur et son pointeur d'animation dirigé dessus, ou un TOD_SM réduit aux mouvements utiles.
- v27 (`remix/snowtod.py`, pas encore actif) :
  - Place : le tas de l'exe (`func_8001F270` = réserve, `func_8001F448` = libère ; blocs à en-tête de 16 octets :
    précédent, suivant, taille, occupé ; tête D_800592BC ; un tas par overlay) a ~200 Ko libres pendant le Boarder
    Cross (bloc libre de 0x80162C90 jusqu'au tampon des TOD humains). Le chargeur de la Compétition `func_8001CCE0`
    met ses fichiers en file avec `func_80013BD0(fichier, dest, &ptr, drapeaux)` (dest 0 = dans le tas) : son appel
    en 0x8001D014 peut aussi mettre TOD_SM (fichier 237) en file quand g_rider = 6 → chargé à chaque épreuve.
    (La fonction « morte » 0x80025820 est le gestionnaire d'interruptions écrit à la main, installé par adresse :
    la toucher empêche le jeu de démarrer ; 0x8001FA98 a un point d'entrée 0x8001FAAC appelé par les overlays.)
  - TOD en mémoire : « TO », 0, nombre de mouvements (100 humains, 46 Snowman), puis leurs adresses. Le fichier a
    « TO2 » et des décalages en mots : chaque overlay les convertit (FREE : `func_8008F878` pour l'en-tête, puis
    `func_80095F98` pour chaque mouvement : décalages + adresse du mouvement, octet 1 de 2 à 0xFE) ; SBC2 a les
    mêmes en 0x8008655C / 0x8008CC7C, SBC1 en 0x80083DC0 / 0x8008A4E0.
  - Tables d'un rider (init `func_80064674` de SBC2, rider + 0x1E4) : +0x204 adresse du mouvement + 8, +0x39C son
    nombre d'images, +0x530 le numéro de sa première image, 100 entrées. Free Style avec Snowman : les 100 entrées
    pointent dans TOD_SM selon une correspondance mouvement humain → mouvement de Snowman (MAP dans snowtod.py, lue
    dans l'émulateur). Les trois tables écrites ainsi pour le joueur : la course tourne (avec la seule première,
    erreur d'adresse en 0x8008C278 : le lecteur sortait des mouvements de Snowman, plus courts), mais les morceaux
    de Snowman sont énormes et éparpillés autour de la caméra.
- v29 — la cause : la **hiérarchie**. Le lecteur de TOD (SBC2 `func_8008C2F8`, le même que FREE à 0x931C près) gère
  les paquets libgs : type 8 = créer l'objet, type 3 = parent (`super` du GsCOORDINATE2, +0x48), 1 = coordonnées…
  Le mouvement 0 de chaque TOD est une « mise en place » : TOD_SM crée 14 nœuds (objets 5..11, os 12..18) et leurs
  parents, TOD_MANx en crée 24 (5..0x1C). Au départ de l'épreuve, le jeu joue le mouvement 0 du TOD humain : les
  7 morceaux de Snowman se retrouvent sous des os humains, et TOD_SM anime ses os 12..18, qui sont au milieu du
  squelette humain. Liste des nœuds du rider : pointeur en rider + 0x1E4 (entrées de 0x18 octets : attribut,
  coordonnées, PMD, objet, base, numéro), racine en rider + 0x1D4. Hiérarchie de Snowman (Free Style) :
  racine → 12 → 9 → 13 → 8 → {14 → 7 → 15 → 5 → 16 → 6, 17 → 10, 18 → 11}.
  `snw` remet ces 14 parents à chaque image (les os humains 19..28 restent, inutilisés, sous ceux de Snowman).
  Piège : `lbu a0` suivi tout de suite de `beqz a0` lisait l'ancien a0 (délai de chargement) → l'os 12 restait
  sous un os humain → boucle dans la hiérarchie, récursion sans fin, mémoire écrasée.
- SBC1 (1re étape, épreuves de figures) a le même problème : riders D_80090DF0, conversions 0x80083DC0 / 0x8008A4E0,
  place libre `func_80061018` (morte), et les deux appels du lecteur de TOD `func_80089AB8` (0x80064B30, début d'un
  mouvement, et 0x80065150, chaque image) passent par `snw` (ses arguments sur la pile restent en place). Avec le
  seul premier appel, la hiérarchie humaine revenait. Vérifié dans l'émulateur : Big Air (1re étape) et Boarder
  Cross (2e étape), Snowman entier, animé comme en Free Style.

## Compteur en bas à gauche (Free Style)

- Les boules rouges : `func_8006CF34` (FREE) dessine jusqu'à 3 grosses boules puis des petites ; le nombre vient du
  champ +0xCB6 du rider. Ce champ est remis à 0 avec le rider (0x800650A8) et augmente de 1 à chaque (re)départ d'une
  descente (`func_8005C1C8`, qui vide aussi l'entrée +0xE10 + 4 n) ; une autre branche (0x80072074) le fait passer de
  1 à 2. C'est donc un compteur de descentes / essais plutôt que de chutes ; ce qu'il change en jeu n'est pas trouvé.

## Icônes des classements (records) — enquête

- Les classements de fin de course (RANKING : TIME / TRICK / TOTAL) dessinent l'icône du rider du record par une table
  de 7 mots `clut << 16 | v << 8 | u`, identique dans FREE (0x80097D60), HP (0x800934F4), BP (0x80097524) et OMT
  (0x80093878) : icônes 16 × 16 en 4 bits, page de texture (448, 256), u 0xC0..0xF0, v 0x30 / 0x40, palettes ligne 463
  (x 928..1008) et 464 (x 0). Le record ne garde que le numéro du rider (0..6) : un record de Kelly s'affiche avec Cindy.
- Pour Jicchi / Nick / Kelly il faudrait des numéros 7..9 dans les records et trois icônes de plus, mais la page de
  texture et les lignes de palettes sont pleines pendant les courses : il faut d'abord trouver de la place (VRAM) dans
  chaque mode.

## Écran large (widescreen hack de l'émulateur)

- Avec `beetle_psx_widescreen_hack`, l'image s'élargit mais le décor n'est dessiné que dans le champ du 4:3 : bords
  vides ou blancs (Free Style à gauche, half-pipe des deux côtés). Les bornes d'écran ne sont pas comparées en
  coordonnées écran (pas de test x contre ±160 / 320 trouvé) : le décor est choisi plus tôt (blocs de piste selon la
  caméra). Pas de correctif pour l'instant ; jouer en 4:3 reste conseillé.
- Suite de l'enquête : les routines de subdivision de libgte/libgs de l'exe (`func_80024D98`, `func_80025198`,
  `func_80037CD0`, `func_80038040`, `func_80038450`, `func_800388D0`, `func_80038DF0`, `func_80039340`) rejettent un
  polygone dont tous les sommets sont hors de OFX ± l/2 (l en +4 d'une structure passée sur la pile) ; neutraliser ces
  tests (56 branches, essai en RAM) ne change rien, pas plus que la largeur 320 de 0x80058E54. Sur le half-pipe, les
  murs du haut vont jusqu'au bord : il ne manque que le sol tout près de la caméra sur les côtés, soit les polygones
  rejetés parce qu'un sommet passe trop près de la caméra (limite de la GTE), invisibles en 4:3 et visibles en 16:9.
  Les corriger demanderait de découper ces polygones contre le plan proche : hors de portée d'un patch.
- Solution retenue (option « WIDESCREEN 16:9 » du mod `options`) : ne pas utiliser le hack de l'émulateur, mais faire
  calculer au jeu un champ plus large en réduisant l'échelle X de la matrice 0x80059288 (0x1000 → 0xC00, code de
  PeterDelta pour DuckStation) ; l'image s'affiche étirée en 16:9, sans bords manquants.
