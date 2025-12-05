# yay-gui-manager — Install & Run

This folder contains GUI utilities for Arch-based OSes. The Yay GUI uses PyQt5; the updater uses Python's built‑in Tkinter.

Tools:
- yay_gui.py — Qt GUI for searching/installing packages and selective updates via `pacman`/`yay`.
- cachy_updater_gui.py — Tk GUI for updates (pacman + yay) in a simple table.

## Quick Setup (Linux)

Option A — One‑liner installer (recommended):

```
bash python/install_dependencies.sh
```

This will:
- Detect your distro and install system packages for Python, PyQt5, and Tkinter when possible.
- Fall back to `pip install` for PyQt5 using `python/requirements` if needed.
- Remind you to install `yay` (AUR helper) if not present.

Option B — Manual install (Arch / Manjaro / EndeavourOS / CachyOS):

- `sudo pacman -Syu --needed python python-pip python-pyqt5 tk`
- Install `yay` from AUR if missing:
  - `sudo pacman -S --needed base-devel git`
  - `git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si`

## Run the apps (Arch‑based)

- Yay GUI (Qt):
  - `python3 python/yay_gui.py`
  - Requires `pacman` and `yay` available in PATH.

- Cachy Updater GUI (Tk):
  - `python3 python/cachy_updater_gui.py`

Only the Qt manager and Tk updater are included.

## Notes & Tips

- Terminals: The Qt Yay GUI prefers `konsole` if available; otherwise it will try common terminals (kitty, xfce4-terminal, gnome-terminal, xterm, tilix, foot, wezterm). You can change `$TERMINAL` to influence the choice.
- Tkinter: On some distros, the Python stdlib Tkinter needs a system package (e.g. `tk` or `python3-tk`). The installer script handles common cases.
- Pip vs system packages: System packages for PyQt5 are preferred on Linux. The installer falls back to pip if the module import fails.
- AUR helper: The Qt Yay GUI calls `yay` for AUR actions. If you don’t use AUR, you can still use repo-only functionality via `pacman` operations in the UI.
