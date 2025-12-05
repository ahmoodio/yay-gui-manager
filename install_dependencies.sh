#!/usr/bin/env bash
set -euo pipefail

# Simple cross-distro installer for Python deps used by the GUI tools here.
#
# - Prefers system packages for Qt/tk bindings when available
# - Falls back to pip for PyQt5 if needed
#
# Usage:
#   bash python/install_dependencies.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

have_cmd() { command -v "$1" >/dev/null 2>&1; }

info() { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[ERR ]\033[0m %s\n" "$*"; }

install_arch() {
  info "Detected Arch-based distro. Installing system packages..."
  sudo pacman -Syu --needed python python-pip python-pyqt5 tk || true
}

install_debian() {
  info "Detected Debian/Ubuntu-based distro. Installing system packages..."
  sudo apt update
  sudo apt install -y python3 python3-pip python3-pyqt5 python3-tk || true
}

install_fedora() {
  info "Detected Fedora/RHEL-based distro. Installing system packages..."
  sudo dnf install -y python3 python3-pip python3-qt5 python3-tkinter || true
}

detect_and_install_system() {
  if [[ -r /etc/os-release ]]; then
    . /etc/os-release || true
    ID_LIKE_LOWER="${ID_LIKE:-}"; ID_LIKE_LOWER="${ID_LIKE_LOWER,,}"
    ID_LOWER="${ID:-}"; ID_LOWER="${ID_LOWER,,}"

    case "${ID_LOWER}" in
      arch|endeavouros|manjaro|garuda) install_arch; return ;;
    esac
    case "${ID_LIKE_LOWER}" in
      *arch*) install_arch; return ;;
      *debian*|*ubuntu*) install_debian; return ;;
      *rhel*|*fedora*|*centos*) install_fedora; return ;;
    esac
  fi

  warn "Could not detect distro. Skipping system package install."
}

ensure_pip_pyqt5() {
  local py="python3"
  if ! have_cmd "$py"; then
    err "python3 not found. Please install Python 3 and re-run."
    exit 1
  fi
  if "$py" - <<'PY' >/dev/null 2>&1; then
import PyQt5
PY
  then
    info "PyQt5 is already available (system or site-packages)."
  else
    info "Installing PyQt5 with pip (fallback)..."
    if have_cmd pip3; then
      pip3 install --user -r "$ROOT_DIR/requirements"
    else
      err "pip3 not found. Install pip or install PyQt5 via your package manager."
    fi
  fi
}

main() {
  detect_and_install_system
  ensure_pip_pyqt5

  if ! have_cmd yay; then
    warn "'yay' AUR helper is not installed. The Qt updater (yay_gui.py) calls 'yay'."
    warn "On Arch-based systems you can install it via AUR, e.g.:"
    cat <<'EOS'
  sudo pacman -S --needed base-devel git
  git clone https://aur.archlinux.org/yay.git
  cd yay && makepkg -si
EOS
  fi

  info "All done. To run the Qt GUI:"
  cat <<'EOS'
  python3 python/yay_gui.py
EOS
}

main "$@"

