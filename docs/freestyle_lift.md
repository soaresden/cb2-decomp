# Remontée en Free Style (mod `lift`, Remix v21)

Juste avant l'arrivée en Free Style, le joueur repart instantanément du haut de la piste, pour enchaîner les descentes
sans repasser par les menus. C'est le « Restart » du menu pause du jeu, déclenché automatiquement : pas de
chargement, porte de départ puis READY / GO (environ 5 s), chrono remis à zéro. Le temps de la descente n'est pas
enregistré (on ne franchit pas l'arrivée).

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

## Le mod

`remix/lift.py` : à 0x8005D04C, l'appel à `func_8005FE2C` passe par une petite routine (68 octets, à la fin de
FREE.BIN, dans le reste de son dernier secteur ; le début du tas de FREE, entrée 7 de la table de l'exe à 0x800100CC,
passe après elle) :

    si code de sortie == 0 et checkpoints == 3 et tronçon >= nombre de tronçons - 6 : code de sortie = 1

puis saute à `func_8005FE2C`. Sur une piste dont l'arrivée serait plus haut que « fin − 6 », l'arrivée se déclenche
avant et la course finit normalement.

Vérifié dans l'émulateur avec une version de test déclenchée au tronçon 15 : retour au tronçon 1 à chaque passage, en
boucle ; avec la vraie valeur, le Free Style se charge et la descente tourne (code chargé, crochet en place).

## Pistes pour la suite

- Sauter le compte à rebours : il n'est pas réglé par un simple compteur (rien ne change régulièrement dans les
  données de FREE pendant READY / GO) ; probablement piloté par l'animation de la porte de départ.
- Poteau visible : l'arrivée et les checkpoints sont des objets de piste (types 0x19… dans le code de collision,
  table de sauts 0x80097428) ; ajouter un objet « poteau » demande de comprendre le format des objets des pistes.
- Option « après l'arrivée » : laisser le code 5 (temps et record) puis enchaîner sur la remontée.
