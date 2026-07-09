# RTSP-TOOL

Visionneuse multi-sites de flux **RTSP** (DVR Hikvision / Dahua) pour **Windows et Linux**.
Application desktop autonome — **pas de serveur, pas d'enregistrement** : chaque poste
lit directement les DVR. Toute la configuration se fait **dans l'interface**, aucun
fichier à éditer à la main.

Pensée pour un réseau contraint : la maîtrise de la **bande passante** est au cœur de
l'outil (substream en grille, mode photo pour les liens 4G, aucun flux ouvert hors écran).

## Fonctionnalités

### Visualisation
- Vue **grille** (jusqu'à 4×4) et vue **mono** (double-clic sur une tuile, Échap pour revenir)
- Arborescence Sites → Caméras : on coche ce qu'on veut voir, le reste **n'ouvre aucune connexion**
- **Rotation automatique** : défilement des pages de la grille (ou des caméras en mono), durée réglable
- **Boucles / séquences** : scénarios configurables (étape 1 telle grille 30 s, étape 2 telle caméra en mono 15 s…) joués en boucle, avec éditeur intégré
- **Plein écran** avec choix du moniteur, **thème sombre**
- Clic droit sur une tuile : **capture d'image**
- Débit réseau affiché **par tuile** et **au total**

### Économie de bande passante (cœur du produit)
Le débit consommé est décidé par le **flux demandé au DVR**, pas par le lecteur.
Profils par caméra :

| Profil | Vue grille | Vue mono | Usage |
|--------|-----------|----------|-------|
| **Normal** (fibre) | Substream | Mainstream (HD) | Sites bien connectés |
| **Éco** (4G) | Substream | Substream | Liens limités |
| **Éco extrême** (4G faible) | **Mode photo** : snapshot JPEG rafraîchi toutes les N s (quelques ko) | Substream | Liens très contraints |

- Caméra hors écran = **zéro connexion** ; rotations et boucles ferment les flux avant d'ouvrir les suivants
- RTSP forcé en **TCP** (fiable sur WAN/4G), lecture directe **sans transcodage**
- Upscaling soigné des substreams (mpv `ewa_lanczossharp`) pour rester lisibles agrandis

### Robustesse
- Reconnexion automatique avec **backoff exponentiel** (5 s → 10 min)
- **Échec d'authentification = arrêt définitif des tentatives** pour ne pas verrouiller
  le compte côté DVR (indispensable quand rotations/boucles ré-ouvrent des flux en boucle)
- Chaque tuile est indépendante : un flux qui meurt n'affecte pas les autres

### Configuration 100 % dans l'interface
- **Ajouter un DVR** : IP + identifiants, découverte automatique des canaux et de leurs
  noms via l'ISAPI Hikvision (ou génération manuelle pour Dahua / ISAPI fermé), toutes
  les caméras créées d'un coup
- Sites (fibre / 4G), caméras, boucles : ajout / édition / suppression à tout moment
  (clic droit dans le panneau ou fenêtre Configuration)
- Config stockée dans le profil utilisateur (`%APPDATA%\RTSP-TOOL\config.yaml` /
  `~/.config/rtsp-tool/config.yaml`) ; un `config.yaml` posé à côté de l'exe prend la
  priorité (mode portable)
- Les mots de passe DVR ne sont jamais réaffichés dans l'interface et sont brouillés
  dans le fichier de config *(brouillage local anti-lecture-fortuite, pas du chiffrement
  fort : la clé est embarquée dans l'app pour rester déployable)*

## Installation (développement)

```bash
pip install -r requirements.txt
python run.py
```

**libmpv** (moteur vidéo) est requise :
- *Windows* : placer `libmpv-2.dll` dans un dossier `lib/` à la racine
  (archive `mpv-dev-x86_64-…` depuis les [builds mpv](https://github.com/shinchiro/mpv-winbuild-cmake/releases))
- *Debian/Ubuntu* : `sudo apt install libmpv2` — *Fedora* : `sudo dnf install mpv-libs`

*(Optionnel : `ffprobe` du paquet ffmpeg améliore le diagnostic des pannes ; l'appli fonctionne sans.)*

Au premier lancement, la fenêtre Configuration s'ouvre pour ajouter sites et DVR.

## Packaging (exe signé, .deb)

Voir [packaging/DEPLOIEMENT.md](packaging/DEPLOIEMENT.md) : build + signature de l'exe
Windows et construction du `.deb` Linux (avec icône et entrée de menu).

```bash
# .deb via Docker (fonctionne aussi depuis Windows)
docker run --rm -v "${PWD}:/src" -w /src debian:12 bash packaging/build_deb.sh
```

## Structure

```
rtsp_tool/
  config.py             # modèle + fichier config.yaml géré par l'appli
  probe.py              # classification des échecs RTSP (auth/timeout/réseau)
  snapshot.py           # snapshots JPEG (ISAPI/CGI) + découverte des canaux Hikvision
  player.py             # chargement libmpv + réglages RTSP basse latence + upscaling
  ui/main_window.py     # grille/mono, rotation, boucles, plein écran multi-écrans
  ui/tile.py            # tuile vidéo : états, backoff, arrêt sur 401, débit, capture
  ui/photo_tile.py      # tuile mode photo (éco extrême)
  ui/config_dialogs.py  # sites, caméras, ajout d'un DVR entier
  ui/sequence_editor.py # éditeur de boucles
  ui/icons.py           # icônes SVG
packaging/              # build .deb, génération d'icône, doc de déploiement
```

## Pile technique

Python 3.11+ · [PySide6](https://doc.qt.io/qtforpython/) (Qt 6) ·
[python-mpv](https://github.com/jaseg/python-mpv) (libmpv) · PyYAML · requests.

## Licence

MIT — voir [LICENSE](LICENSE).
