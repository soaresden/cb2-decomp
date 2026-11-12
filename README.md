# Cool Boarders 2 : Remix et décompilation

Tout le code du projet **Cool Boarders 2 Remix** (PlayStation, version PAL **SCES-00992**) :

- **`remix/`** : les sources du Remix (riders cachés jouables, contrôle en l'air, stats MAX, collisions…) ;
- **`make_remix.py`** : **une commande** qui construit le Remix à partir de ton propre disque ;
- **`batocera/`** : le patcheur pour Batocera (un fichier `.pygame`) ;
- **`skins/`** : appliquer les skins et la planche perso faits sur le site, en ligne de commande ;
- **`decomp.py`**, **`config/`** : la décompilation du jeu. Les 15 binaires (exécutable et 14 overlays) se reconstruisent
  déjà à l'identique depuis l'assembleur ; on les remplace par du C petit à petit.

**Aucune donnée du jeu n'est dans ce dépôt.** Tout part de ton disque : CHD ou BIN de *Cool Boarders 2 (Europe)*.

## Pour jouer (sans rien installer)

| Où | Comment |
|---|---|
| Navigateur | [soaresden.github.io/CB2Remix](https://soaresden.github.io/CB2Remix/) : ouvre ton CHD, installe le Remix, retouche les tenues, dessine ta planche. |
| Batocera | `CB2_Remix_Patcher.pygame` dans `/userdata/roms/pygame/`, lance-le depuis le système Pygame : il trouve le jeu dans `/userdata/roms/psx` et écrit `Cool Boarders 2 Remix (Europe).chd` à côté. |
| PC | Le CHD produit se joue dans n'importe quel émulateur PS1 (DuckStation, pcsx_rearmed…). |

## Construire le Remix soi-même

Il faut Python 3.8 ou plus récent (Windows, Linux ou macOS), puis :

```
pip install numpy pillow
python3 make_remix.py "Cool Boarders 2 (Europe).chd"
```

Résultat : `build/Cool Boarders 2 Remix (Europe).chd`. Pas besoin de chdman : le CHD est lu et réécrit en Python, seuls les
blocs modifiés sont réécrits et le reste garde la compression d'origine.

Avec `--release`, la commande produit aussi tout ce qu'on distribue :

| Fichier (`build/`) | Usage |
|---|---|
| `cb2remix.delta.gz` | le patch (uniquement les octets nouveaux et des instructions de copie depuis le disque du joueur) |
| `CB2_Remix_Patcher.pygame` | le patcheur Batocera (environ 50 Ko) |
| `patches.js` | le patch pour le site (à copier dans le dépôt `CB2Remix`) |

Le patcheur Batocera de la version publiée se régénère aussi sans le disque : `python3 batocera/mkpygame.py`.

### Musiques de la version américaine

Avec ton CD américain en CHD, le Remix peut prendre les musiques US (20 pistes, recopiées telles quelles) :
`python3 make_remix.py "Cool Boarders 2 (Europe).chd" --us-music "Cool Boarders 2 (USA).chd"`. Même option sur le site
(onglet Patchs) et dans le patcheur Batocera (s'il trouve les deux CHD, bouton B = avec les musiques US). Le jeu cherche
ses musiques par les fichiers `/CDDA/BGMx.DA` : ils sont redirigés vers les pistes US qui jouent au même moment
(correspondance tirée des appels de musique des deux versions, voir `docs/pal_vs_usa.md`).

### Remix pour la version américaine

Première version (tout débloqué, planches SPECIAL, Hard + Mirror) : voir `docs/remix_usa.md`.

## Skins et planches perso (sans navigateur)

Les éditeurs restent sur le site : le Prêt-à-porter enregistre des skins `.cb2skin.json` ; l'Atelier exporte la planche
en PNG 128×64. `skins/cb2skins.js` (Node.js, sans dépendance) les applique avec le même code que le site. Il faut aussi
une copie du dépôt du site, à côté de celui-ci (`../CB2Remix`) ou indiquée avec `--site`.

```
# Remix + skins sur le jeu d'origine
node skins/cb2skins.js "Cool Boarders 2 (Europe).chd" --remix --skin pere-noel.cb2skin.json --skin pop-star.cb2skin.json -o "CB2 Remix perso.chd"
# planche perso dans une carte mémoire (nouvelle, ou --card ta_carte.srm pour l'ajouter à la tienne)
node skins/cb2skins.js "Cool Boarders 2 (Europe).chd" --board planche.png -o carte.srm
node skins/cb2skins.js "Cool Boarders 2 (Europe).chd" --board dessus.png --board-bottom dessous.png --style 1 --type 2 -o carte.srm
```

## Modifier le Remix

1. Modifier `remix/remix.py` (la fonction `patches()` liste chaque mot changé dans l'exécutable et les overlays ;
   `apply()` fait le reste : textures, sons, emplacement des fichiers sur le disque).
2. Augmenter `remix/VERSION`.
3. `python3 make_remix.py ton_jeu.chd --release --keep`, tester le CHD dans un émulateur, puis publier les fichiers de
   `build/`. `--keep` garde les fichiers extraits dans `work/` pour les essais suivants.

## Décompilation

```
pip install -r requirements.txt
sudo apt install binutils-mips-linux-gnu        # assembleur MIPS (sous Windows : dans WSL)
```

1. Mettre l'exécutable et les overlays du disque dans `iso/` (`iso/SCES_009.92`, `iso/INIT.BIN` … `iso/ENDING.BIN`) : la
   page « Extracteur CB2 » le fait depuis le CHD, ou bien `make_remix.py --keep` les laisse dans `work/fs/`.
2. `python3 decomp.py split` : découpe avec splat dans `asm/`.
3. `python3 decomp.py check` : assemble, relie et compare chaque binaire à l'original (`15/15 identiques`).

| Chemin | Contenu |
|---|---|
| `config/<binaire>.yaml` | découpage splat de chaque binaire |
| `config/symbols.<binaire>.txt` | noms des fonctions et variables (à enrichir) |
| `include/macro.inc` | macros de l'assembleur généré |
| `asm/`, `linker/`, `build/`, `assets/`, `work/`, `iso/` | générés ou issus du disque, jamais commités |

Repères :

- Exe : en-tête PS-X EXE de 0x800 ; adresse = offset fichier + 0x8000F800. `.rodata` de 0x80010000 à 0x80012134, code
  jusqu'à 0x80045684, données jusqu'à 0x80050800, puis `.bss` jusqu'à 0x8005AEA8. Bibliothèques Sony PsyQ datées de fin 1996.
- `main()` (0x800121F8) charge la table des fichiers (`g_fileTable`, 0x800583E8), puis boucle : chargement d'un overlay et
  appel de son point d'entrée 0x8005AEAC. Chaque overlay (menus, courses, half-pipe…) commence par son numéro.
- Les zones « mortes » utilisées par le Remix sont des fonctions Sony jamais appelées : `SetGraphReverse` / `SetGraphDebug`
  (0x8002957C) et `DrawOTagEnv` (0x8002A030).

## Et une version PC native ?

C'est l'aboutissement possible d'une décompilation, mais il faut d'abord avoir passé presque tout le jeu en C, puis remplacer
ce qui parle directement au matériel de la PlayStation (affichage, son, CD). En attendant, le Remix se joue sur PC via un
émulateur.

## Vérifications

- `tools/cb2disc.py` (lecture CHD/BIN, application du patch, écriture CHD) donne les mêmes fichiers que le code du site
  (`disc.js`), testé en BIN et en CHD (cdlz, cdzl) ; le CHD écrit est relu correctement par chdman.
- Les sources du Remix appliquées au jeu d'origine reproduisent l'exécutable et les 14 overlays de la v16 à l'octet près
  (comparaison avec le patch publié). Les étapes qui touchent aux autres fichiers du disque (textures, sons, films) n'ont pas
  encore été relancées depuis le portage : le premier `make_remix.py --release` sur un vrai disque doit redonner exactement
  `remix/cb2remix.delta.gz`.
- `skins/cb2skins.js` : décodeur PNG vérifié sur tous les formats 8 bits, carte mémoire de planche relue par `board.js`.
  L'application des skins reprend le code du bouton « Créer le jeu modifié » du site, mais n'a pas encore tourné sur un vrai
  disque.
