# Remix pour la version américaine (SCUS-94358)

## Ce qui est fait (1re version, « 16-us1 »)

| Fonction | État |
|---|---|
| Tout débloqué sur une nouvelle sauvegarde (riders, pistes, planches SPECIAL, miroir, hard, récompenses) | testé dans l'émulateur : variables en RAM |
| Tous les riders sélectionnables même avec une ancienne sauvegarde | transposé |
| Planches SPECIAL toujours proposées, compétition comprise | transposé |
| Hard + Mirror ensemble (L1 + R1 + X sur Competition > NEW) | testé : L1+X = hard, R1+X = miroir, L1+R1+X = les deux |

Le patch (`remix/cb2remix_usa.delta.gz`, 11 secteurs) est appliqué par le site (onglet Patchs, le jeu US est reconnu) et
par le patcheur Batocera (il écrit « Cool Boarders 2 Remix (USA).chd »).

## Comment c'est fait

1. `tools/port_usa.py` aligne les deux versions : fonctions appariées (même ordre dans les overlays, par contenu dans
   l'exécutable), puis instructions appariées dans chaque fonction (98 à 99 % des instructions). Il en déduit :
   - l'adresse US de chaque instruction européenne ;
   - l'adresse US de chaque variable, apprise sur les couples `lui` / `addiu|lw|sw…` du code aligné
     (ex. `g_rider` 0x80057408 → 0x800570C8 ; variables de l'exe 0x340 octets plus bas).
2. `remix/usa.py` prend les patchs du Remix européen (`remix.patches()`), les transpose en vérifiant l'instruction
   d'origine côté US, recopie le code neuf dans la même zone libre de l'exe US (après avoir vérifié qu'elle est vide)
   en corrigeant sauts, branchements et adresses, puis construit le delta US.
3. Différence importante : **l'exe US charge ses overlays à 0x8005AB68** (0x8005AEA8 en Europe).

```
python3 remix/usa.py PAL_fs USA_fs USA.chd remix/cb2remix_usa.delta.gz
```
(`PAL_fs` / `USA_fs` : fichiers extraits des deux disques ; `make_remix.py --keep` laisse ceux du disque européen dans
`work/fs`.)

## En cours : 2e version (expérimentale, pas encore publiée)

`remix.usa.phase2()` transpose en plus, sans erreur (449 mots) :

| Fonction | État |
|---|---|
| contrôle en l'air (X seul fait tourner, vitesses spin/flip, carré ×4, grabs « X to Y ») | transposé ; accroche du flip refaite pour SBC1 / TM / OMT / BP (`lw v0` au lieu de `lw a0` aux USA) |
| lecture de la manette (base des grabs et du ○ des stats MAX) | **testé** : l'exe US n'a pas le saut où le Remix s'accroche ; accroche refaite après le calcul des boutons + relais. Dans l'émulateur la copie des boutons suit la manette (Rond 0x20, Carré 0x80, Gauche 0x8000) et le jeu tourne |
| stats MAX (○ sur l'écran BOARDER) | transposé, pas encore vérifié en jeu |
| Boarder Cross : collisions | transposé, pas encore vérifié en jeu |
| Big Air Master (colonne NEXT) | pas transposé : son code calcule ses adresses de tables par additions, et la zone libre US n'est pas la même |

Construction du patch de test : `phase1()` + `phase2()` puis `build_delta()` (43 secteurs). À valider en jeu avant de le
publier.

## Ce qui reste (essai de transposition de tout le Remix)

Sur les 874 mots modifiés par le Remix européen :

| | Nombre |
|---|---|
| instructions du jeu retrouvées telles quelles côté US | 621 |
| code neuf dans les zones libres (à transposer par blocs, comme Hard + Mirror) | 240 |
| instructions à reprendre à la main (exe 7, MAIN_SEL 2, SBC1 / TM / OMT / BP 1 chacun) | 13 |

À cela s'ajoutent les étapes « données » de `remix.apply()` à adapter aux fichiers US :

- riders en compétition (Boss, Gray, Snowman) : paquets de modèles, variantes d'ENEMY1, table des fichiers
  (`LOCTBL`, index des fichiers différents aux USA) ;
- plaques de nom GRAY / SNOWMAN, voix de Boss (`SBC2ND0`), emplacements libres sur le disque (les films s'appellent
  `OPMOVIEA.STR` / `SBCMOVA.STR` aux USA) ;
- aperçu des tenues cachées dans le menu (bloc ajouté à MAIN_SEL, tas du menu) ;
- contrôle en l'air, stats MAX, collisions de Boarder Cross, Big Air Master : code à transposer par blocs ;
  attention, une partie de la physique européenne est recalée au 50 Hz (voir `pal_vs_usa.md`) : les constantes de
  temps du Remix (délais en images) sont à revoir pour le 60 Hz.

## Tester

L'émulateur de test est Beetle PSX (paquet `libretro-beetle-psx`) piloté par un petit frontal Python ; il ne lit pas les
CHD (`chdman extractcd` d'abord) et n'expose pas la RAM : elle est lue dans les sauvegardes d'état (bloc
`MainRAM.data8`). Il faut un BIOS PlayStation (non fourni).
