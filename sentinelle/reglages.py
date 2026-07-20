"""Accès unique aux réglages locaux du poste (QSettings).

Passer par cette fonction plutôt que de construire QSettings directement permet
aux tests de rediriger les réglages vers un fichier temporaire, sans jamais
toucher la configuration réelle du poste (le registre sous Windows).
"""

from PySide6.QtCore import QSettings

# chemin de fichier .ini imposé par les tests ; None = comportement normal
# (registre Windows / .conf Linux via le format natif de Qt)
_fichier_test: str | None = None


def reglages() -> QSettings:
    if _fichier_test is not None:
        return QSettings(_fichier_test, QSettings.IniFormat)
    return QSettings("Sentinelle", "viewer")


def _rediriger_pour_tests(chemin: str):
    """Réservé aux tests : isole les réglages dans un fichier dédié."""
    global _fichier_test
    _fichier_test = chemin
