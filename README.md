<p align="center">
  <img src="https://i.imgur.com/P2NBMK4.png" alt="Yay GUI Manager logo" width="180"/>
</p>

<h1 align="center">Yay GUI Manager – Rebuilt</h1>

A modern, fast, and user-friendly graphical interface for **yay** on Arch-based systems.

---

## 🎥 Demo GIFs

### 🔍 Search & Install
![Search]([https://s6.ezgif.com/tmp/ezgif-65dc73a013a38c94.gif](https://media.discordapp.net/attachments/1316059512947474524/1446727609940447433/68747470733a2f2f73362e657a6769662e636f6d2f746d702f657a6769662d363564633733613031336133386339342e676966.gif?ex=69350995&is=6933b815&hm=5877fc53645bf77fd5dd4817635b616a236547336173bcc0bb7afbe89815a845&=))

### 📦 Installed Packages
![Installed]([https://s6.ezgif.com/tmp/ezgif-6731420813f92e67.gif)]((https://media.discordapp.net/attachments/1316059512947474524/1446727610401816697/68747470733a2f2f73362e657a6769662e636f6d2f746d702f657a6769662d363733313432303831336639326536372e676966.gif?ex=69350995&is=6933b815&hm=480b18be8da1ef9a4af97014dd12e208da7901134201a1540c319615e6d7e4da&=))

### 🔄 Updates
![Updates]([https://s6.ezgif.com/tmp/ezgif-6d68827d82fa3940.gif](https://media.discordapp.net/attachments/1316059512947474524/1446727610787954749/68747470733a2f2f73362e657a6769662e636f6d2f746d702f657a6769662d366436383832376438326661333934302e676966.gif?ex=69350995&is=6933b815&hm=b9527042542c7746eda690c9db150d98365d6580c8e76339b1fa001b0e47114f&=)

## 🛠️ Development

---

```bash
git clone https://github.com/ahmoodio/yay-gui-manager.git
cd yay-gui-manager
pip install --user -r python/requirements
./python/yay_gui.py
```

Feel free to open issues or PRs for:

- New views or filters  
- Better error handling and logging  
- Translations / localization  
- AppImage / Flatpak / PKGBUILD packaging  

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

---

## ⚠️ Disclaimer  

This is a GUI wrapper around `yay`. Always check what will be installed or removed, and review AUR PKGBUILDs as you normally would in the terminal.

---

## 📄 License

Included in LICENSE file.

---

## ⭐ Support  

If you find this useful, please ⭐ the repo!
