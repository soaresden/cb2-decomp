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
