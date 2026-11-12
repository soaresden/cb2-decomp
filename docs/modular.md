# Remix modulaire : un interrupteur par mod, et un code de configuration

`remix/modular.py` découpe le Remix v16 en 9 mods indépendants. Le site (onglet Patchs), `make_remix.py --config` et le
patcheur Batocera utilisent le même paquet (`remix/cb2remix_mods.json.gz`, 31 Ko) et donnent **le même fichier, à l'octet
près**.

| id | Mod | Ce que ça touche |
|---|---|---|
| `unlock` | Tout débloqué | INIT (valeurs de départ), MAIN_SEL 0x80063EA8 (riders sélectionnables avec une ancienne sauvegarde) |
| `special` | Planches SPECIAL partout | MAIN_SEL 0x8005B0C4 + lectures de 0x80057442 |
| `hardmirror` | Hard + Mirror | exe 0x8004F878–0x8004F89F, MODE_SEL |
| `riders` | Boss, Gray et Snowman en championnat | caves de l'exe, MAIN_SEL, SBC1/SBC2, ENEMY1, EFCT_SBC (plaques), LOCTBL, paquets de modèles, voix de Boss (fin du film d'intro coupée) |
| `outfits` | Tenues cachées de Cindy et Irin | MAIN_SEL (grandit : déplacé à la fin de SBCMOVE.STR, coupée), exe |
| `max` | Stats MAX | MAIN_SEL + écrans de course |
| `air` | Figures en l'air | overlays de course |
| `ramming` | Chocs en Boarder Cross | exe 0x80028BF4–0x80028D3C, SBC2 |
| `bam` | Big Air Master | TM |

`max` et `air` partagent la lecture de la manette (`input`, ajoutée automatiquement). Sans `air`, les sauts du code
partagé vers la partie « contrôle en l'air » retournent directement au jeu (`input_noair`).

## Vérifications

- tous les mods = build v16 (713 secteurs identiques) ; aucun mod = disque d'origine ;
- moteur JS (`disc.js` `applyMods`) = moteur Python sur plusieurs combinaisons ;
- émulateur (Beetle PSX) : chaque mod seul et « tous sauf un » (18 images) démarrent, passent les menus et jouent une
  manche de compétition ;
- « 100 % à gagner » (tout sauf `unlock` et `special`) : 4 riders seulement sur une nouvelle partie (0x80057440 = 0xF),
  miroir et hard verrouillés, ○ : MAX présent.

## Le paquet

Opérations par mod, relatives au disque d'origine : mots de 32 bits (`w`, avec la valeur d'origine vérifiée), octets
(`bs` : copiés depuis le fichier d'origine ou nouveaux), ajout à la fin d'un fichier (`append`), entrées de répertoire
(`rec`), secteurs entiers (`sec`, copies depuis le disque + octets nouveaux). Aucune donnée du jeu n'y est stockée : ce qui
vient du jeu est copié depuis le disque du joueur.

Régénération (après un changement du Remix) : `make_remix.py --release` (écrit aussi `build/patches.js` avec
`window.REMIX_MODS`), ou :

```
python3 remix/modular.py PAL.chd "Remix v16.chd" PAL_fs remix/cb2remix.delta.gz remix/cb2remix_mods.json.gz
```

## Code de configuration

`CB2-XXXX-XXXX` : 1 octet de version, 2 octets de mods (bit i = i-ème mod du tableau ci-dessus), 1 octet d'options
(bit 0 : musiques US ; bits 1-3 réservés : intro, 60 Hz), 2 octets de tenues du Prêt-à-porter (bit i = entrée i de
`skins/index.json` du site), octets nuls de fin retirés, puis 1 octet de contrôle (crc32 & 255), en base32 Crockford.
Exemples : `CB2-07ZG-3G8` = Remix complet, `CB2-07Y0-20G` = 100 % à gagner, `CB2-040B-W` = aucun mod.

Le code est écrit dans le disque construit (descripteur de volume, secteur 16, octet 900, zone inutilisée par le jeu) :
le site et le patcheur reconnaissent un jeu déjà patché et affichent son code.

```
python3 make_remix.py original.chd --config CB2-07Y0-20G      # (les tenues : avec le site)
python3 CB2_Remix_Patcher.pygame source.chd dest.chd --code CB2-07Y0-20G [--us usa.chd]
```

Sur Batocera, le patcheur ouvre un écran d'interrupteurs (croix haut/bas, A = cocher, START = construire) et part du
code de `cb2remix_code.txt` (à côté du .pygame) s'il existe ; il y enregistre le dernier code utilisé.

## Intro

Les films d'intro européen (`OPMOVIEE.STR`) et américain (`OPMOVIEA.STR`) ont exactement la même taille : c'est le
même film ré-encodé. Le choix de l'intro n'apporte donc rien ; le champ est réservé dans le code (pour « sans intro »
plus tard : le film est lancé par INIT, table de 4 chemins à 0x8005F700).
