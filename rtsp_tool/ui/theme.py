"""Thème sombre (palette Fusion) — adapté à un mur d'images."""

from PySide6.QtGui import QColor, QPalette


def apply_dark_theme(app):
    app.setStyle("Fusion")
    p = QPalette()
    fond = QColor(24, 24, 24)
    panneau = QColor(32, 32, 32)
    texte = QColor(220, 220, 220)
    desactive = QColor(110, 110, 110)
    accent = QColor(42, 130, 218)

    p.setColor(QPalette.Window, fond)
    p.setColor(QPalette.WindowText, texte)
    p.setColor(QPalette.Base, panneau)
    p.setColor(QPalette.AlternateBase, fond)
    p.setColor(QPalette.Text, texte)
    p.setColor(QPalette.Button, panneau)
    p.setColor(QPalette.ButtonText, texte)
    p.setColor(QPalette.ToolTipBase, panneau)
    p.setColor(QPalette.ToolTipText, texte)
    p.setColor(QPalette.Highlight, accent)
    p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.Link, accent)
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, desactive)
    app.setPalette(p)
