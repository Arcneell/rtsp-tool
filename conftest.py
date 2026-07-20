"""Configuration des tests.

- rend le paquet du dépôt importable (racine sur sys.path) ;
- ISOLE les réglages Qt (QSettings) dans un dossier temporaire pour ne jamais
  écrire dans la configuration réelle du poste pendant les tests.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings

_reglages_tests = tempfile.mkdtemp(prefix="sentinelle-tests-")
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, _reglages_tests)
QSettings.setPath(QSettings.IniFormat, QSettings.SystemScope, _reglages_tests)
