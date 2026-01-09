# YAY-GUI-MANAGER

<div align="center">
  <img src="https://files.catbox.moe/kd0wv5.png" alt="Yay GUI Manager logo" width="180"/>
  <p><em>Streamlining Package Management with Effortless Control</em></p>

  [![last-commit](https://img.shields.io/github/last-commit/ahmoodio/yay-gui-manager?style=flat&logo=git&logoColor=white&color=0080ff)](https://github.com/ahmoodio/yay-gui-manager)
  [![repo-top-language](https://img.shields.io/github/languages/top/ahmoodio/yay-gui-manager?style=flat&color=0080ff)](https://github.com/ahmoodio/yay-gui-manager)
  [![license](https://img.shields.io/github/license/ahmoodio/yay-gui-manager?style=flat&color=0080ff)](https://github.com/ahmoodio/yay-gui-manager/blob/main/LICENSE)

  <p><em>Built with:</em></p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB.svg?style=flat&logo=Python&logoColor=white">
  <img alt="GNU Bash" src="https://img.shields.io/badge/GNU%20Bash-4EAA25.svg?style=flat&logo=GNU-Bash&logoColor=white">
  <img alt="Qt" src="https://img.shields.io/badge/Qt-41CD52.svg?style=flat&logo=Qt&logoColor=white">
</div>



# 🎥 Demo GIFs

### 🔍 Search & Install  
<em>Search both repo + AUR and view descriptions in a side panel.</em>  
![Search Demo](https://files.catbox.moe/2izcwr.gif)

---

### 📦 Installed Packages  
<em>Explicitly installed packages (pacman -Qe) with filter + batch uninstall.</em>  
![Installed Tab](https://files.catbox.moe/w32hbc.gif)

---

### 🔄 Updates Tab  
<em>Repo + AUR updates (yay -Qu / -Qua) with batch update tools.</em>  
![Updates Tab](https://files.catbox.moe/u0i2h2.gif)

---

# ✨ Features

- 3 main tabs:
  - <strong>Search & Install</strong> – uses <code>pacman -Ss</code> and <code>yay -Ss --aur</code>
  - <strong>Installed</strong> – uses <code>pacman -Qe</code> to list explicitly installed packages
  - <strong>Updates</strong> – uses <code>yay -Qu</code> and <code>yay -Qua</code>
- Multi-select install / uninstall / update using checkboxes
- Package details panel with description and URL (<code>pacman -Si</code>, <code>yay -Si --aur</code>)
- External terminal integration:
  - Prefers Konsole
  - Falls back to kitty / xfce4-terminal / gnome-terminal / tilix / xterm / wezterm / kgx / foot
- Optional “keep Konsole open after command finishes”
- Crash log written to <code>/tmp/yay_gui_error.log</code>

---

# 📥 Installation (Arch / CachyOS)

Easiest most forward way is using (yay):
```bash
yay -S yay-gui-manager-git
```


Install runtime dependencies from pacman (no pip required):

```bash
sudo pacman -Syu --needed python python-pyqt5 yay git base-devel
```

Then clone and run:

```bash
git clone https://github.com/ahmoodio/yay-gui-manager.git
cd yay-gui-manager
python yay_gui.py
```

Or make it executable:

```bash
chmod +x yay_gui.py
./yay_gui.py
```

---

# 🎛️ Desktop Launcher

To have <strong>Yay GUI Manager</strong> appear in your app menu:

### Automatic (recommended)

From the repo root:

```bash
chmod +x install-desktop.sh
./install-desktop.sh
```

This will:

- Copy <code>desktop/yay-gui.desktop</code> → <code>~/.local/share/applications/</code>
- Look for an icon at <code>desktop/yay-gui.png</code> and, if present, copy it to:
  - <code>~/.local/share/icons/hicolor/256x256/apps/yay-gui.png</code>
- Set <code>Exec=</code> to:
  - <code>yay-gui-manager</code> if installed via package, or
  - <code>/usr/bin/python3 /absolute/path/yay_gui.py</code> for a local clone
- Refresh the desktop + icon caches (if available)

> 💡 To use your logo, save it as <code>desktop/yay-gui.png</code> in the repo.

### Manual

```bash
cp desktop/yay-gui.desktop ~/.local/share/applications/
# Optional icon (if you add desktop/yay-gui.png)
cp desktop/yay-gui.png ~/.local/share/icons/hicolor/256x256/apps/
```

---

# 🧩 Development (Optional venv)

If you prefer to use a virtual environment and pip:

```bash
python -m venv .venv
source .venv/bin/activate   # or: source .venv/bin/activate.fish
pip install -r requirements
python yay_gui.py
```

The <code>requirements</code> file is minimal and only lists <code>PyQt5</code>.

> ⚠️ On Arch, avoid using system-wide <code>pip</code> due to PEP 668. Prefer pacman for system packages.

---


# 📄 License

MIT License. See <code>LICENSE</code>.

---

# ⭐ Support

If you find this useful, please ⭐ the repo and share feedback / PRs.
