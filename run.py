"""Lanceur : python run.py [--config cameras.yaml] — sert aussi d'entrée PyInstaller."""

from rtsp_tool.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
