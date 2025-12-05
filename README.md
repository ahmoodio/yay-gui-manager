<p align="center">
  <img src="desktop/yay-gui.png" alt="Yay GUI Manager logo" width="180"/>
</p>

<h1 align="center">Yay GUI Manager – Rebuilt</h1>

A modern, fast, and user-friendly graphical interface for **yay** on Arch-based systems.

---

## 🎥 Demo GIFs

### 🔍 Search & Install
![Search](https://s6.ezgif.com/tmp/ezgif-65dc73a013a38c94.gif)

### 📦 Installed Packages
![Installed](https://s6.ezgif.com/tmp/ezgif-6731420813f92e67.gif)

### 🔄 Updates
![Updates](https://s6.ezgif.com/tmp/ezgif-6d68827d82fa3940.gif)

---

## 🧩 Desktop Launcher Installation

### Automatic installation (recommended)

Run:

```bash
./install-desktop.sh
```

This script will:

- Copy the `.desktop` launcher into `~/.local/share/applications/`
- Copy the icon into the correct system icon directory
- Auto‑detect the correct `Exec=` path
- Refresh icon & desktop databases  
- Make the app show up in your system menu

### Manual installation

```bash
cp desktop/yay-gui.desktop ~/.local/share/applications/
cp desktop/yay-gui.png ~/.local/share/icons/hicolor/256x256/apps/
```

---

## 🛠 install-desktop.sh Script

```bash
#!/usr/bin/env bash
# install-desktop.sh

set -e
APP_ID="yay-gui"
DESKTOP_SOURCE="desktop/yay-gui.desktop"
ICON_SOURCE="desktop/yay-gui.png"

DESKTOP_TARGET="${HOME}/.local/share/applications/${APP_ID}.desktop"
ICON_TARGET="${HOME}/.local/share/icons/hicolor/256x256/apps/${APP_ID}.png"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$(dirname "${DESKTOP_TARGET}")"
mkdir -p "$(dirname "${ICON_TARGET}")"

cp "${SCRIPT_DIR}/${DESKTOP_SOURCE}" "${DESKTOP_TARGET}"
cp "${SCRIPT_DIR}/${ICON_SOURCE}" "${ICON_TARGET}"

if command -v yay-gui-manager >/dev/null 2>&1; then
  EXEC_CMD="yay-gui-manager"
else
  EXEC_CMD="/usr/bin/python3 ${SCRIPT_DIR}/python/yay_gui.py"
fi

ESCAPED_EXEC_CMD=$(printf '%s
' "${EXEC_CMD}" | sed 's/[&/\]/\&/g')
sed -i "s|^Exec=.*$|Exec=${ESCAPED_EXEC_CMD}|" "${DESKTOP_TARGET}"

update-desktop-database "${HOME}/.local/share/applications" || true
gtk-update-icon-cache -q -t -f "${HOME}/.local/share/icons/hicolor" || true

echo "Launcher installed!"
```

---

## 📄 License

Included in LICENSE file.
