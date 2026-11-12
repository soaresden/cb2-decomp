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

## Une page dans le jeu ?

Faisable, mais c'est un vrai chantier : il faut un nouvel écran dans MAIN_SEL (texte et cases), appelé depuis un menu
existant, dans les zones libres de l'overlay. Le site couvre le besoin en attendant.
