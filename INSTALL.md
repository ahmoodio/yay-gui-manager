# Yay GUI — Install & Run (Arch‑based)

Copy and paste everything below into a terminal:

```
sudo pacman -Syu --needed python python-pip python-pyqt5 git base-devel && \
if ! command -v yay >/dev/null 2>&1; then \
  git clone https://aur.archlinux.org/yay.git && (cd yay && makepkg -si); \
fi && \
git clone https://github.com/ahmoodio/yay-gui-manager.git && \
cd yay-gui-manager && \
pip3 install --user -r python/requirements && \
chmod +x python/yay_gui.py && \
./python/yay_gui.py
```

