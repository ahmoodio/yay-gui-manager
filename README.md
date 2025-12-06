<p align="center">
  <img src="https://cdn.discordapp.com/attachments/1316059512947474524/1446743829444165703/ChatGPT_Image_Dec_5_2025_11_48_48_PM.png?ex=693518b0&is=6933c730&hm=96d0bca8546af8185f68215047f28f2e437ebb34ea57959a65e97de745bdecea&" alt="Yay GUI Manager logo" width="180"/>
</p>

<h1 align="center">Yay GUI Manager – Rebuilt</h1>

A <strong>fast</strong>, <strong>modern</strong>, and <strong>Konsole-integrated</strong> GUI for the <code>yay</code> AUR helper.  
Built with <strong>Python + PyQt5</strong>, with real-time streaming parsing for search, installed packages, and updates.

---


# 🎥 Demo GIFs

### 🔍 Search & Install  
*Search both repo + AUR and view descriptions in a side panel.*  
▶️ [Watch Search Demo (WEBM)](https://cdn.discordapp.com/attachments/1316059512947474524/1446751025208758426/Screencast_20251205_231254.webm?ex=69351f63&is=6933cde3&hm=59f74ec480d6429753c9868086da29be586dd769d6fda16c696a6b4d89dd8b8f&)

---

### 📦 Installed Packages  
<em>Explicitly installed packages (pacman -Qe) with filter + batch uninstall.</em>  
![Installed Tab](https://media.discordapp.net/attachments/1316059512947474524/1446727610401816697/68747470733a2f2f73362e657a6769662e636f6d2f746d702f657a6769662d363733313432303831336639326536372e676966.gif?ex=69350995&is=6933b815&hm=480b18be8da1ef9a4af97014dd12e208da7901134201a1540c319615e6d7e4da&=)

---

### 🔄 Updates Tab  
<em>Repo + AUR updates (yay -Qu / -Qua) with batch update tools.</em>  
![Updates Tab](https://media.discordapp.net/attachments/1316059512947474524/1446727610787954749/68747470733a2f2f73362e657a6769662e636f6d2f746d702f657a6769662d366436383832376438326661333934302e676966.gif?ex=69350995&is=6933b815&hm=b9527042542c7746eda690c9db150d98365d6580c8e76339b1fa001b0e47114f&=)


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

# 📦 AUR Packaging (yay-gui-manager-git)

This repo can be packaged for the AUR using the provided <code>PKGBUILD</code> and <code>yay-gui-manager-git.install</code>.  
The package installs:

- <code>/usr/bin/yay-gui-manager</code> → wrapper for <code>yay_gui.py</code>
- <code>/usr/share/applications/yay-gui.desktop</code>
- <code>/usr/share/icons/hicolor/256x256/apps/yay-gui.png</code> (you must provide the PNG when packaging)
- License under <code>/usr/share/licenses/yay-gui-manager-git/</code>

---

# 📄 License

MIT License. See <code>LICENSE</code>.

---

# ⭐ Support

If you find this useful, please ⭐ the repo and share feedback / PRs.
