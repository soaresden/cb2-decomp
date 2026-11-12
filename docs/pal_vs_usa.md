# Cool Boarders 2 : Europe (SCES-00992) et USA (SCUS-94358)

Comparaison des deux disques, faite à partir des CHD (intégrité vérifiée par `chdman verify` sur les deux).

## En bref

| | Europe | USA |
|---|---|---|
| Exécutable | `SCES_009.92` | `SCUS_943.58` |
| Date de compilation (chaîne dans l'exe) | 11/11/1997 13:36 | 17/09/1997 09:44 |
| Pistes audio (musiques) | 19 (`BGMA` … `BGMS`) | 20 (`BGMA` … `BGMT`) |
| Fichiers du disque | 380 | 379 |
| Sauvegardes | `BESCES-00992…` | `BASCUS-94358…` |

La version européenne est **la plus récente** (près de deux mois après) : c'est une adaptation de la version américaine.

## Musiques

Bandes-son presque entièrement différentes : sur 19 et 20 pistes, **2 enregistrements seulement sont identiques**
(empreinte SHA-1 du son) :

| Europe | USA | Durée |
|---|---|---|
| `BGML` | `BGMM` | 67 s |
| `BGMS` | `BGMT` | 15 s (presque silencieuse) |

Toutes les autres pistes sont propres à chaque version ; les musiques américaines sont nettement plus fortes
(niveau moyen 1,5 à 3 fois plus élevé). Seule l'européenne contient le code `CdGetToc2` et la chaîne `track=%d,%d` : elle
lit la table des pistes du CD.

## Code

| Binaire | Fonctions | Code identique |
|---|---|---|
| exécutable | 418 / 415 | 97 % |
| overlays de course (SBC1, SBC2, VS, OMT, BP, HP, FREE, TM, COMB) | même nombre dans les deux versions | 92 à 95 % |
| MAIN_SEL / MODE_SEL / INIT | même nombre | 91 % / 88 % / 43 % |
| **Total** | 3228 fonctions européennes | **93 %** identiques |

(Comparaison des instructions sans les adresses, qui se décalent forcément.)

Ce qui change :

- **Adaptation au 50 Hz** : des seuils exprimés en images passent de 114 à 137, de 113 à 136, etc. (rapport 6/5,
  60 → 50 images par seconde). Concerne les figures en l'air (`<overlay>_playerAirControl`, modifiée dans les 8 modes de
  course) et les chocs (`sbc2_racerBumpResponse`, qui a aussi quelques instructions en plus en Europe).
- **Structure du rider** : de nombreux champs sont environ 0x418 octets plus loin en Europe (ex. 4024 → 5072).
- Textes de la carte mémoire (majuscules aux USA : « No Memory Card! », « Save Successful. »…).
- Les replays de démonstration (`DATA/DEMO/*.DEM`, 20 % d'octets différents) ont été refaits, logique si la physique est
  recalée au 50 Hz.

## Fichiers propres à chaque version

| Europe seulement | USA seulement |
|---|---|
| `ETC/CB2T1E.FBD`, `ETC/CB2T2E.FBD` | `ETC/CB2T1A.FBD`, `ETC/CB2T2A.FBD` |
| `MOVIE/OPMOVIEE.STR`, `SBCMOVE.STR`, `STAFFE.STR` | `MOVIE/OPMOVIEA.STR`, `SBCMOVA.STR`, `STAFFA.STR` |
| `ETC/RANK.DAT`, `LOAD/NOTICE.FBD` | `CDDA/BGMT.DA` |

## Autres différences

- Parcours (`DATA/CRS/*.DAT`, 17 fichiers, et `DATA/CRS/VS/*`) : tailles et contenus différents (jusqu'à 28 % des octets
  sur un fichier de même taille) ; à étudier (réglages au 50 Hz ? IA ?).
- Graphismes : quasiment identiques (menus 0,2 %, effets 0,2 %), sauf le half-pipe (`CRSFBD/HS.FBD`, 4,7 %) et l'écran
  d'avertissement (`LOAD/WARNING.FBD`, 14 %).
- Sons : `SOUND/ETC/SBC_SEL.VB`, `SEL_SE.VB`, `SOUND/SBC/SBC1SE.VB`, `SESBCRNK.VB` différents.
- Logo de l'éditeur (`ETC/PRESENTS.DAT`) : 53 Ko en Europe, 13 Ko aux USA.

## Conséquences pour le projet

- Le Remix est fait pour la version européenne ; 93 % du code étant commun, un portage vers la version américaine est
  possible, mais toutes les adresses changent et la structure du rider est décalée.
- La décompilation peut viser les deux versions avec le même découpage : mêmes fonctions, adresses différentes.
- Mettre les musiques américaines dans le Remix européen (ou l'inverse) est techniquement faisable à partir des deux
  disques du joueur (remplacement des pistes audio), sans rien distribuer.
