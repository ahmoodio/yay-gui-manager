# BetterSniff Python Tools — Install & Run

This folder contains several small GUI utilities. The Yay GUI uses PyQt5; the others use Python's built‑in Tkinter.

Tools:
- yay_gui.py — Qt GUI for searching/installing packages and selective updates via `pacman`/`yay`.
- cachy_updater_gui.py — Tk GUI for updates (pacman + yay) in a simple table.
- givemebadge_gui.py — Tk GUI helper to run a Python project in a venv.
- btd_gui.py — Tk GUI helper for BetterDiscord actions.
- gpu-recorder-control.py — Tk GUI to start/stop the `gpu-screen-recorder-ui` user service.

## Quick Setup (Linux)

Option A — One‑liner installer (recommended):

```
bash python/install_dependencies.sh
```

This will:
- Detect your distro and install system packages for Python, PyQt5, and Tkinter when possible.
- Fall back to `pip install` for PyQt5 using `python/requirements` if needed.
- Remind you to install `yay` (AUR helper) if not present.

Option B — Manual install by distro:

- Arch / Manjaro / EndeavourOS:
  - `sudo pacman -Syu --needed python python-pip python-pyqt5 tk`
  - Install `yay` from AUR if you need the Yay GUI:
    - `sudo pacman -S --needed base-devel git`
    - `git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si`

- Debian / Ubuntu:
  - `sudo apt update && sudo apt install -y python3 python3-pip python3-pyqt5 python3-tk`
  - If you want to try pip for Qt: `pip3 install -r python/requirements`

- Fedora:
  - `sudo dnf install -y python3 python3-pip python3-qt5 python3-tkinter`
  - Optional pip fallback: `pip3 install -r python/requirements`

## Run the apps

- Yay GUI (Qt):
  - `python3 python/yay_gui.py`
  - Requires `pacman` and `yay` available in PATH.

- Cachy Updater GUI (Tk):
  - `python3 python/cachy_updater_gui.py`

- GiveMeBadge VENV Runner (Tk):
  - `python3 python/givemebadge_gui.py`

- BetterDiscord GUI (Tk):
  - `python3 python/btd_gui.py`

- GPU Screen Recorder UI Service Control (Tk):
  - `python3 python/gpu-recorder-control.py`

## Notes & Tips

- Terminals: The Qt Yay GUI prefers `konsole` if available; otherwise it will try common terminals (kitty, xfce4-terminal, gnome-terminal, xterm, tilix, foot, wezterm). You can change `$TERMINAL` to influence the choice.
- Tkinter: On some distros, the Python stdlib Tkinter needs a system package (e.g. `tk` or `python3-tk`). The installer script handles common cases.
- Pip vs system packages: System packages for PyQt5 are preferred on Linux. The installer falls back to pip if the module import fails.
- AUR helper: The Qt Yay GUI calls `yay` for AUR actions. If you don’t use AUR, you can still use repo-only functionality via `pacman` operations in the UI.

