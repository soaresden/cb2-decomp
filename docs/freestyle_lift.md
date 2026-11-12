# Arrivée express en Free Style (mod `lift`, Remix v22)

À l'arrivée, la descente compte comme dans le jeu d'origine (classement, records, trophées : c'est ce qui débloque
Snowman, les planches SPECIAL…), mais sans la célébration FINISH ni le replay (une quinzaine de secondes) :

1. on franchit la ligne → classement de la piste (saisie du nom si record) ;
2. START → écran RESULTS avec le temps, les figures et le total de la descente, RETRY déjà sélectionné ;
3. X → retour immédiat en haut de la piste (porte de départ, READY / GO), sans chargement.

Comment : le code de sortie 5 (arrivée) est traité à 0x8005D548 : le jeu compte les arrivés puis appelle
`func_80074768` (célébration + replay, qui renvoie −1 = « afficher les résultats » quand on appuie sur START).
À 0x8005D5A4, l'appel est remplacé par son résultat (`addiu v0, zero, -1`). Le reste (classement, records, trophées,
écran RESULTS et son RETRY) est le code du jeu, inchangé.

La v21 renvoyait en haut *avant* la ligne (le temps ne comptait pas) : abandonné.

## Ce qu'on a trouvé (FREE.BIN, White Resort)

| Adresse | Rôle |
|---|---|
| 0x800A3DA0 | pointeur vers la structure du joueur |
| joueur +0x2C | position X, Y, Z (Y vers le bas) |
| joueur +0xEC (+0x94) | tronçon de piste courant |
| joueur +0xCB6 | checkpoints passés (1 au départ, 3 dans la dernière section, 4 = arrivée) |
| joueur +0xE10 + 4 × n | temps de passage aux checkpoints |
| 0x800A3D78 | tableau des tronçons (56 octets chacun : position X, Y, Z…) ; le mot juste avant = leur nombre (148 sur White Resort) |
| 0x8009E234 | code de sortie de la boucle de course : 1 = Restart, 2 = Select, 3 = Exit (menu pause, table de sauts 0x80096590), 4 = TIME OVER, 5 = arrivée |
| 0x800A2D08 | chrono affiché |
| 0x8004F6C4 | compteur d'images global (exe) |

L'arrivée est un objet de la piste (comme les checkpoints) : sa traversée fait passer +0xCB6 à 4, puis
`func_8005FE2C` (mise à jour des checkpoints, appelée à chaque image à 0x8005D04C) écrit le code 5. Sur White Resort,
elle est au tronçon 145 sur 148.

## Ancienne version (v21, abandonnée)

`remix/lift.py` : à 0x8005D04C, l'appel à `func_8005FE2C` passe par une petite routine (68 octets, à la fin de
FREE.BIN, dans le reste de son dernier secteur ; le début du tas de FREE, entrée 7 de la table de l'exe à 0x800100CC,
passe après elle) :

    si code de sortie == 0 et checkpoints == 3 et tronçon >= nombre de tronçons - 6 : code de sortie = 1

puis saute à `func_8005FE2C`. Sur une piste dont l'arrivée serait plus haut que « fin − 6 », l'arrivée se déclenche
avant et la course finit normalement.

Vérifié dans l'émulateur avec une version de test déclenchée au tronçon 15 : retour au tronçon 1 à chaque passage, en
boucle ; avec la vraie valeur, le Free Style se charge et la descente tourne (code chargé, crochet en place).

Fin de course après l'arrivée : FINISH (≈ 6 s, dans la boucle de course) → replay (code remis à 0) → START →
classement (code 8 → `func_800600C0` → `func_80089F1C` : classement, trophées 0x80057448…, planches SPECIAL,
Snowman, puis écran RESULTS avec RETRY / GHOST UPDATE / SELECT / EXIT). Code de sortie → valeur rendue par la
fonction de course : 1 → 2 (relancer), 2 → 1, 3 → 0, 8 → −1 (résultats).

Pour les tests, la limite de temps du checkpoint suivant est en 0x80098654 (65 000 au départ de White Resort) ;
0x800A2D08 est le temps de la SECT1 (figé ensuite), pas le chrono total.

## Pistes pour la suite

- Afficher le temps de la descente précédente pendant la suivante (il est sur l'écran RESULTS juste avant RETRY).
- Sauter le compte à rebours : il n'est pas réglé par un simple compteur (rien ne change régulièrement dans les
  données de FREE pendant READY / GO) ; probablement piloté par l'animation de la porte de départ.
- Poteau visible : l'arrivée et les checkpoints sont des objets de piste (types 0x19… dans le code de collision,
  table de sauts 0x80097428) ; ajouter un objet « poteau » demande de comprendre le format des objets des pistes.
- Option « après l'arrivée » : laisser le code 5 (temps et record) puis enchaîner sur la remontée.
