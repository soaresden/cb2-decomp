# Cool Boarders 2 européen en 60 Hz (en cours)

La version européenne est la version américaine adaptée au 50 Hz. Pour la faire tourner en 60 Hz à la bonne vitesse :

1. **Mode vidéo** : le jeu choisit son mode une seule fois, au démarrage : `SetVideoMode(1)` (PAL) à l'exe
   0x800122D8 / argument en 0x800122E0 ; la version US appelle `SetVideoMode(0)` au même endroit. Le basculer suffit :
   dans l'émulateur le jeu passe de 49,8 Hz à 59,3 Hz et continue de tourner (mêmes écrans, un peu plus tard).
2. **Constantes recalées** : 1 158 constantes diffèrent dans le code aligné des deux versions, surtout ×1,2
   (durées en images, 245 cas) et la géométrie d'écran (256 → 240 lignes, positions verticales −32).
   `remix/pal60.py` reprend les valeurs US (1 042 mots : `addiu`/`ori` depuis `$zero`, `slti`, `sltiu`, `andi`).
3. **Blocs ajoutés pour le 50 Hz** : la version européenne a inséré quelques calculs (ex. ×35/25 sur l'entrée de
   rotation en l'air, SBC1 / TM / OMT / BP). À sauter pour retrouver le comportement 60 Hz. Pas encore fait.
4. Les fichiers de parcours (`DATA/CRS`) diffèrent entre les versions, mais par des décalages (rapports proches de 1),
   pas par des valeurs ×1,2 : a priori pas de recalage 50 Hz dans les données.

## État du prototype

| | Résultat dans l'émulateur |
|---|---|
| mode vidéo seul | 59,3 Hz, le jeu tourne, **image noire** |
| mode vidéo + constantes | idem |
| registres d'affichage | mode NTSC, mais zone affichée encore celle du PAL (début vertical 0x20 / fin 0x102 contre 0x10 / 0xFF aux USA, début horizontal 0x29C contre 0x260) |

Prochaine étape : trouver où le jeu fixe sa zone d'affichage (DISPENV, `PutDispEnv`) et lui donner les valeurs US,
puis vérifier la vitesse (chrono d'une course, durée d'une animation) contre la version US.
