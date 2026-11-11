# Cool Boarders 2 : décompilation

Décompilation de **Cool Boarders 2** (PlayStation, version PAL **SCES-00992**), base du [Remix](https://soaresden.github.io/CB2Remix/).

Le but est de comprendre le code du jeu et de le modifier en C. On ne cherche pas, pour l'instant, à retrouver le C d'origine
octet pour octet (décompilation « matching »). Le projet reconstruit déjà le jeu à l'identique à partir de l'assembleur, puis on
remplace les fonctions utiles par du C au fur et à mesure.

**Aucune donnée du jeu n'est dans ce dépôt.** Il faut ton propre disque : le dépôt ne contient que la configuration, les noms et
le code écrit à la main.

## État

| Binaire | Rôle | Reconstruit à l'identique |
|---|---|---|
| `SCES_009.92` | exécutable principal (chargé à 0x80010000) | oui |
| `INIT.BIN` … `ENDING.BIN` | 14 overlays (chargés à 0x8005AEA8) | oui, les 14 |

- Exécutable principal : environ 810 fonctions repérées.
- Bibliothèques Sony (PsyQ, sources datées de fin 1996) : appels BIOS nommés automatiquement, et une partie de libgpu / libcd
  nommée par ses propres messages de debug.
- Variables du jeu connues grâce au Remix : rider, veste, tenue cachée, miroir, déblocages, table des fichiers.

## Mise en route

1. Extraire le code du disque : l'exécutable et les overlays vont dans `iso/`
   (`iso/SCES_009.92`, `iso/INIT.BIN`, … `iso/ENDING.BIN`).
   La page « Extracteur CB2 » le fait depuis le CHD, dans le navigateur.
2. Installer les outils :
   ```
   python3 -m venv venv && venv/bin/pip install -r requirements.txt
   sudo apt install binutils-mips-linux-gnu
   ```
3. Découper puis reconstruire :
   ```
   for n in main $(cat config/overlays.txt); do venv/bin/python -m splat split config/$n.yaml; done
   python3 build.py            # tout, ou : python3 build.py main sbc2
   ```
   `build.py` assemble, relie, puis compare chaque binaire à l'original.

## Organisation

| Chemin | Contenu |
|---|---|
| `config/<binaire>.yaml` | découpage splat de chaque binaire |
| `config/symbols.<binaire>.txt` | noms des fonctions et variables (à enrichir) |
| `include/macro.inc` | macros de l'assembleur généré |
| `build.py` | reconstruction et vérification |
| `asm/`, `linker/`, `build/`, `assets/` | générés, jamais commités |

## Repères

- Exe : en-tête PS-X EXE de 0x800 ; adresse = offset fichier + 0x8000F800. `.rodata` de 0x80010000 à 0x80012134, code
  jusqu'à 0x80045684, puis données jusqu'à 0x80050800, puis `.bss` jusqu'à 0x8005AEA8.
- `main()` (0x800121F8) charge la table des fichiers (`g_fileTable`, 0x800583E8), puis boucle : chargement d'un overlay
  et appel de son point d'entrée 0x8005AEAC.
- Overlays : le 1er mot est leur numéro, le code commence à 0x8005AEAC.
- Les zones « mortes » utilisées par le Remix sont des fonctions Sony jamais appelées : `SetGraphReverse` /
  `SetGraphDebug` (0x8002957C) et `DrawOTagEnv` (0x8002A030).
