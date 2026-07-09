"""Génère l'icône de l'application : rtsp-tool.svg, .png (256) et .ico (multi-tailles).

Usage : python packaging/make_icon.py
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

DOSSIER = Path(__file__).parent

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <rect x="8" y="8" width="240" height="240" rx="52" fill="#16181d"/>
  <rect x="8" y="8" width="240" height="240" rx="52" fill="none"
        stroke="#2a82da" stroke-width="6" opacity="0.35"/>
  <g transform="translate(49,49) scale(6.6)" fill="none" stroke="#2a82da"
     stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <polygon points="23 7 16 12 23 17 23 7" fill="#2a82da"/>
    <rect x="1" y="5" width="15" height="14" rx="2"/>
  </g>
  <circle cx="66" cy="196" r="9" fill="#3fbf5f"/>
</svg>
"""


def main():
    svg_path = DOSSIER / "rtsp-tool.svg"
    svg_path.write_text(SVG, encoding="utf-8")

    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QGuiApplication, QPixmap

    _app = QGuiApplication(sys.argv)
    pix = QPixmap()
    if not pix.loadFromData(QByteArray(SVG.encode()), "SVG"):
        raise SystemExit("rendu SVG impossible (plugin qsvg absent ?)")

    png_path = DOSSIER / "rtsp-tool.png"
    pix.save(str(png_path), "PNG")

    from PIL import Image
    ico_path = DOSSIER / "rtsp-tool.ico"
    Image.open(png_path).save(
        ico_path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                         (128, 128), (256, 256)])
    print(f"OK : {svg_path.name}, {png_path.name}, {ico_path.name}")


if __name__ == "__main__":
    main()
