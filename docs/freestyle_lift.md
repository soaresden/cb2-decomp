# Remontée en Free Style (en cours)

Idée : un poteau juste avant l'arrivée ; on fonce dedans et on remonte tout en haut, posé juste devant le départ, pour
enchaîner les descentes (pratique en time attack, sans repasser par les menus).

## Ce qu'on sait (émulateur, White Resort, Remix complet)

- Position du joueur (X, Y, Z ; Y vers le bas, Z décroît en descendant) : plusieurs copies dans le tas, p. ex.
  0x8018D46C (puis 0x8018D4C4, 0x8018D574, 0x8019204C… ; 0x80191EB0… = historique décalé, traînée / fantôme).
  Départ après « Restart » : (-306, 1694, -5354).
- Chrono de la descente : 0x800A2D08 (BSS de FREE), remis à 0 par « Restart ».
- Le menu pause (Continue / Restart / Select / Exit, chaînes à 0x80096540…, pointeurs rangés en 0x800A4178…) :
  **« Restart » remet le joueur au départ instantanément, sans chargement**, avec la porte de départ et READY / GO.
  C'est la routine à réutiliser.
- Indicateur de pause probable : 0x8009ED34 (0 en course, 1 en pause) ; le curseur du menu pause n'est pas encore
  trouvé (ni en mot de 16 ni de 32 bits dans les données de FREE : peut-être dans le tas ou en octet).

## Plan

1. Trouver le code qui exécute « Restart » (lecture du curseur de pause, puis appel de la remise à zéro).
2. Crochet par image en Free Style : si le joueur dépasse un point juste avant l'arrivée (Z de la piste, par piste),
   appeler cette remise à zéro, puis sauter le compte à rebours (garder la vitesse si possible).
3. Repère visuel : réutiliser un objet existant de la piste (panneau, drapeau) plutôt qu'un modèle neuf ; à défaut,
   un message à l'écran (« LIFT »).
4. Time attack : le temps de la descente est-il enregistré si on ne franchit pas l'arrivée ? Sinon, déclencher la
   remontée juste après la ligne d'arrivée.
