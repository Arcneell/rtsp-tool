"""Tests de non-régression du serveur : authentification, droits par
utilisateur, autorisation du relais, invalidation de session, anti-force-brute,
minimum de mot de passe et validité de session.

N'exige ni Docker ni MediaMTX : l'API est testée via TestClient ; le relais et
le moniteur de mouvement tournent en arrière-plan et échouent silencieusement,
sans gêner les tests.
"""

import os

import yaml
from fastapi.testclient import TestClient

CONFIG = {
    "options": {"rotation_duree_s": 20},
    "sites": [{"id": "s1", "nom": "Site 1", "lien": "fibre"}],
    "cameras": [{
        "id": "cam1", "nom": "Caméra 1", "site": "s1", "profil": "normal",
        "marque": "hikvision", "hote": "127.0.0.1", "port": 554, "canal": 1,
        "port_http": 9, "user": "u", "password": "p",
    }],
}


def _mdp_admin_initial(data_dir) -> str:
    ligne = (data_dir / "admin-initial.txt").read_text(encoding="utf-8")
    for l in ligne.splitlines():
        if "mot de passe" in l:
            return l.split(":", 1)[1].strip()
    raise AssertionError("mot de passe admin introuvable")


def _client(tmp_path):
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(CONFIG), encoding="utf-8")
    os.environ["SENTINELLE_DATA"] = str(tmp_path)
    from sentinelle_server.app import create_app
    return create_app(str(tmp_path))


def test_parcours_complet(tmp_path):
    app = _client(tmp_path)
    with TestClient(app) as c:
        mdp = _mdp_admin_initial(tmp_path)

        # santé + rejets d'authentification
        assert c.get("/api/health").json()["ok"] is True
        assert c.post("/api/login", json={"username": "admin", "password": "faux"}).status_code == 401
        assert c.post("/api/login", json={"username": "ghost", "password": "x"}).status_code == 401

        tok = c.post("/api/login", json={"username": "admin", "password": mdp}).json()["token"]
        A = {"Authorization": f"Bearer {tok}"}

        # validité de session exposée pour le rafraîchissement client
        sess = c.get("/api/session", headers=A).json()
        assert sess["ok"] is True and sess["reste_s"] > 0

        # admin voit tout
        cfg = c.get("/api/config", headers=A).json()
        assert cfg["compte"]["role"] == "admin"
        assert [x["id"] for x in cfg["cameras"]] == ["cam1"]

        # création d'un utilisateur sans aucune caméra (mot de passe >= 8)
        users = c.get("/api/users", headers=A).json()["users"]
        v = {"username": "v", "role": "user", "tout": False,
             "sites": [], "cameras": [], "password": "viewer-1"}
        assert c.put("/api/users", headers=A, json={"users": users + [v]}).status_code == 200

        tv = c.post("/api/login", json={"username": "v", "password": "viewer-1"}).json()["token"]
        V = {"Authorization": f"Bearer {tv}"}

        # le viewer ne voit aucune caméra et n'accède pas à l'admin
        assert c.get("/api/config", headers=V).json()["cameras"] == []
        assert c.get("/api/users", headers=V).status_code == 403
        assert c.get("/api/config/full", headers=V).status_code == 403

        # autorisation relais : refus viewer, accord admin, refus jeton bidon
        base = {"action": "read", "path": "cam1-sub"}
        assert c.post("/api/relay-auth", json={**base, "password": tv}).status_code == 403
        assert c.post("/api/relay-auth", json={**base, "password": tok}).status_code == 200
        assert c.post("/api/relay-auth", json={**base, "password": "bidon"}).status_code == 401

        # publication : refusée depuis une IP publique, tolérée depuis le réseau
        # interne ET sans ip (appel interne MediaMTX — ne jamais couper les sources)
        pub = {"action": "publish", "path": "cam1-sub"}
        assert c.post("/api/relay-auth", json={**pub, "ip": "8.8.8.8"}).status_code == 403
        assert c.post("/api/relay-auth", json={**pub, "ip": "127.0.0.1"}).status_code == 200
        assert c.post("/api/relay-auth", json=pub).status_code == 200

        # droit accordé au site -> le viewer voit la caméra
        v["sites"] = ["s1"]
        c.put("/api/users", headers=A, json={"users": users + [v]})
        tv = c.post("/api/login", json={"username": "v", "password": "viewer-1"}).json()["token"]
        V = {"Authorization": f"Bearer {tv}"}
        assert [x["id"] for x in c.get("/api/config", headers=V).json()["cameras"]] == ["cam1"]
        assert c.post("/api/relay-auth",
                      json={**base, "password": tv}).status_code == 200

        # boucles personnelles filtrées sur les caméras visibles
        boucles = {"sequences": [
            {"nom": "ok", "etapes": [{"mode": "mono", "cameras": ["cam1"], "duree_s": 5}]},
            {"nom": "ko", "etapes": [{"mode": "mono", "cameras": ["absente"], "duree_s": 5}]},
        ]}
        c.put("/api/account/sequences", headers=V, json=boucles)
        seqs = c.get("/api/config", headers=V).json()["sequences"]
        assert [s["nom"] for s in seqs] == ["ok"]

        # changement de mot de passe -> l'ancienne session est invalidée
        r = c.post("/api/account/password", headers=V,
                   json={"ancien": "viewer-1", "nouveau": "viewer-2"})
        assert r.status_code == 200
        assert c.get("/api/config", headers=V).status_code == 401


def test_dernier_admin_protege(tmp_path):
    app = _client(tmp_path)
    with TestClient(app) as c:
        mdp = _mdp_admin_initial(tmp_path)
        tok = c.post("/api/login", json={"username": "admin", "password": mdp}).json()["token"]
        A = {"Authorization": f"Bearer {tok}"}
        # tenter de ne laisser aucun admin -> refus
        r = c.put("/api/users", headers=A, json={"users": [
            {"username": "u", "role": "user", "tout": False,
             "sites": [], "cameras": [], "password": "unmotdepasse"}]})
        assert r.status_code == 422


def test_mot_de_passe_trop_court_rejete(tmp_path):
    """Un mot de passe < 8 caractères n'est jamais enregistré : le compte n'est
    pas créé et un avertissement est renvoyé."""
    app = _client(tmp_path)
    with TestClient(app) as c:
        mdp = _mdp_admin_initial(tmp_path)
        tok = c.post("/api/login", json={"username": "admin", "password": mdp}).json()["token"]
        A = {"Authorization": f"Bearer {tok}"}
        users = c.get("/api/users", headers=A).json()["users"]
        faible = {"username": "faible", "role": "user", "tout": False,
                  "sites": [], "cameras": [], "password": "123"}
        r = c.put("/api/users", headers=A, json={"users": users + [faible]})
        assert r.status_code == 200
        assert r.json()["warnings"]                       # avertissement présent
        # le compte n'a pas été créé avec ce mot de passe faible
        assert c.post("/api/login",
                      json={"username": "faible", "password": "123"}).status_code == 401
        # changement de son propre mot de passe : minimum imposé aussi
        assert c.post("/api/account/password", headers=A,
                      json={"ancien": mdp, "nouveau": "court"}).status_code == 422


def test_anti_force_brute_login(tmp_path):
    """Au-delà de LOGIN_MAX échecs depuis la même IP, le login est temporairement
    refusé (429) sans même vérifier le mot de passe."""
    from sentinelle_server.app import LOGIN_MAX
    app = _client(tmp_path)
    with TestClient(app) as c:
        for _ in range(LOGIN_MAX):
            assert c.post("/api/login",
                          json={"username": "admin", "password": "faux"}).status_code == 401
        r = c.post("/api/login", json={"username": "admin", "password": "faux"})
        assert r.status_code == 429
        assert "Retry-After" in r.headers
