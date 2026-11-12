# Progression et 100 %

## La sauvegarde

Fichier de carte mémoire `BESCES-00992SAVE0` (USA : `BASCUS-94358SAVE0`), un bloc de 8 Ko écrit par `func_800189EC`
(exe) : en-tête de carte (« SC », titre, icône) sur 0x200 octets, puis à 0x21C la taille (0x998) et les données remplies
par `func_80018EB4`. Les 26 premiers octets de données (à 0x220) sont une copie de 0x80057434–0x8005744D :

| Adresse (PAL) | Contenu |
|---|---|
| 0x8005743E | pistes ouvertes au Free Style (3 après le podium en Compétition, 10 après le podium en Mirror) |
| 0x80057440 | riders : 0x0F au départ ; 0x10 Boss, 0x20 Gray, 0x40 Snowman |
| 0x80057442 | planches SPECIAL (bits 0, 1, 2) |
| 0x80057444 | mode Mirror débloqué |
| 0x80057446 | mode Hard débloqué |
| 0x80057448 / 744A / 744C | trophées du Free Style : 10 bits chacun (bit = piste), dans l'ordre temps / figures / total |

Suivent les records (0x800582F8…, 10 × 0xC0 octets de classements par piste, etc.).

## Conditions (lues dans le code)

- **Mirror** et pistes : podium (top 3) en Compétition (`ENDING` `func_8005D208`) ;
- **Hard** et les 10 pistes : podium en Compétition Mirror ;
- **Hard + Mirror** (ajouté par le Remix, L1 + R1 + ✕) : disponible dès que le Hard l'est (le jeu exige le Hard
  débloqué pour L1 + ✕, et le Hard suppose le Mirror) ; gagner en Hard + Mirror ne débloque rien de plus (le jeu ne
  l'enregistre pas). 0x80057438 et 0x8005743A sont sauvegardés mais jamais lus par le jeu : place libre pour
  enregistrer un jour une victoire en Hard + Mirror ;
- **Boss** : 1re place en Compétition Mirror ;
- **Snowman** : 1re place en Compétition après avoir débloqué le Hard, **ou** les 30 trophées du Free Style (FREE) ;
- **Gray** : half-pipe ≥ 376 (37,6 points, HP `sltiu s2, 0x178`), **ou** toutes les figures du Big Air Master (TM) ;
- **planches SPECIAL** : records du Free Style (compteurs de trophées, conditions exactes à confirmer) ;
- les tenues cachées de Cindy et Irin ne sont pas sauvegardées (code manette dans le jeu d'origine ; toujours là avec le
  mod `outfits`).

Les guides en ligne (GameFAQs, SuperCheats, Neoseeker… lus via des résumés de recherche) donnent les mêmes
conditions, avec des seuils de half-pipe variables (37,5 à 38) ; le code dit 37,6.

## Page Progression du site

Onglet « Progression » : ouvre la carte mémoire (.srm de pcsx_rearmed sur Batocera, .mcr, .mcd, .mc, .gme, .vmp, .mcs,
.psv), coche ce qui est gagné et donne le pourcentage (38 objectifs : 3 riders, Mirror, Hard, 3 planches, 30 trophées).
À valider avec une vraie sauvegarde de joueur (l'ordre temps / figures / total des trophées surtout).

## Page dans le jeu (mod `progress`, Remix v18)

Sur l'écran de sélection de mode, **maintenir SELECT** affiche un panneau : PROGRESSION xx %, BOSS, GRAY, SNOWMAN,
MIRROR, HARD, HARD+MIRROR (OK / --), SPECIAL n/3, TROPHEES n/30. Le pourcentage compte les mêmes 38 objectifs que le
site (Hard + Mirror affiché mais pas compté).

Comment c'est fait (`remix/progress.py`) :
- le code (991 octets) est ajouté à la fin de `MODE_SEL.BIN`, dans le reste de son dernier secteur (le fichier garde
  ses 81 secteurs ; sa taille dans le répertoire passe à 0x287FF — une taille de 81 × 2048 exactement fait lire un
  secteur de trop au chargeur et plante) ;
- le tas de MODE_SEL commençait juste après le fichier (table des débuts de tas des overlays dans l'exe,
  0x800100B0 + 4 × index) : l'entrée de MODE_SEL passe de 0x800832C8 à 0x800836A8 ;
- crochet : la fonction de la télé (`func_80064200`) appelle `func_8002E228` (numéro du tampon d'affichage) à
  0x800643B4 ; l'appel passe par la routine, qui rend le même résultat ;
- texte : routine du jeu `func_80012CA0` (police du menu 8×12 en VRAM (512,48), descripteur 0x80070648), primitives
  dans un tampon à part à 0x801F2000 / 0x801F3000 (au-dessus du tas, qui s'arrête à 0x801F1E00), insérées en tête de
  l'OT (entrée 0, devant tout), fond = un TILE bleu nuit ;
- coordonnées centrées sur l'écran (décalage de dessin du menu).
