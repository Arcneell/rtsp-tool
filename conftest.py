"""Configuration des tests.

- rend le paquet du dépôt importable (racine sur sys.path) ;
- ISOLE les réglages du poste dans un fichier temporaire : les tests ne
  touchent JAMAIS la configuration réelle (registre Windows / .conf Linux).
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sentinelle.reglages import _rediriger_pour_tests

_rediriger_pour_tests(os.path.join(tempfile.mkdtemp(prefix="sentinelle-tests-"),
                                   "reglages.ini"))
