
  # YAY-GUI-MANAGER
<div align="center">
  <img src="https://files.catbox.moe/kd0wv5.png" alt="Yay GUI Manager logo" width="180"/>
  <p><em>Streamlining Package Management with Effortless Control</em></p>

  [![last-commit](https://img.shields.io/github/last-commit/ahmoodio/yay-gui-manager?style=flat&logo=git&logoColor=white&color=0080ff)](https://github.com/ahmoodio/yay-gui-manager)
  [![repo-top-language](https://img.shields.io/github/languages/top/ahmoodio/yay-gui-manager?style=flat&color=0080ff)](https://github.com/ahmoodio/yay-gui-manager)
  [![license](https://img.shields.io/github/license/ahmoodio/yay-gui-manager?style=flat&color=0080ff)](https://github.com/ahmoodio/yay-gui-manager/blob/main/LICENSE)
[![Arch Linux](https://img.shields.io/badge/Arch%20Linux-blue?logo=arch-linux\&logoColor=white)](https://archlinux.org/)
[![AUR Helper: yay](https://img.shields.io/badge/AUR%20Helper-yay-success?logo=arch-linux\&logoColor=white)](https://github.com/Jguer/yay)
  
  <p><em>Built with:</em></p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB.svg?style=flat&logo=Python&logoColor=white">
  <img alt="GNU Bash" src="https://img.shields.io/badge/GNU%20Bash-4EAA25.svg?style=flat&logo=GNU-Bash&logoColor=white">
  <img alt="Qt" src="https://img.shields.io/badge/Qt-41CD52.svg?style=flat&logo=Qt&logoColor=white">

  <p>
    <a href="#-demo-gifs">🎥 Demos</a> •
    <a href="#-features">✨ Features</a> •
    <a href="#-installation-arch--cachyos">📥 Installation</a> •
    <a href="#-desktop-launcher">🎛️ Desktop Launcher</a> •
    <a href="#-support">⭐ Support</a>
  </p>
</div>

---
</div>

## 🎥 Demo GIFs

### 🔍 [Search & Install](https://files.catbox.moe/2izcwr.gif)
<em>Search both repo + AUR and view descriptions in a side panel.</em>  
![Search Demo](https://files.catbox.moe/2izcwr.gif)

---

### 📦 [Installed Packages](https://files.catbox.moe/w32hbc.gif)
<em>Explicitly installed packages (pacman -Qe) with filter + batch uninstall.</em>  
![Installed Tab](https://files.catbox.moe/w32hbc.gif)

---

### 🔄 [Updates Tab](https://files.catbox.moe/u0i2h2.gif)
<em>Repo + AUR updates (yay -Qu / -Qua) with batch update tools.</em>  
![Updates Tab](https://files.catbox.moe/u0i2h2.gif)

<p align="right"><a href="#top"><b>↑ Back to Top</b></a></p>

---

# ✨ Features

- **3 main tabs:**
  - **Search & Install** – uses `pacman -Ss` and `yay -Ss --aur`
  - **Installed** – uses `pacman -Qe` to list explicitly installed packages
  - **Updates** – uses `yay -Qu` and `yay -Qua`
- **Multi-select:** Install / uninstall / update using checkboxes
- **Package details:** Side panel with description and URL (`pacman -Si`, `yay -Si --aur`)
- **External terminal integration:**
  - Prefers **Konsole**
  - Falls back to kitty / xfce4-terminal / gnome-terminal / tilix / xterm / wezterm / kgx / foot
- **Session Control:** Optional “keep Konsole open after command finishes”
- **Debugging:** Crash log written to `/tmp/yay_gui_error.log`

<p align="right"><a href="#top"><b>↑ Back to Top</b></a></p>

---

# 📥 Installation ([Arch](https://archlinux.org/) / [CachyOS](https://cachyos.org/))

Easiest most forward way is using [yay](https://github.com/Jguer/yay):
```bash
yay -S yay-gui-manager-git
```
### Or you can do it manualy:

Install runtime dependencies from [pacman](https://wiki.archlinux.org/title/Pacman) (no pip required):

```bash
sudo pacman -Syu --needed python python-pyqt5 yay git base-devel
```

Then clone and run:

```bash
git clone https://github.com/ahmoodio/yay-gui-manager.git
cd yay-gui-manager
python yay_gui.py
```

Make it executable:

```bash
chmod +x yay_gui.py
./yay_gui.py
```
<p align="right"><a href="#top"><b>↑ Back to Top</b></a></p>



# 🎛️ Desktop Launcher

To have <strong>[Yay GUI Manager](https://github.com/ahmoodio/yay-gui-manager/)</strong> appear in your app menu:

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




# 🧩 Development (Optional [venv](https://docs.python.org/3/library/venv.html))

If you prefer to use a virtual environment and [pip](https://pypi.org/project/pip/):

```bash
python -m venv .venv
source .venv/bin/activate   # or: source .venv/bin/activate.fish
pip install -r requirements
python yay_gui.py
```

The <code>requirements</code> file is minimal and only lists <code>PyQt5</code>.

> ⚠️ On Arch, avoid using system-wide <code>pip</code> due to PEP 668. Prefer pacman for system packages.

<p align="right"><a href="#top"><b>↑ Back to Top</b></a></p>




# 📄 License

MIT License. See <code>[LICENSE](https://github.com/ahmoodio/yay-gui-manager/blob/main/LICENSE)</code>.

<p align="right"><a href="#top"><b>↑ Back to Top</b></a></p>




# ⭐ Support

If you find this useful, please ⭐ the repo and share feedback / PRs.

<p align="right"><a href="#top"><b>↑ Back to Top</b></a></p>
