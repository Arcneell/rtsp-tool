<div align="center">

# RTSP-TOOL

**Visionneuse de vidéosurveillance multi-sites, pensée pour les réseaux contraints.**

Lecture de flux RTSP (DVR **Hikvision** / **Dahua**) en grille ou plein écran, avec
rotation automatique, séquences configurables et une gestion fine de la bande passante.
Application desktop autonome — *sans serveur, sans enregistrement.*

[![Licence MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)
[![Plateformes](https://img.shields.io/badge/plateformes-Windows%20%7C%20Linux-informational.svg)](#installation)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-PySide6%20(Qt%206)-41cd52.svg)](https://doc.qt.io/qtforpython/)
[![Moteur vidéo](https://img.shields.io/badge/vidéo-libmpv-ff5555.svg)](https://mpv.io/)

</div>

---

## Sommaire

- [Pourquoi cet outil](#pourquoi-cet-outil)
- [Fonctionnalités](#fonctionnalités)
- [Gestion de la bande passante](#gestion-de-la-bande-passante-le-cœur-du-projet)
- [Installation](#installation)
- [Configuration](#configuration)
- [Packaging & déploiement](#packaging--déploiement)
- [Architecture](#architecture)
- [Pile technique](#pile-technique)
- [Feuille de route](#feuille-de-route)
- [Licence](#licence)

## Pourquoi cet outil

Superviser des dizaines de caméras réparties sur plusieurs sites — certains en fibre,
d'autres en 4G — sans saturer le réseau ni monter une infrastructure serveur.

RTSP-TOOL est un **client desktop autonome** : chaque poste lit directement les DVR,
on l'installe via un `.exe` (Windows) ou un `.deb` (Linux), et tout se configure
**dans l'interface**. Le parti pris central : **c'est le flux qu'on demande au DVR qui
décide du débit**, jamais le poste — d'où une consommation réseau maîtrisée par
conception.

## Fonctionnalités

| | |
|---|---|
| **Vues** | Grille adaptative (jusqu'à 4×4) et plein écran mono-caméra, bascule au double-clic |
| **Rotation** | Défilement automatique des pages de la grille (ou des caméras en mono), durée réglable |
| **Séquences** | « Boucles » configurables : suite d'étapes (grille ou mono + caméras + durée) jouées en continu, éditeur intégré |
| **Profils bande passante** | Par caméra : *Normal*, *Éco* (4G), *Éco extrême* (mode photo) |
| **Multi-écrans** | Plein écran sur le moniteur de son choix |
| **Découverte DVR** | Ajout d'un DVR entier : les canaux et leurs noms sont récupérés via l'API ISAPI Hikvision |
| **Robustesse** | Reconnexion à backoff exponentiel, arrêt sur erreur d'authentification (anti-verrouillage de compte) |
| **Confort** | Capture d'image, débit affiché par tuile et au total, thème sombre |
| **Sécurité** | Mots de passe jamais réaffichés dans l'UI, brouillés dans le fichier de config |

## Gestion de la bande passante — le cœur du projet

Le débit consommé dépend du **flux demandé au DVR**, pas du lecteur. RTSP-TOOL joue
uniquement sur *quel* flux ouvrir et *quand* — zéro transcodage, aucun flux ouvert
hors écran.

| Profil | Vue grille | Vue mono | Cible |
|--------|-----------|----------|-------|
| **Normal** | Substream | Mainstream (HD) | Sites bien connectés (fibre) |
| **Éco** | Substream | Substream | Liens limités (4G) |
| **Éco extrême** | **Mode photo** — snapshot JPEG rafraîchi toutes les *N* secondes (quelques ko) | Substream | Liens 4G très contraints |

Principes appliqués partout :

- 🔌 **Caméra hors écran = zéro connexion.** Rotations et séquences ferment les flux
  précédents avant d'ouvrir les suivants.
- 📉 **Mode photo** pour les liens saturés : une tuile passe de ~300 kbps continus à
  quelques ko par image.
- 🖥️ **Upscaling soigné** des substreams (mpv `ewa_lanczossharp`) pour rester lisibles
  une fois agrandis.
- 🔒 **RTSP sur TCP**, lecture directe H.264/H.265 sans réencodage.

## Installation

> **Prérequis :** Python 3.11+ et **libmpv** (moteur vidéo).
> - *Windows* : placer `libmpv-2.dll` dans un dossier `lib/` à la racine
>   (archive `mpv-dev-x86_64-…` des [builds mpv](https://github.com/shinchiro/mpv-winbuild-cmake/releases)).
> - *Debian/Ubuntu* : `sudo apt install libmpv2` — *Fedora* : `sudo dnf install mpv-libs`.
> - *Optionnel :* `ffprobe` (paquet `ffmpeg`) affine le diagnostic des pannes.

```bash
git clone https://github.com/Arcneell/rtsp-tool.git
cd rtsp-tool
pip install -r requirements.txt
python run.py
```

Au premier lancement, la fenêtre **Configuration** s'ouvre pour ajouter sites et DVR.

## Configuration

Tout se gère **dans l'interface** — aucun fichier à éditer à la main :

1. **Ajouter un site** (fibre ou 4G).
2. **Ajouter un DVR** : adresse + identifiants, puis découverte automatique des canaux
   (Hikvision) ou génération manuelle (Dahua). Toutes les caméras sont créées d'un coup.
3. Cocher les caméras à afficher, composer des boucles, régler la rotation.

La configuration est stockée dans le profil utilisateur
(`%APPDATA%\RTSP-TOOL\config.yaml` sous Windows,
`~/.config/rtsp-tool/config.yaml` sous Linux). Un `config.yaml` placé à côté de
l'exécutable prend la priorité (**mode portable** pour livrer une config commune).

> **Note de sécurité** — les mots de passe DVR ne sont jamais réaffichés dans l'interface
> et sont brouillés dans le fichier. Il s'agit d'un brouillage local (anti-lecture
> fortuite), *pas* d'un chiffrement fort : la clé est embarquée pour que la config reste
> déployable telle quelle. Utilisez un compte DVR **en lecture seule** dédié à l'outil.

## Packaging & déploiement

Guide complet : **[packaging/DEPLOIEMENT.md](packaging/DEPLOIEMENT.md)** (build, signature
de l'exe Windows, construction du `.deb` avec icône et entrée de menu).

```bash
# Exécutable Windows
pyinstaller --noconfirm --windowed --name RTSP-Tool --icon packaging/rtsp-tool.ico \
    --add-binary "lib/libmpv-2.dll;." run.py

# Paquet .deb (via Docker, fonctionne aussi depuis Windows)
docker run --rm -v "${PWD}:/src" -w /src debian:12 bash packaging/build_deb.sh
```

## Architecture

```
rtsp_tool/
├── config.py             Modèle de données + fichier config.yaml géré par l'appli
├── probe.py              Classification des échecs RTSP (auth / timeout / réseau)
├── snapshot.py           Snapshots JPEG (ISAPI/CGI) + découverte des canaux Hikvision
├── player.py             Chargement libmpv, réglages RTSP basse latence, upscaling
└── ui/
    ├── main_window.py    Grille/mono, rotation, boucles, plein écran multi-écrans
    ├── tile.py           Tuile vidéo : états, backoff, arrêt sur 401, débit, capture
    ├── photo_tile.py     Tuile « mode photo » (profil éco extrême)
    ├── config_dialogs.py Sites, caméras, ajout d'un DVR entier
    ├── sequence_editor.py Éditeur de boucles
    └── icons.py          Icônes SVG
packaging/                Build .deb, génération d'icône, guide de déploiement
```

**Principes de conception**

- Une **instance libmpv par tuile**, sur un thread indépendant : un flux qui tombe
  n'affecte jamais les autres.
- **Échec d'authentification = arrêt définitif des tentatives.** Les rotations et boucles
  ré-ouvrant des flux en permanence, un mauvais mot de passe re-tenté verrouillerait le
  compte côté DVR — l'outil s'arrête et le signale au lieu d'insister.
- **Reconnexion à backoff exponentiel** (5 s → 10 min) pour les liens 4G instables.

## Pile technique

[Python 3.11+](https://www.python.org/) · [PySide6](https://doc.qt.io/qtforpython/) (Qt 6)
· [python-mpv](https://github.com/jaseg/python-mpv) (libmpv) · [PyYAML](https://pyyaml.org/)
· [requests](https://requests.readthedocs.io/).

## Feuille de route

- [x] Grille / mono, profils bande passante, reconnexion robuste
- [x] Mode photo (4G), rotation automatique, éditeur de boucles
- [x] Découverte ISAPI, débit par tuile, multi-écrans, thème sombre
- [x] Packaging exe signé + `.deb` avec icône
- [ ] Découverte ONVIF (marques hors Hikvision/Dahua)
- [ ] Réglage du substream directement depuis l'outil (résolution / IPS / débit)

## Licence

Distribué sous licence **MIT** — voir [LICENSE](LICENSE).
