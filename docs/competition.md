# Compétition : manches, qualifications et départ en handicap

Chaque manche du Tour Competition = « 1st STAGE » (épreuve de figures de qualification, overlay **SBC1**, mode
`0x80057420` = 0) puis « 2nd STAGE » Boarder Cross (overlay **SBC2**, mode 1). `0x80057458` = manche (piste),
`0x8005745C` = numéro de l'épreuve dans la manche (0 puis 1), `0x8005741C` = piste de l'épreuve en cours.

## Effectif (8 × 0xA8 octets à 0x80057464, indexé par rider, joueur = `g_rider` 0x80057408)

| Champ | Contenu |
|---|---|
| +0x00 | rider de l'ordinateur / figure (selon l'épreuve) |
| +0x02, +0x04 | points des 2 essais de la qualification (-1 = pas encore joué) |
| +0x06… | noms des figures (« <Miss> »…) |
| +0x8E (h) | **écart de départ** du Boarder Cross, en 1/100 s (meilleur = 0, dernier ≈ 22 s) |
| +0x90 (w) | le même × 10 |
| +0x94… | places des Boarder Cross des manches (-1 = pas couru) |

Le Boarder Cross part **en handicap** : chaque rider s'élance avec son écart. SBC1 écrit les écarts d'après le
classement de la qualification (manche 1 : 0, 4,00, 7,91, 11,53, 13,73, 15,79, 18,22, 22,22 s). Mettre l'écart du
joueur à 10 s le fait partir 4e (vérifié dans l'émulateur). Le « START RANK » de l'écran de la manche ne vient pas
de ces écarts (non trouvé).

## Fin d'une épreuve dans SBC1

`sbc1_entry` lance l'épreuve par `jal func_80062804` (0x8005B058 : écran de la manche, épreuve, résultats → code de
sortie), puis selon le mode (table 0x8008AA4C) : mode 0 → mode 1, nettoyage, `func_8001C748(ctx, 2)` qui met en
file les fichiers de l'épreuve suivante et rend la transition. Les « scènes » passées à `func_80014360` par la boucle
principale sont des transitions (7 = écran de chargement…), pas des numéros d'overlay : l'overlay et ses fichiers
sont dans la file du contexte (`sp+0x10` de `main`, lue par `func_80012448` en tête de boucle).

## Mod `skipq` (v25)

Au choix sur l'écran « 1st STAGE » : START = qualifications jouées ; SELECT maintenu + START = passées.
À 0x8005B058, en mode 0 et SELECT tenu (manette 0x8004FBF0, bit 0x100) seulement : écarts écrits directement (joueur 4e = 11,50 s ; les 7 autres écarts aux riders
de l'ordinateur, décalés à chaque manche), essais à 0, `0x8005745C` + 1, `0x8005741C` = piste de la manche, puis
« retour » du code 3 : la fin d'épreuve normale de SBC1 enchaîne sur le Boarder Cross. L'écran « 1st STAGE » reste
affiché (c'est là que se fait le choix ; le retirer bloque le chargement de l'épreuve). Code dans `func_800291CC` (fonction morte de l'exe), voir remix/skipq.py.
Échecs instructifs : forcer l'overlay depuis la boucle principale charge les fichiers de la mauvaise épreuve (la file
est lue avant le chargement de la scène) ou bloque le chargement.
