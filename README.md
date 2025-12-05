# BetterSniff Python GUIs

This folder contains small desktop helpers (Qt and Tk). The main one is `yay_gui.py`, a Qt GUI for searching/installing packages and selective updates using `pacman` and `yay`.

- Qt: `yay_gui.py`
- Tk: `cachy_updater_gui.py`, `givemebadge_gui.py`, `btd_gui.py`, `gpu-recorder-control.py`

## Quick Start (Arch/Manjaro/EndeavourOS)

Clone and install dependencies, then run the Qt GUI:

```
# 1) Clone this repo
# (replace URL with your GitHub repo when publishing)
 git clone <your-repo-url>.git
 cd <your-repo>/

# 2) Install system deps (Python, PyQt5, Tk)
 sudo pacman -Syu --needed python python-pip python-pyqt5 tk

# 3) Install yay if missing (AUR helper)
 sudo pacman -S --needed base-devel git
 git clone https://aur.archlinux.org/yay.git
 cd yay && makepkg -si && cd -

# 4) (Optional) Pip fallback if PyQt5 missing for some reason
 pip3 install --user -r python/requirements

# 5) Run the Qt GUI
 python3 python/yay_gui.py
```

Notes:
- The Qt GUI prefers `konsole`; otherwise it will try common terminals (kitty, xfce4-terminal, gnome-terminal, xterm, tilix, foot, wezterm).
- `yay_gui.py` uses `pacman` for repo metadata and `yay` for AUR actions.

## Other Distros

Debian/Ubuntu:
```
sudo apt update
sudo apt install -y python3 python3-pip python3-pyqt5 python3-tk
pip3 install --user -r python/requirements   # optional fallback
python3 python/yay_gui.py
```

Fedora:
```
sudo dnf install -y python3 python3-pip python3-qt5 python3-tkinter
pip3 install --user -r python/requirements   # optional fallback
python3 python/yay_gui.py
```

## Run Other Tools

- Tk updater (pacman + yay):
```
python3 python/cachy_updater_gui.py
```

- GiveMeBadge venv runner:
```
python3 python/givemebadge_gui.py
```

- BetterDiscord helper:
```
python3 python/btd_gui.py
```

- GPU Screen Recorder UI service control:
```
python3 python/gpu-recorder-control.py
```

## One‑Command Installer

A convenience script is included to detect your distro and install dependencies. It prefers system packages, and falls back to pip for PyQt5 when needed.

```
bash python/install_dependencies.sh
```

See also: python/INSTALL.md for more background and tips.
