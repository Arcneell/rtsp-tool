"""Point d'entrée : python -m sentinelle [--config chemin/config.yaml]

Sans argument, la configuration vit dans le profil utilisateur
(%APPDATA%\\Sentinelle\\config.yaml) et se gère entièrement dans l'interface.
Usage portable : --config .\\config.yaml à côté de l'exe.
"""

import argparse
import logging
import os
import sys

from .config import app_data_dir, default_config_path, migrer_ancien_dossier

logger = logging.getLogger("sentinelle")


def _config_logging(verbose: bool):
    """Journalisation : console + fichier dans le dossier de données.

    Le fichier est essentiel quand l'application est lancée depuis le bureau
    (aucun terminal, cas de Debian/GNOME) : un échec au démarrage y laisse une
    trace au lieu de disparaître silencieusement."""
    niveau = logging.DEBUG if verbose else logging.INFO
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                            "%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(niveau)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)


def _ajouter_journal_fichier():
    """Ajoute le journal fichier (après l'éventuelle migration de dossier)."""
    try:
        os.makedirs(app_data_dir(), exist_ok=True)
        fh = logging.FileHandler(os.path.join(app_data_dir(), "sentinelle.log"),
                                 encoding="utf-8")
        fh.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S"))
        logging.getLogger().addHandler(fh)
    except OSError as e:
        logger.warning(f"Journal fichier indisponible ({e})")


def _installer_excepthook():
    """Trace toute exception non gérée (y compris hors terminal)."""
    def hook(exc_type, exc, tb):
        logger.critical("Exception non gérée", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = hook


def _forcer_xcb_si_wayland():
    """Sous Wayland, préfère Qt en xcb (XWayland).

    mpv s'incruste dans chaque tuile via un identifiant de fenêtre X11 (`wid`) ;
    en Wayland natif cela ne fonctionne pas (tuiles noires). On demande donc
    xcb en premier, avec repli sur wayland si le plugin xcb ne peut pas se
    charger (liste « xcb;wayland » : l'application démarre dans tous les cas).
    Sans effet si l'utilisateur a fixé lui-même QT_QPA_PLATFORM."""
    if (sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY")
            and not os.environ.get("QT_QPA_PLATFORM")):
        os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"
        logger.info("Session Wayland détectée : Qt demandé en xcb (XWayland) "
                    "pour l'affichage vidéo, repli wayland si indisponible.")


def main() -> int:
    parser = argparse.ArgumentParser(prog="sentinelle",
                                     description="Sentinelle — visionneuse de vidéosurveillance")
    parser.add_argument("--config", "-c", default="",
                        help="chemin du fichier de configuration (défaut : profil utilisateur)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="journalisation détaillée (niveau DEBUG)")
    parser.add_argument("--safe-video", action="store_true",
                        help="sortie vidéo logicielle (vo=x11, sans OpenGL) — "
                             "à utiliser si l'affichage vidéo fait planter le "
                             "système (pilote GPU fragile)")
    args = parser.parse_args()

    _config_logging(args.verbose)
    _installer_excepthook()

    if args.safe_video:
        # sortie logicielle : évite le chemin OpenGL de mpv, qui peut faire
        # tomber le serveur d'affichage sur certains pilotes GPU Linux.
        os.environ.setdefault("SENTINELLE_MPV_VO", "x11")
        os.environ.setdefault("SENTINELLE_MPV_HWDEC", "no")
        logger.info("Mode vidéo sûr : vo=x11, hwdec=no")

    migrer_ancien_dossier()          # reprend les données de l'ancien nom si présent
    _ajouter_journal_fichier()       # dossier de données désormais fixé

    _forcer_xcb_si_wayland()         # AVANT la création de QApplication

    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    from PySide6.QtWidgets import QApplication, QMessageBox

    # Route les messages internes de Qt dans le logging Python (mêmes format et
    # flux que le reste), pour qu'ils restent visibles au débogage.
    _qt_log = logging.getLogger("qt")
    _niveaux = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def _handler_qt(mode, contexte, message):
        niveau = _niveaux.get(mode, logging.INFO)
        # Avertissement bénin en DPI fractionnaire / multi-écrans : Windows rabote
        # la géométrie de quelques pixels, sans effet visible. On le rétrograde en
        # DEBUG (masqué par défaut, réapparaît avec --verbose) au lieu de polluer.
        if "Unable to set geometry" in message:
            niveau = logging.DEBUG
        _qt_log.log(niveau, message)

    qInstallMessageHandler(_handler_qt)

    app = QApplication(sys.argv)
    app.setApplicationName("Sentinelle")
    # NE PAS quitter tant que seules des boîtes de dialogue de démarrage
    # (assistant de premier lancement, page de connexion) sont affichées, AVANT
    # la fenêtre principale. Sinon, sous certains gestionnaires de fenêtres
    # (GNOME/Wayland en tête), la fermeture de la dernière boîte de dialogue fait
    # quitter l'application et la fenêtre principale n'apparaît jamais — c'était
    # le symptôme « je me connecte, la fenêtre de login se ferme, rien ne s'ouvre ».
    app.setQuitOnLastWindowClosed(False)

    from .ui.theme import apply_theme
    apply_theme(app)          # thème mémorisé (sombre par défaut)
    from .ui.icons import app_icon
    app.setWindowIcon(app_icon())

    config_path = args.config
    if not config_path:
        # portable : un config.yaml posé à côté de l'exe a priorité
        if getattr(sys, "frozen", False):
            portable = os.path.join(os.path.dirname(sys.executable), "config.yaml")
            if os.path.exists(portable):
                config_path = portable
        config_path = config_path or default_config_path()

    # Premier lancement : choix du mode AVANT d'ouvrir l'application. Fermer
    # l'assistant sans choisir n'entre pas dans l'appli — on quitte, et le choix
    # sera redemandé au prochain lancement.
    from .reglages import reglages
    settings = reglages()
    if not settings.contains("mode"):
        from .ui.setup_dialog import SetupDialog
        dlg = SetupDialog()
        if not dlg.exec() or not dlg.resultat:
            return 0
        # repart d'une base propre (aucun compte hérité d'une install précédente)
        settings.remove("serveur_user")
        settings.remove("serveur_pass")
        settings.setValue("mode", dlg.resultat["mode"])
        # l'adresse du serveur est saisie à la connexion (page de login)

    from .ui.main_window import MainWindow

    try:
        win = MainWindow(config_path)
    except Exception:
        # un échec ici (config serveur, thème, écran…) fermait l'appli sans rien
        # afficher : on trace et on prévient l'utilisateur au lieu de disparaître.
        logger.exception("Échec au démarrage de la fenêtre principale")
        journal = os.path.join(app_data_dir(), "sentinelle.log")
        QMessageBox.critical(None, "Sentinelle",
                             "Le démarrage a échoué.\n\n"
                             f"Détails dans le journal :\n{journal}")
        return 1

    if getattr(win, "demarrage_annule", False):
        return 0                         # connexion serveur abandonnée

    win.show()
    win.raise_()
    win.activateWindow()
    # à partir d'ici, fermer la dernière fenêtre quitte normalement l'application
    app.setQuitOnLastWindowClosed(True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
