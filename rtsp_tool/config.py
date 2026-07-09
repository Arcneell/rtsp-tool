"""Modèle de configuration et lecture/écriture de config.yaml.

Fichier géré par l'application (fenêtre Configuration). Emplacement par défaut
dans le profil utilisateur, ou config.yaml à côté de l'exe (mode portable).
Une entrée invalide est ignorée avec un avertissement, sans bloquer les autres.
"""

import base64
import logging
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import quote

import yaml

logger = logging.getLogger(__name__)

# Les mots de passe ne sont pas stockés en clair dans config.yaml (préfixe "obf:").
# NB : c'est un brouillage local, pas du chiffrement — la clé est embarquée dans
# l'app pour que la config reste déployable telle quelle sur chaque poste. Ça
# empêche la lecture fortuite du fichier, pas un attaquant déterminé.
_OBF_KEY = b"RTSP-TOOL.local.v1"


def _xor(data: bytes) -> bytes:
    return bytes(b ^ _OBF_KEY[i % len(_OBF_KEY)] for i, b in enumerate(data))


def obfusquer(clair: str) -> str:
    if not clair:
        return ""
    return "obf:" + base64.b64encode(_xor(clair.encode("utf-8"))).decode("ascii")


def desobfusquer(valeur: str) -> str:
    if isinstance(valeur, str) and valeur.startswith("obf:"):
        try:
            return _xor(base64.b64decode(valeur[4:])).decode("utf-8")
        except Exception:
            return ""
    return valeur or ""

# Flux demandé selon la vue : sub = substream, main = mainstream.
# En eco-extreme, la grille passe en mode photo ; ce mapping ne vaut que pour le mono.
PROFILS = {
    "normal": {"grille": "sub", "mono": "main"},
    "eco": {"grille": "sub", "mono": "sub"},
    "eco-extreme": {"grille": "sub", "mono": "sub"},
}

PROFIL_LABELS = {
    "normal": "Normal (fibre) — substream en grille, HD en mono",
    "eco": "Éco (4G) — substream partout",
    "eco-extreme": "Éco extrême (4G faible) — photo périodique en grille",
}

MARQUES = ("hikvision", "dahua", "custom")
LIENS = ("fibre", "4g")


def default_config_path() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "RTSP-TOOL", "config.yaml")
    base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, "rtsp-tool", "config.yaml")


def slugify(nom: str) -> str:
    """« Port — Quai 2 » → « port-quai-2 » (ids internes générés par l'UI)."""
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "item"


def mask_url(url: str) -> str:
    """rtsp://user:pass@host → rtsp://user:***@host (pour logs et UI)."""
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        creds, host = rest.rsplit("@", 1)
        return f"{scheme}://{creds.split(':', 1)[0]}:***@{host}"
    return url


# ---------------------------------------------------------------- structures

@dataclass
class Site:
    id: str
    nom: str
    lien: str = "fibre"           # fibre | 4g


@dataclass
class Camera:
    id: str
    nom: str
    site: Site
    profil: str = "normal"        # normal | eco | eco-extreme
    marque: str = "hikvision"     # hikvision | dahua | custom
    hote: str = ""
    port: int = 554
    canal: int = 1
    user: str = ""
    password: str = ""
    url_substream: str = ""       # marque: custom
    url_mainstream: str = ""      # marque: custom
    url_snapshot: str = ""        # marque: custom, profil eco-extreme
    port_http: int = 80           # ISAPI/CGI (mode photo, import DVR)
    photo_intervalle_s: int = 10  # rafraîchissement du mode photo
    reconnexion_preventive_s: int = 0   # 0 = désactivé

    def _auth(self) -> str:
        if not self.user:
            return ""
        return f"{quote(self.user, safe='')}:{quote(self.password, safe='')}@"

    def url(self, flux: str) -> str:
        """URL RTSP pour flux ∈ {sub, main}."""
        main = flux == "main"
        if self.marque == "custom":
            u = self.url_mainstream if main else self.url_substream
            # si un seul des deux est fourni, il sert pour les deux vues
            return u or self.url_mainstream or self.url_substream
        base = f"rtsp://{self._auth()}{self.hote}:{self.port}"
        if self.marque == "dahua":
            return f"{base}/cam/realmonitor?channel={self.canal}&subtype={0 if main else 1}"
        # hikvision : canal 1 → 101 (main) / 102 (sub), canal 12 → 1201/1202
        return f"{base}/Streaming/Channels/{self.canal * 100 + (1 if main else 2)}"

    def url_pour_vue(self, vue: str) -> str:
        """URL selon la vue ∈ {grille, mono}, en appliquant le profil."""
        return self.url(PROFILS[self.profil][vue])

    def flux_pour_vue(self, vue: str) -> str:
        return PROFILS[self.profil][vue]

    def snapshot_url(self) -> str:
        """URL HTTP d'une image instantanée (mode photo). Vide si non supporté."""
        if self.marque == "custom":
            return self.url_snapshot
        base = f"http://{self.hote}:{self.port_http}"
        if self.marque == "dahua":
            return f"{base}/cgi-bin/snapshot.cgi?channel={self.canal}"
        # Hikvision : image du substream (id x02) = résolution réduite, parfaite
        # pour une tuile de grille et plus légère sur un lien 4G
        return f"{base}/ISAPI/Streaming/channels/{self.canal * 100 + 2}/picture"

    def to_dict(self) -> dict:
        d = {"id": self.id, "nom": self.nom, "site": self.site.id,
             "profil": self.profil, "marque": self.marque}
        if self.marque == "custom":
            d.update(url_substream=self.url_substream,
                     url_mainstream=self.url_mainstream,
                     url_snapshot=self.url_snapshot)
        else:
            d.update(hote=self.hote, port=self.port, canal=self.canal,
                     port_http=self.port_http)
        d.update(user=self.user, password=obfusquer(self.password),
                 photo_intervalle_s=self.photo_intervalle_s)
        if self.reconnexion_preventive_s:
            d["reconnexion_preventive_s"] = self.reconnexion_preventive_s
        return d


@dataclass
class Etape:
    mode: str                      # grille | mono
    cameras: list                  # ids ; en mono : un seul élément
    duree_s: int = 30

    def to_dict(self) -> dict:
        return {"mode": self.mode, "cameras": list(self.cameras), "duree_s": self.duree_s}


@dataclass
class Sequence:
    nom: str
    etapes: list = field(default_factory=list)   # [Etape]

    def to_dict(self) -> dict:
        return {"nom": self.nom, "etapes": [e.to_dict() for e in self.etapes]}


@dataclass
class AppConfig:
    sites: list = field(default_factory=list)      # [Site]
    cameras: list = field(default_factory=list)    # [Camera]
    sequences: list = field(default_factory=list)  # [Sequence]
    warnings: list = field(default_factory=list)   # messages de validation
    path: str = ""
    rotation_duree_s: int = 20

    def site(self, site_id: str) -> Site | None:
        return next((s for s in self.sites if s.id == site_id), None)

    def camera(self, cam_id: str) -> Camera | None:
        return next((c for c in self.cameras if c.id == cam_id), None)

    def unique_id(self, base: str, taken: set | None = None) -> str:
        """Id unique dérivé d'un nom (les ids sont internes, générés par l'UI)."""
        taken = taken or ({s.id for s in self.sites} | {c.id for c in self.cameras})
        slug = slugify(base)
        cand, i = slug, 2
        while cand in taken:
            cand, i = f"{slug}-{i}", i + 1
        return cand


def purger_cameras_sequences(cfg: AppConfig, ids_retires: set):
    """Retire des séquences les caméras supprimées (étapes vides éliminées)."""
    for seq in cfg.sequences:
        for etape in seq.etapes:
            etape.cameras = [c for c in etape.cameras if c not in ids_retires]
        seq.etapes = [e for e in seq.etapes if e.cameras]
    cfg.sequences = [s for s in cfg.sequences if s.etapes]


# -------------------------------------------------------------------- lecture

def load_config(path: str) -> AppConfig:
    """Charge config.yaml. Fichier absent = config vide (premier lancement) ;
    les entrées invalides sont collectées dans AppConfig.warnings."""
    cfg = AppConfig(path=path)
    if not os.path.exists(path):
        logger.info(f"Pas de config existante ({path}) — démarrage vide")
        return cfg

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    options = raw.get("options") or {}
    try:
        cfg.rotation_duree_s = max(3, int(options.get("rotation_duree_s", 20)))
    except (TypeError, ValueError):
        cfg.warnings.append("[options] rotation_duree_s invalide → 20")

    for s in raw.get("sites") or []:
        try:
            lien = str(s.get("lien", "fibre")).lower()
            if lien not in LIENS:
                cfg.warnings.append(f"[site {s.get('id')}] lien '{lien}' inconnu → fibre")
                lien = "fibre"
            cfg.sites.append(Site(id=str(s["id"]), nom=str(s.get("nom") or s["id"]), lien=lien))
        except (KeyError, TypeError) as e:
            cfg.warnings.append(f"[site ?] entrée invalide ({e}) — skippée")

    ids_vus = set()
    for c in raw.get("cameras") or []:
        nom = c.get("id") or c.get("nom") or "<sans id>"
        try:
            cam_id = str(c["id"])
            if cam_id in ids_vus:
                raise ValueError(f"id '{cam_id}' en double")
            site = cfg.site(str(c.get("site")))
            if site is None:
                raise ValueError(f"site '{c.get('site')}' inconnu")
            marque = str(c.get("marque", "hikvision")).lower()
            if marque not in MARQUES:
                raise ValueError(f"marque '{marque}' inconnue")
            profil = str(c.get("profil") or ("eco" if site.lien == "4g" else "normal")).lower()
            if profil not in PROFILS:
                cfg.warnings.append(f"[{cam_id}] profil '{profil}' inconnu → normal")
                profil = "normal"
            if marque == "custom":
                if not (c.get("url_substream") or c.get("url_mainstream")):
                    raise ValueError("marque 'custom' : url_substream ou url_mainstream requis")
            elif not c.get("hote"):
                raise ValueError("champ 'hote' requis")

            cfg.cameras.append(Camera(
                id=cam_id,
                nom=str(c.get("nom") or cam_id),
                site=site,
                profil=profil,
                marque=marque,
                hote=str(c.get("hote", "")),
                port=int(c.get("port", 554)),
                canal=int(c.get("canal", 1)),
                user=str(c.get("user", "")),
                password=desobfusquer(str(c.get("password", ""))),
                url_substream=str(c.get("url_substream", "")),
                url_mainstream=str(c.get("url_mainstream", "")),
                url_snapshot=str(c.get("url_snapshot", "")),
                port_http=int(c.get("port_http", 80)),
                photo_intervalle_s=max(2, int(c.get("photo_intervalle_s", 10))),
                reconnexion_preventive_s=int(c.get("reconnexion_preventive_s", 0)),
            ))
            ids_vus.add(cam_id)
        except (KeyError, ValueError, TypeError) as e:
            cfg.warnings.append(f"[{nom}] config invalide : {e} — caméra skippée")

    cam_ids = {c.id for c in cfg.cameras}
    for s in raw.get("sequences") or []:
        nom = s.get("nom") or "<sans nom>"
        try:
            etapes = []
            for e in s.get("etapes") or []:
                mode = str(e.get("mode", "grille"))
                if mode not in ("grille", "mono"):
                    raise ValueError(f"mode '{mode}' inconnu")
                cams = [str(x) for x in (e.get("cameras") or []) if str(x) in cam_ids]
                if not cams:
                    raise ValueError("étape sans caméra valide")
                if mode == "mono":
                    cams = cams[:1]
                etapes.append(Etape(mode=mode, cameras=cams,
                                    duree_s=max(3, int(e.get("duree_s", 30)))))
            if not etapes:
                raise ValueError("aucune étape valide")
            cfg.sequences.append(Sequence(nom=str(nom), etapes=etapes))
        except (KeyError, ValueError, TypeError) as e:
            cfg.warnings.append(f"[séquence {nom}] invalide : {e} — skippée")

    for w in cfg.warnings:
        logger.warning(w)
    logger.info(f"Config : {len(cfg.cameras)} caméra(s), {len(cfg.sites)} site(s), "
                f"{len(cfg.sequences)} séquence(s) depuis {path}")
    return cfg


# ------------------------------------------------------------------- écriture

def save_config(cfg: AppConfig):
    """Réécrit config.yaml (écriture atomique : tmp puis remplacement)."""
    data = {
        "options": {"rotation_duree_s": cfg.rotation_duree_s},
        "sites": [{"id": s.id, "nom": s.nom, "lien": s.lien} for s in cfg.sites],
        "cameras": [c.to_dict() for c in cfg.cameras],
        "sequences": [s.to_dict() for s in cfg.sequences],
    }
    os.makedirs(os.path.dirname(os.path.abspath(cfg.path)), exist_ok=True)
    tmp = cfg.path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("# RTSP-TOOL — fichier géré par l'application (fenêtre Configuration).\n")
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, cfg.path)
    logger.info(f"Config enregistrée : {cfg.path}")
