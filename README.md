<p align="center">
  <img src="[desktop/yay-gui.png](https://cdn.discordapp.com/attachments/1316059512947474524/1446743829444165703/ChatGPT_Image_Dec_5_2025_11_48_48_PM.png?ex=693518b0&is=6933c730&hm=96d0bca8546af8185f68215047f28f2e437ebb34ea57959a65e97de745bdecea&)" alt="Yay GUI Manager logo" width="180"/>
</p>

<h1 align="center">Yay GUI Manager – Rebuilt</h1>

A modern, fast, and user-friendly graphical interface for **yay** on Arch-based systems.

---

## 🎥 Demo GIFs

### 🔍 Search & Install
![Search]([https://s6.ezgif.com/tmp/ezgif-65dc73a013a38c94.gif](https://media.discordapp.net/attachments/1316059512947474524/1446727609940447433/68747470733a2f2f73362e657a6769662e636f6d2f746d702f657a6769662d363564633733613031336133386339342e676966.gif?ex=69350995&is=6933b815&hm=5877fc53645bf77fd5dd4817635b616a236547336173bcc0bb7afbe89815a845&=))

### 📦 Installed Packages
![Installed]([https://s6.ezgif.com/tmp/ezgif-6731420813f92e67.gif](https://media.discordapp.net/attachments/1316059512947474524/1446727610401816697/68747470733a2f2f73362e657a6769662e636f6d2f746d702f657a6769662d363733313432303831336639326536372e676966.gif?ex=69350995&is=6933b815&hm=480b18be8da1ef9a4af97014dd12e208da7901134201a1540c319615e6d7e4da&=))

### 🔄 Updates
![Updates]([https://s6.ezgif.com/tmp/ezgif-6d68827d82fa3940.gif](https://media.discordapp.net/attachments/1316059512947474524/1446727610787954749/68747470733a2f2f73362e657a6769662e636f6d2f746d702f657a6769662d366436383832376438326661333934302e676966.gif?ex=69350995&is=6933b815&hm=b9527042542c7746eda690c9db150d98365d6580c8e76339b1fa001b0e47114f&=))

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
