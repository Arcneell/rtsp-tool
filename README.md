<div align="center">

# RTSP-TOOL

**Multi-site video-surveillance viewer, built for bandwidth-constrained networks.**

View RTSP streams (**Hikvision** / **Dahua** DVRs) in a grid or full screen, with
automatic rotation, configurable sequences and fine-grained bandwidth control.
A standalone desktop app — *no server, no recording.*

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20Linux-informational.svg)](#installation)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-PySide6%20(Qt%206)-41cd52.svg)](https://doc.qt.io/qtforpython/)
[![Video engine](https://img.shields.io/badge/video-libmpv-ff5555.svg)](https://mpv.io/)

</div>

---

## Table of contents

- [Why this tool](#why-this-tool)
- [Features](#features)
- [Bandwidth management](#bandwidth-management--the-heart-of-the-project)
- [Installation](#installation)
- [Configuration](#configuration)
- [Packaging & deployment](#packaging--deployment)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Roadmap](#roadmap)
- [License](#license)

## Why this tool

Monitoring dozens of cameras spread across multiple sites — some on fiber, others on
4G — without saturating the network or standing up server infrastructure.

RTSP-TOOL is a **standalone desktop client**: each workstation reads the DVRs directly,
you install it via an `.exe` (Windows) or a `.deb` (Linux), and everything is configured
**in the interface**. The core design choice: **the stream you request from the DVR is
what decides the bitrate**, never the workstation — so network usage is controlled by
design.

## Features

| | |
|---|---|
| **Views** | Adaptive grid (up to 4×4) and full-screen single camera, toggle on double-click |
| **Rotation** | Automatic cycling through grid pages (or through cameras in single view), adjustable interval |
| **Sequences** | Configurable "loops": a series of steps (grid or single + cameras + duration) played continuously, with a built-in editor |
| **Bandwidth profiles** | Per camera: *Normal*, *Eco* (4G), *Extreme eco* (photo mode) |
| **Multi-monitor** | Full screen on the display of your choice |
| **DVR discovery** | Add a whole DVR at once: channels and their names are retrieved via the Hikvision ISAPI |
| **Resilience** | Exponential-backoff reconnection, stop on authentication failure (prevents account lockout) |
| **Convenience** | Snapshot capture, per-tile and total bitrate display, dark theme |
| **Security** | Passwords never shown again in the UI, obfuscated in the config file |

## Bandwidth management — the heart of the project

The bitrate consumed depends on the **stream requested from the DVR**, not on the player.
RTSP-TOOL only decides *which* stream to open and *when* — zero transcoding, no stream
kept open off-screen.

| Profile | Grid view | Single view | Target |
|---------|-----------|-------------|--------|
| **Normal** | Substream | Mainstream (HD) | Well-connected sites (fiber) |
| **Eco** | Substream | Substream | Limited links (4G) |
| **Extreme eco** | **Photo mode** — JPEG snapshot refreshed every *N* seconds (a few KB) | Substream | Very constrained 4G links |

Principles applied everywhere:

- 🔌 **Off-screen camera = zero connection.** Rotation and sequences close the previous
  streams before opening the next ones.
- 📉 **Photo mode** for saturated links: a tile drops from ~300 kbps continuous to a few
  KB per image.
- 🖥️ **Careful upscaling** of substreams (mpv `ewa_lanczossharp`) so they stay legible
  when enlarged.
- 🔒 **RTSP over TCP**, direct H.264/H.265 playback with no re-encoding.

## Installation

> **Requirements:** Python 3.11+ and **libmpv** (video engine).
> - *Windows*: place `libmpv-2.dll` in a `lib/` folder at the project root
>   (`mpv-dev-x86_64-…` archive from the [mpv builds](https://github.com/shinchiro/mpv-winbuild-cmake/releases)).
> - *Debian/Ubuntu*: `sudo apt install libmpv2` — *Fedora*: `sudo dnf install mpv-libs`.
> - *Optional:* `ffprobe` (from the `ffmpeg` package) improves failure diagnostics.

```bash
git clone https://github.com/Arcneell/rtsp-tool.git
cd rtsp-tool
pip install -r requirements.txt
python run.py
```

On first launch, the **Configuration** window opens so you can add sites and DVRs.

## Configuration

Everything is managed **in the interface** — no files to edit by hand:

1. **Add a site** (fiber or 4G).
2. **Add a DVR**: address + credentials, then automatic channel discovery (Hikvision)
   or manual generation (Dahua). All cameras are created at once.
3. Tick the cameras to display, build loops, set the rotation.

The configuration is stored in the user profile
(`%APPDATA%\RTSP-TOOL\config.yaml` on Windows,
`~/.config/rtsp-tool/config.yaml` on Linux). A `config.yaml` placed next to the
executable takes priority (**portable mode**, to ship a shared configuration).

> **Security note** — DVR passwords are never shown again in the interface and are
> obfuscated in the file. This is local obfuscation (against casual reading), *not*
> strong encryption: the key is embedded so the config stays deployable as-is. Use a
> **read-only** DVR account dedicated to the tool.

## Packaging & deployment

Full guide: **[packaging/DEPLOIEMENT.md](packaging/DEPLOIEMENT.md)** (build, Windows exe
signing, `.deb` build with icon and menu entry).

```bash
# Windows executable
pyinstaller --noconfirm --windowed --name RTSP-Tool --icon packaging/rtsp-tool.ico \
    --add-binary "lib/libmpv-2.dll;." run.py

# .deb package (via Docker, works from Windows too)
docker run --rm -v "${PWD}:/src" -w /src debian:12 bash packaging/build_deb.sh
```

## Architecture

```
rtsp_tool/
├── config.py             Data model + config.yaml file managed by the app
├── probe.py              RTSP failure classification (auth / timeout / network)
├── snapshot.py           JPEG snapshots (ISAPI/CGI) + Hikvision channel discovery
├── player.py             libmpv loading, low-latency RTSP settings, upscaling
└── ui/
    ├── main_window.py    Grid/single, rotation, loops, multi-monitor full screen
    ├── tile.py           Video tile: state, backoff, stop on 401, bitrate, snapshot
    ├── photo_tile.py     "Photo mode" tile (extreme-eco profile)
    ├── config_dialogs.py Sites, cameras, whole-DVR import
    ├── sequence_editor.py Loop editor
    └── icons.py          SVG icons
packaging/                .deb build, icon generation, deployment guide
```

**Design principles**

- One **libmpv instance per tile**, on an independent thread: a failing stream never
  affects the others.
- **Authentication failure = permanent stop of retries.** Since rotation and loops keep
  re-opening streams, a wrong password retried in a loop would lock the DVR account — the
  tool stops and reports it instead of hammering.
- **Exponential-backoff reconnection** (5 s → 10 min) for unstable 4G links.

## Tech stack

[Python 3.11+](https://www.python.org/) · [PySide6](https://doc.qt.io/qtforpython/) (Qt 6)
· [python-mpv](https://github.com/jaseg/python-mpv) (libmpv) · [PyYAML](https://pyyaml.org/)
· [requests](https://requests.readthedocs.io/).

## Roadmap

- [x] Grid / single views, bandwidth profiles, resilient reconnection
- [x] Photo mode (4G), automatic rotation, loop editor
- [x] ISAPI discovery, per-tile bitrate, multi-monitor, dark theme
- [x] Signed exe + `.deb` packaging with icon
- [ ] ONVIF discovery (brands beyond Hikvision/Dahua)
- [ ] Substream tuning directly from the tool (resolution / FPS / bitrate)

## License

Released under the **MIT** license — see [LICENSE](LICENSE).
