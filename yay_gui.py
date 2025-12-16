#!/usr/bin/env python3
import sys
import os
import re
import shutil
import subprocess
import shlex

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QStatusBar, QHeaderView, QTextEdit,
    QTabWidget, QFrame, QLabel,
    QComboBox, QCheckBox, QFileDialog, QToolButton, QDialog
)
from PyQt5.QtCore import Qt, QProcess, QSettings, QSize
from PyQt5.QtGui import QIcon


# ---- Crash logging ----
def _install_exception_hook():
    import traceback

    def handle_exception(exc_type, exc_value, exc_tb):
        log_path = "/tmp/yay_gui_error.log"
        try:
            with open(log_path, "w") as f:
                f.write(''.join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        except Exception:
            pass
        traceback.print_exception(exc_type, exc_value, exc_tb)
        try:
            QMessageBox.critical(None, "Unexpected Error",
                                 f"A crash log was written to: {log_path}")
        except Exception:
            pass

    sys.excepthook = handle_exception


# ---- Helpers ----
def clean_control_codes(text: str) -> str:
    """Strip ANSI escape sequences including OSC8 hyperlinks.

    - CSI: ESC [ ... cmd
    - OSC: ESC ] ... BEL or ESC \\
    - Single-char escapes: ESC followed by @-Z, \\ or _
    """
    ansi_re = re.compile(
        r"\x1B("               # ESC
        r"\[[0-?]*[ -/]*[@-~]"  # CSI sequence
        r"|\][^\x07\x1B]*(?:\x07|\x1B\\)"  # OSC sequence terminated by BEL or ST
        r"|[@-Z\\-_]"           # 2-char sequences
        r")"
    )
    return ansi_re.sub('', text)


def parse_yay_search(output: str):
    packages = []
    current = None
    header_re = re.compile(r'^(?P<repo>[^/\s]+)/(?P<name>\S+)\s+(?P<ver>.+)$')
    for raw in output.splitlines():
        line = clean_control_codes(raw)
        if not line or line.startswith('::'):
            continue
        m = header_re.match(line)
        if m:
            if current:
                packages.append(current)
            current = {
                'repo': m.group('repo'),
                'name': m.group('name'),
                'version': m.group('ver').strip(),
                'description': ''
            }
            continue
        if line.startswith(' ') and current:
            current['description'] += line.strip() + ' '
            continue
        if current:
            packages.append(current)
            current = None
    if current:
        packages.append(current)
    for p in packages:
        p['description'] = p['description'].strip()
    return packages


def parse_yay_installed(output: str):
    packages = []
    for raw in output.splitlines():
        line = clean_control_codes(raw).strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            packages.append({'name': parts[0], 'version': parts[1]})
    return packages


def parse_yay_updates(output: str):
    """Parse lines like: 'pkg 1.0-1 -> 1.1-1' into dicts."""
    packages = []
    upd_re = re.compile(r'^(?P<name>\S+)\s+(?P<old>\S+)\s+->\s+(?P<new>\S+)\s*$')
    for raw in output.splitlines():
        line = clean_control_codes(raw).strip()
        if not line or line.startswith('::'):
            continue
        m = upd_re.match(line)
        if m:
            packages.append({
                'name': m.group('name'),
                'old': m.group('old'),
                'new': m.group('new')
            })
    return packages


def parse_si_desc_url(output: str):
    """Extract Description and URL from `pacman -Si` / `yay -Si` output.

    Returns a tuple (description, url). Missing fields return as empty strings.
    """
    desc = ''
    url = ''
    for raw in output.splitlines():
        line = clean_control_codes(raw).strip()
        if not line or ':' not in line:
            continue
        # Split only on the first ':' to preserve values that contain ':'
        key, val = line.split(':', 1)
        key = key.strip().lower()
        val = val.strip()
        if key == 'description' and val:
            desc = val
        elif key == 'url' and val:
            url = val
    return desc, url


class TerminalLauncher:
    def __init__(self):
        self.detected = self._detect_terminal()

    def _detect_terminal(self):
        # Always prefer Konsole when available (ignore $TERMINAL if it is alacritty)
        if shutil.which('konsole'):
            return 'konsole'

        term_env = os.environ.get('TERMINAL')
        if term_env and shutil.which(term_env) and os.path.basename(term_env).lower() != 'alacritty':
            return term_env

        # Fallbacks, explicitly excluding alacritty per user request
        for name in (
            'kitty', 'xfce4-terminal', 'gnome-terminal', 'kgx',
            'xterm', 'tilix', 'foot', 'wezterm'
        ):
            if shutil.which(name):
                return name
        return None

    def build(self, cmd_str: str):
        term = self.detected
        if not term:
            return None
        name = os.path.basename(term).lower()
        # Keep open on success and failure
        script = (
            f"{cmd_str} && echo \"\\nOperation Complete! Press Enter to close.\" && read -r "
            f"|| (echo \"\\nCommand failed; opening interactive shell.\"; exec bash)"
        )
        if name in ('alacritty', 'kitty', 'konsole', 'xterm', 'tilix', 'foot', 'wezterm'):
            return [term, '-e', 'bash', '-lc', script]
        if name in ('xfce4-terminal',):
            return [term, '--hold', '-x', 'bash', '-lc', script]
        if name in ('gnome-terminal', 'kgx'):
            return [term, '--', 'bash', '-lc', script]
        return [term, '-e', 'bash', '-lc', script]

    def run(self, cmd_str: str):
        args = self.build(cmd_str)
        if not args:
            raise RuntimeError('No terminal emulator found. Install alacritty/kitty/xterm, or set $TERMINAL.')
        env = os.environ.copy()
        env.pop('SUDO_ASKPASS', None)
        env.pop('SSH_ASKPASS', None)
        if os.path.basename(args[0]).lower() == 'alacritty':
            env['ALACRITTY_CONFIG_FILE'] = '/dev/null'
            env.setdefault('ALACRITTY_LOG', '/tmp/alacritty-yaygui.log')
        subprocess.Popen(args, env=env)

    def run_konsole_direct(self, program_args, keep_open=False):
        """Run a program in Konsole.

        If keep_open is True, wrap the command in a login shell that pauses after
        completion so the window does not close immediately.
        """
        if not shutil.which('konsole'):
            raise RuntimeError('Konsole is not installed.')
        if keep_open:
            quoted = ' '.join(shlex.quote(a) for a in program_args)
            # Run via bash -lc so PATH/env are correct and pause afterwards
            cmd = ['konsole', '-e', 'bash', '-lc', f"{quoted}; echo; read -r"]
        else:
            cmd = ['konsole', '-e', *program_args]
        env = os.environ.copy()
        # Avoid askpass interferance; let yay/sudo handle prompts in the TTY
        env.pop('SUDO_ASKPASS', None)
        env.pop('SSH_ASKPASS', None)
        subprocess.Popen(cmd, env=env)


class YayGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Yay GUI - Rebuilt')
        self.resize(1200, 800)

        self.term = TerminalLauncher()

        self.search_proc = None
        self.installed_proc = None
        self.search_buffer = ''
        self.installed_buffer = ''
        self.upd_proc = None
        self.upd_stage = None  # 'repo' or 'aur'
        self.upd_repo_buf = ''
        self.upd_aur_buf = ''
        # Streaming helpers
        self._search_stream_pending = ''
        self._search_stream_current = None
        self._search_stream_item = None
        self._search_header_re = re.compile(r'^(?P<repo>[^/\s]+)/(?P<name>\S+)\s+(?P<ver>.+)$')
        self._upd_line_re = re.compile(r'^(?P<name>\S+)\s+(?P<old>\S+)\s+->\s+(?P<new>\S+)\s*$')
        self._repo_pending = ''
        self._aur_pending = ''
        self._repo_done = False
        self._aur_done = False
        self._repo_count = 0
        self._aur_count = 0
        # Installed streaming
        self._installed_pending = ''
        self._installed_count = 0
        self._installed_max_items = 5000
        self._active_inst_procs = []
        self._inst_pending = {}
        self._inst_source_by_proc = {}
        # Optional cap to keep UI snappy on huge searches
        self._search_max_items = 500
        # Parallel search state
        self._active_search_procs = []
        self._search_pending = {'repo': '', 'aur': ''}
        self._search_ctx = {
            'repo': {'current': None, 'item': None},
            'aur': {'current': None, 'item': None}
        }
        self._search_done = {'repo': True, 'aur': True}
        # Details fetch state
        self._info_procs = {}
        self._info_buffers = {}
        self._current_info_key = None
        # Installed names cache for hiding already-installed from search
        self._installed_names = set()
        self._installed_names_ready = False
        self._installed_names_buf = ''
        self._installed_names_proc = None
        self._pending_search_term = None

        # ----- Root layout with top-right Settings gear and tabs -----
        root = QVBoxLayout(self)
        topbar = QHBoxLayout()
        topbar.addStretch(1)
        self.settings_btn = QToolButton()
        icon = QIcon.fromTheme('preferences-system')
        if not icon.isNull():
            self.settings_btn.setIcon(icon)
        else:
            self.settings_btn.setText('⚙')
            self.settings_btn.setStyleSheet('font-size: 22px; padding: 0px;')
        self.settings_btn.setToolTip('Open Settings')
        self.settings_btn.setAutoRaise(True)
        # Make the gear more prominent
        self.settings_btn.setIconSize(QSize(32, 32))
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.clicked.connect(self._open_settings_dialog)
        topbar.addWidget(self.settings_btn)
        root.addLayout(topbar)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # Build tabs and keep references/indices for behavior hooks
        self.search_tab = self._build_search_tab()
        self.installed_tab = self._build_installed_tab()
        self.update_tab = self._build_update_tab()

        self.tabs.addTab(self.search_tab, 'Search & Install')
        self.installed_tab_index = self.tabs.addTab(self.installed_tab, 'Installed Packages')
        self.update_tab_index = self.tabs.addTab(self.update_tab, 'Update')

        # Auto-load installed packages when the Installed tab is first opened
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # ---- Settings ----
        self.keep_konsole_open = True

        # ---- Updates deduplication set ----
        self._updates_seen = set()  # (source, name)

        # Load saved settings and apply theme
        self._load_settings()

        # Preload installed names so search can hide installed packages
        try:
            self._refresh_installed_names()
        except Exception:
            pass

    # ---- Graceful shutdown ----
    def closeEvent(self, event):
        # Stop/cleanup any running processes to avoid late signals hitting deleted widgets
        try:
            for proc in list(getattr(self, '_active_search_procs', []) or []):
                try:
                    if proc.state() != QProcess.NotRunning:
                        proc.kill(); proc.waitForFinished(500)
                except Exception:
                    pass
            self._active_search_procs = []
        except Exception:
            pass
        try:
            # Stop any installed-tab processes
            for proc in list(getattr(self, '_active_inst_procs', []) or []):
                try:
                    if proc.state() != QProcess.NotRunning:
                        proc.kill(); proc.waitForFinished(500)
                except Exception:
                    pass
            self._active_inst_procs = []
            if getattr(self, 'installed_proc', None):
                try:
                    if self.installed_proc.state() != QProcess.NotRunning:
                        self.installed_proc.kill(); self.installed_proc.waitForFinished(500)
                except Exception:
                    pass
                self.installed_proc = None
        except Exception:
            pass
        try:
            for proc in list(getattr(self, '_active_upd_procs', []) or []):
                try:
                    if proc.state() != QProcess.NotRunning:
                        proc.kill(); proc.waitForFinished(500)
                except Exception:
                    pass
            self._active_upd_procs = []
        except Exception:
            pass
        try:
            for k, proc in list(getattr(self, '_info_procs', {}).items()):
                try:
                    if proc.state() != QProcess.NotRunning:
                        proc.kill(); proc.waitForFinished(300)
                except Exception:
                    pass
            self._info_procs = {}
        except Exception:
            pass
        try:
            if getattr(self, '_installed_names_proc', None):
                if self._installed_names_proc.state() != QProcess.NotRunning:
                    self._installed_names_proc.kill(); self._installed_names_proc.waitForFinished(300)
            self._installed_names_proc = None
        except Exception:
            pass
        # Proceed with normal close
        super().closeEvent(event)

    # ---- Safe error handlers (avoid lambdas referencing deleted widgets) ----
    def _on_repo_search_error(self, e):
        try:
            self.status_bar.showMessage(f'Repo search error: {e}')
        except Exception:
            pass

    def _on_aur_search_error(self, e):
        try:
            self.status_bar.showMessage(f'AUR search error: {e}')
        except Exception:
            pass

    def _on_installed_error(self, e):
        try:
            self.installed_status.showMessage(f'Error: {e}')
        except Exception:
            pass

    def _on_repo_updates_error(self, e):
        try:
            self.update_status.showMessage(f'Repo update error: {e}')
        except Exception:
            pass

    def _on_aur_updates_error(self, e):
        try:
            self.update_status.showMessage(f'AUR update error: {e}')
        except Exception:
            pass

    def _on_info_error(self, e):
        try:
            self.status_bar.showMessage(f'Info fetch error: {e}')
        except Exception:
            pass

    def _open_settings_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('Settings')
        lay = QVBoxLayout(dlg)
        lay.addWidget(self._build_settings_tab())
        dlg.resize(700, 420)
        dlg.exec_()

    # ---- Helpers: tool availability ----
    def _is_yay_usable(self) -> bool:
        path = shutil.which('yay')
        if not path:
            return False
        try:
            cp = subprocess.run(['bash', '-lc', 'yay --version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        except Exception:
            return False
        out = (cp.stdout or b'') + (cp.stderr or b'')
        text = out.decode('utf-8', errors='ignore').lower()
        if 'error while loading shared libraries' in text:
            return False
        # non-zero could be fine, but if version printed it's good enough
        return True

    # ---- UI builders ----
    def _build_search_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        left = QVBoxLayout()
        self.status_bar = QStatusBar()
        self.status_bar.showMessage('Ready')
        left.addWidget(self.status_bar)

        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Search (name only)')
        self.search_input.setMinimumWidth(500)
        self.search_input.returnPressed.connect(self.do_search)
        btn = QPushButton('Search')
        btn.setFixedWidth(90)
        btn.clicked.connect(self.do_search)
        top.addWidget(self.search_input, 1)
        top.addWidget(btn)
        left.addLayout(top)

        self.search_results = QTreeWidget()
        self.search_results.setHeaderLabels(['Select', 'Package', 'Version', 'Source'])
        self.search_results.setColumnCount(4)
        self.search_results.setSortingEnabled(False)
        self.search_results.setUniformRowHeights(True)
        header = self.search_results.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        left.addWidget(self.search_results)

        self.install_button = QPushButton('Install Selected (yay -S)')
        self.install_button.clicked.connect(self.do_install)
        left.addWidget(self.install_button)

        layout.addLayout(left, 2)

        self.sidebar_text = QTextEdit(readOnly=True)
        self.sidebar_text.setHtml('<h3>Details</h3><p>Click a package to view details.</p>')
        layout.addWidget(self.sidebar_text, 1)

        self.search_results.itemClicked.connect(self._show_pkg_info)
        return tab

    # ---- Installed names cache (for hiding from search) ----
    def _refresh_installed_names(self):
        # If running, kill it
        try:
            if self._installed_names_proc and self._installed_names_proc.state() != QProcess.NotRunning:
                self._installed_names_proc.kill(); self._installed_names_proc.waitForFinished(500)
        except Exception:
            pass
        self._installed_names_buf = ''
        self._installed_names_ready = False
        proc = QProcess(self)
        proc.setProgram('pacman')
        proc.setArguments(['--color', 'never', '-Qq'])
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(self._collect_installed_names_output)
        proc.finished.connect(self._installed_names_finished)
        # not critical to show errors
        self._installed_names_proc = proc
        proc.start()

    def _collect_installed_names_output(self):
        if not self._installed_names_proc:
            return
        try:
            chunk = bytes(self._installed_names_proc.readAllStandardOutput()).decode('utf-8', errors='ignore')
        except Exception:
            chunk = ''
        if chunk:
            self._installed_names_buf += chunk

    def _installed_names_finished(self):
        text = self._installed_names_buf
        names = set()
        for raw in (text or '').split('\n'):
            line = clean_control_codes(raw).strip()
            if not line:
                continue
            # take first token as name
            name = line.split()[0]
            names.add(name)
        self._installed_names = names
        self._installed_names_ready = True
        self._installed_names_proc = None
        # If a search was pending, run it now
        if self._pending_search_term is not None:
            term = self._pending_search_term
            self._pending_search_term = None
            self._start_search(term)

    def _build_installed_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)
        top = QHBoxLayout()
        self.installed_status = QStatusBar()
        self.installed_status.showMessage("Installed packages (pacman -Qen/-Qem)")
        refresh = QPushButton('Refresh (yay -Qe)')
        refresh.clicked.connect(self.do_list_installed)
        # Move Uninstall button to top bar next to Refresh
        remove = QPushButton('Uninstall Selected (yay -Rns)')
        remove.clicked.connect(self.do_uninstall)
        self.uninstall_button = remove

        top.addWidget(self.installed_status, 1)
        top.addWidget(refresh)
        top.addWidget(remove)
        v.addLayout(top)

        # Filter bar with text + source dropdown
        from PyQt5.QtWidgets import QLineEdit
        filter_bar = QHBoxLayout()
        self.installed_filter = QLineEdit()
        self.installed_filter.setPlaceholderText('Filter installed (name/version)')
        self.installed_filter.textChanged.connect(self._filter_installed_list)
        filter_bar.addWidget(self.installed_filter)
        filter_bar.addWidget(QLabel('Source:'))
        self.installed_source_filter = QComboBox()
        self.installed_source_filter.addItems(['All', 'Pacman', 'Yay'])
        self.installed_source_filter.currentTextChanged.connect(self._filter_installed_list)
        self.installed_source_filter.setMinimumWidth(110)
        filter_bar.addWidget(self.installed_source_filter)
        v.addLayout(filter_bar)

        self.installed_view = QTreeWidget()
        self.installed_view.setHeaderLabels(['Select', 'Package', 'Version', 'Source'])
        self.installed_view.setColumnCount(4)
        self.installed_view.setUniformRowHeights(True)
        header = self.installed_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        v.addWidget(self.installed_view)
        return tab

    def _on_tab_changed(self, idx: int):
        # Auto-populate Installed tab on first open or when empty
        try:
            if idx == getattr(self, 'installed_tab_index', -1):
                if self.installed_view.topLevelItemCount() == 0:
                    self.do_list_installed()
            # Always refresh updates when opening Updates tab
            if idx == getattr(self, 'update_tab_index', -1):
                self.do_list_updates()
        except Exception:
            # Be safe; do not crash UI due to tab logic
            pass

    def _build_update_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)

        # Controls row (filter + select all + action buttons + refresh + source dropdown)
        controls = QHBoxLayout()
        from PyQt5.QtWidgets import QLineEdit
        self.update_filter = QLineEdit()
        self.update_filter.setPlaceholderText('Filter updates...')
        self.update_filter.textChanged.connect(self._filter_updates_list)
        controls.addWidget(self.update_filter, 2)

        self.select_all_cb = QCheckBox('Select All')
        self.select_all_cb.toggled.connect(self._toggle_select_all)
        controls.addWidget(self.select_all_cb)

        update_btn = QPushButton('Update Selected (yay -S)')
        update_btn.clicked.connect(self.do_update_selected)
        controls.addWidget(update_btn)

        update_all_btn = QPushButton('Update All (yay -Syu)')
        update_all_btn.clicked.connect(self.do_update_all)
        controls.addWidget(update_all_btn)

        refresh = QPushButton('Refresh Updates')
        refresh.clicked.connect(self.do_list_updates)
        controls.addWidget(refresh)

        controls.addWidget(QLabel('Source:'))
        self.updates_source_filter = QComboBox()
        self.updates_source_filter.addItems(['All', 'Pacman', 'Yay'])
        self.updates_source_filter.currentTextChanged.connect(self._filter_updates_list)
        self.updates_source_filter.setMinimumWidth(110)
        controls.addWidget(self.updates_source_filter)

        v.addLayout(controls)

        # Status bar
        self.update_status = QStatusBar()
        self.update_status.showMessage('Updates (yay -Qu + -Qua)')
        v.addWidget(self.update_status)

        # Updates list
        self.updates_view = QTreeWidget()
        self.updates_view.setHeaderLabels(['Select', 'Package', 'Current', 'New', 'Source'])
        self.updates_view.setColumnCount(5)
        self.updates_view.setUniformRowHeights(True)
        header = self.updates_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        v.addWidget(self.updates_view)

        return tab

    def _build_settings_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)
        v.setContentsMargins(8, 8, 8, 8)

        # Top-right restore default theme
        topbar = QHBoxLayout()
        topbar.addStretch(1)
        default_btn = QPushButton('Restore Default')
        default_btn.setToolTip('Restore the default (System) theme and clear any custom stylesheet')
        default_btn.clicked.connect(self._restore_default_theme)
        topbar.addWidget(default_btn)
        v.addLayout(topbar)

        # Execution settings
        exec_label = QLabel('<b>Execution</b>')
        v.addWidget(exec_label)

        self.keep_open_cb = QCheckBox('Keep Konsole open after finish (when using external terminal)')
        self.keep_open_cb.setChecked(True)
        self.keep_open_cb.toggled.connect(self._on_keep_open_changed)
        v.addWidget(self.keep_open_cb)

        v.addSpacing(8)

        # Theme settings
        theme_label = QLabel('<b>Theme</b>')
        v.addWidget(theme_label)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel('Theme:'))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['System', 'Light', 'Dark', 'Nord', 'Dracula', 'Solarized Light', 'Solarized Dark', 'Custom'])
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self.theme_combo, 1)
        import_btn = QPushButton('Import .qss…')
        import_btn.clicked.connect(self._import_qss)
        theme_row.addWidget(import_btn)
        export_btn = QPushButton('Export .qss…')
        export_btn.clicked.connect(self._export_qss)
        theme_row.addWidget(export_btn)
        v.addLayout(theme_row)

        v.addStretch(1)
        return tab

    # ---- Settings helpers ----
    def _load_settings(self):
        st = QSettings('YayGUI', 'YayGUI')
        keep_open = st.value('keep_open', True, type=bool)
        theme = st.value('theme', 'System', type=str)
        self._custom_css = st.value('custom_css', '', type=str) or ''
        self.keep_konsole_open = bool(keep_open)
        # Sync UI if available
        # no integrated log toggle in UI anymore
        if hasattr(self, 'keep_open_cb'):
            self.keep_open_cb.setChecked(self.keep_konsole_open)
        if hasattr(self, 'theme_combo'):
            idx = self.theme_combo.findText(theme)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
        # Apply theme
        if (theme or '').lower() == 'custom' and not self._custom_css:
            theme = 'System'
        self._apply_theme(theme)

    def _save_settings(self):
        st = QSettings('YayGUI', 'YayGUI')
        st.setValue('keep_open', self.keep_konsole_open)
        sel = self.theme_combo.currentText() if hasattr(self, 'theme_combo') else 'System'
        st.setValue('theme', sel)
        if (sel or '').lower() == 'custom':
            st.setValue('custom_css', getattr(self, '_custom_css', ''))
        else:
            st.setValue('custom_css', '')

    def _restore_default_theme(self):
        # Clear custom style and switch to System theme
        self._custom_css = ''
        if hasattr(self, 'theme_combo'):
            self.theme_combo.setCurrentText('System')
        self._apply_theme('System')
        self._save_settings()

    def _on_keep_open_changed(self, checked: bool):
        self.keep_konsole_open = bool(checked)
        self._save_settings()

    def _on_theme_changed(self, name: str):
        self._apply_theme(name)
        self._save_settings()

    def _apply_theme(self, name: str):
        app = QApplication.instance()
        if not app:
            return
        css = ''
        n = (name or '').lower()
        if n == 'dark':
            css = self._dark_theme_stylesheet()
        elif n == 'light':
            css = self._light_theme_stylesheet()
        elif n == 'nord':
            css = self._nord_theme_stylesheet()
        elif n == 'dracula':
            css = self._dracula_theme_stylesheet()
        elif n == 'solarized dark':
            css = self._solarized_dark_theme_stylesheet()
        elif n == 'solarized light':
            css = self._solarized_light_theme_stylesheet()
        elif n == 'custom':
            css = getattr(self, '_custom_css', '')
        # System -> empty stylesheet
        app.setStyleSheet(css)

    def _light_theme_stylesheet(self) -> str:
        # Subtle light theme close to system defaults
        return """
        QWidget { background: #fafafa; color: #202020; }
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox { background: #ffffff; color: #202020; border: 1px solid #cfcfcf; }
        QPushButton { background: #f3f3f3; border: 1px solid #cfcfcf; padding: 4px 8px; }
        QPushButton:hover { background: #e9e9e9; }
        QTreeWidget, QHeaderView::section { background: #ffffff; color: #202020; }
        QStatusBar { background: #f0f0f0; }
        QTabWidget::pane { border: 1px solid #cfcfcf; }
        QSplitter::handle { background: #e0e0e0; }
        """

    def _dark_theme_stylesheet(self) -> str:
        # Conservative dark theme for readability
        return """
        QWidget { background: #121212; color: #e0e0e0; }
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox { background: #1e1e1e; color: #e0e0e0; border: 1px solid #2a2a2a; }
        QPushButton { background: #1f2933; border: 1px solid #2a2f36; padding: 4px 8px; color: #e0e0e0; }
        QPushButton:hover { background: #26323d; }
        QTreeWidget, QHeaderView::section { background: #1a1a1a; color: #e0e0e0; }
        QStatusBar { background: #181818; }
        QTabWidget::pane { border: 1px solid #2a2a2a; }
        QSplitter::handle { background: #2a2a2a; }
        """

    def _nord_theme_stylesheet(self) -> str:
        return """
        QWidget { background: #2e3440; color: #d8dee9; }
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox { background: #3b4252; color: #eceff4; border: 1px solid #434c5e; }
        QPushButton { background: #434c5e; border: 1px solid #4c566a; padding: 4px 8px; color: #eceff4; }
        QPushButton:hover { background: #4c566a; }
        QTreeWidget, QHeaderView::section { background: #3b4252; color: #eceff4; }
        QStatusBar { background: #2e3440; }
        QTabWidget::pane { border: 1px solid #434c5e; }
        QSplitter::handle { background: #434c5e; }
        """

    def _dracula_theme_stylesheet(self) -> str:
        return """
        QWidget { background: #282a36; color: #f8f8f2; }
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox { background: #1e1f29; color: #f8f8f2; border: 1px solid #44475a; }
        QPushButton { background: #44475a; border: 1px solid #5a5f73; padding: 4px 8px; color: #f8f8f2; }
        QPushButton:hover { background: #5a5f73; }
        QTreeWidget, QHeaderView::section { background: #1e1f29; color: #f8f8f2; }
        QStatusBar { background: #1e1f29; }
        QTabWidget::pane { border: 1px solid #44475a; }
        QSplitter::handle { background: #44475a; }
        """

    def _solarized_light_theme_stylesheet(self) -> str:
        return """
        QWidget { background: #fdf6e3; color: #657b83; }
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox { background: #eee8d5; color: #586e75; border: 1px solid #d6ceb6; }
        QPushButton { background: #e9e2c6; border: 1px solid #d6ceb6; padding: 4px 8px; color: #586e75; }
        QPushButton:hover { background: #e2dabd; }
        QTreeWidget, QHeaderView::section { background: #fefcf2; color: #586e75; }
        QStatusBar { background: #f3eddb; }
        QTabWidget::pane { border: 1px solid #d6ceb6; }
        QSplitter::handle { background: #e2dabd; }
        """

    def _solarized_dark_theme_stylesheet(self) -> str:
        return """
        QWidget { background: #002b36; color: #93a1a1; }
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox { background: #073642; color: #93a1a1; border: 1px solid #0f3945; }
        QPushButton { background: #0f3945; border: 1px solid #12404d; padding: 4px 8px; color: #93a1a1; }
        QPushButton:hover { background: #12404d; }
        QTreeWidget, QHeaderView::section { background: #073642; color: #93a1a1; }
        QStatusBar { background: #002b36; }
        QTabWidget::pane { border: 1px solid #0f3945; }
        QSplitter::handle { background: #0f3945; }
        """

    def _import_qss(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import QSS', '', 'Qt Stylesheets (*.qss);;All Files (*)')
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                css = f.read()
        except Exception as e:
            QMessageBox.critical(self, 'Import failed', f'Could not read file:\n{e}')
            return
        self._custom_css = css
        self.theme_combo.setCurrentText('Custom')
        self._apply_theme('Custom')
        self._save_settings()

    def _export_qss(self):
        # Determine current css
        current = self.theme_combo.currentText() if hasattr(self, 'theme_combo') else 'System'
        n = (current or '').lower()
        if n == 'system':
            css = ''
        elif n == 'light':
            css = self._light_theme_stylesheet()
        elif n == 'dark':
            css = self._dark_theme_stylesheet()
        elif n == 'nord':
            css = self._nord_theme_stylesheet()
        elif n == 'dracula':
            css = self._dracula_theme_stylesheet()
        elif n == 'solarized dark':
            css = self._solarized_dark_theme_stylesheet()
        elif n == 'solarized light':
            css = self._solarized_light_theme_stylesheet()
        elif n == 'custom':
            css = getattr(self, '_custom_css', '')
        else:
            css = ''
        path, _ = QFileDialog.getSaveFileName(self, 'Export QSS', 'theme.qss', 'Qt Stylesheets (*.qss);;All Files (*)')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(css or '')
        except Exception as e:
            QMessageBox.critical(self, 'Export failed', f'Could not write file:\n{e}')

    # ---- Search ----
    def do_search(self):
        term = self.search_input.text().strip()
        if not term:
            QMessageBox.warning(self, 'Missing', 'Please enter a search term.')
            return
        self._current_search_term = term.lower()
        if not getattr(self, '_installed_names_ready', False):
            # Fetch installed names first so we can hide installed from results
            self._pending_search_term = term
            self.status_bar.showMessage('Loading installed package list...')
            self._refresh_installed_names()
            return
        self._start_search(term)

    def _start_search(self, term):
        # Cancel any previous search processes
        for p in self._active_search_procs:
            try:
                if p.state() != QProcess.NotRunning:
                    p.kill(); p.waitForFinished(500)
            except Exception:
                pass
        self._active_search_procs = []
        self.search_results.clear()
        self.sidebar_text.setHtml('<h3>Details</h3><p>Searching...</p>')
        self.status_bar.showMessage('Searching repos + AUR...')
        self.search_buffer = ''
        self._search_pending = {'repo': '', 'aur': ''}
        self._search_ctx = {
            'repo': {'current': None, 'item': None},
            'aur': {'current': None, 'item': None}
        }
        self._search_done = {'repo': False, 'aur': False}
        self.search_results.setSortingEnabled(False)

        # Repo search via pacman (fast)
        repo = QProcess(self)
        repo.setProgram('pacman')
        repo.setArguments(['--color', 'never', '-Ss', term])
        repo.setProcessChannelMode(QProcess.MergedChannels)
        repo.readyReadStandardOutput.connect(lambda: self._collect_search_output_streaming('repo', repo))
        repo.finished.connect(lambda _c=0, _s=0: self._search_one_finished('repo'))
        repo.errorOccurred.connect(self._on_repo_search_error)
        self._active_search_procs.append(repo)
        repo.start()

        # AUR search via yay (AUR only)
        aur = QProcess(self)
        aur.setProgram('yay')
        aur.setArguments(['--color=never', '-Ss', term, '--aur'])
        aur.setProcessChannelMode(QProcess.MergedChannels)
        aur.readyReadStandardOutput.connect(lambda: self._collect_search_output_streaming('aur', aur))
        aur.finished.connect(lambda _c=0, _s=0: self._search_one_finished('aur'))
        aur.errorOccurred.connect(self._on_aur_search_error)
        self._active_search_procs.append(aur)
        aur.start()

    def _collect_search_output(self):
        # Kept for completeness; not used now
        self.search_buffer += bytes(self.search_proc.readAllStandardOutput()).decode('utf-8', errors='ignore')

    def _collect_search_output_streaming(self, source, proc):
        chunk = bytes(proc.readAllStandardOutput()).decode('utf-8', errors='ignore')
        if not chunk:
            return
        self._search_pending[source] += chunk
        lines = self._search_pending[source].split('\n')
        self._search_pending[source] = lines.pop()  # keep last partial line
        for raw in lines:
            line = clean_control_codes(raw.rstrip('\r'))
            if not line or line.startswith('::'):
                continue
            # Stop adding if we hit cap to keep UI responsive
            if self.search_results.topLevelItemCount() >= self._search_max_items:
                continue
            m = self._search_header_re.match(line)
            if m:
                # finalize previous (nothing special needed)
                # create new item
                p = {
                    'repo': m.group('repo'),
                    'name': m.group('name'),
                    'version': m.group('ver').strip(),
                    'description': ''
                }
                # Enforce name-only match
                if self._current_search_term and self._current_search_term not in p['name'].lower():
                    continue
                # Skip if installed
                try:
                    if p['name'] in getattr(self, '_installed_names', set()):
                        continue
                except Exception:
                    pass
                it = QTreeWidgetItem(self.search_results)
                it.setText(0, '')
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(0, Qt.Unchecked)
                it.setText(1, p['name'])
                it.setText(2, p['version'])
                it.setData(1, Qt.UserRole, p)
                src = 'Yay' if (p['repo'] or '').lower() == 'aur' else 'Pacman'
                it.setText(3, src)
                # Apply source filter immediately
                sel = self.search_source_filter.currentText() if hasattr(self, 'search_source_filter') else 'All'
                if sel in ('Pacman', 'Yay') and src != sel:
                    it.setHidden(True)
                self._search_ctx[source]['current'] = p
                self._search_ctx[source]['item'] = it
                continue
            if line.startswith(' ') and self._search_ctx[source]['current'] and self._search_ctx[source]['item']:
                cur = self._search_ctx[source]['current']
                it = self._search_ctx[source]['item']
                cur['description'] += line.strip() + ' '
                # description now shown in sidebar only

    def _search_finished(self):
        # Kept for compatibility when using single-process path
        self._search_one_finished('repo')
        self._search_one_finished('aur')

    def _search_one_finished(self, source):
        # Flush pending desc for that source
        ctx = self._search_ctx.get(source)
        # Ensure last item's description captured for sidebar (no list column)
        self._search_done[source] = True
        if all(self._search_done.values()):
            count = self.search_results.topLevelItemCount()
            if count == 0:
                self.status_bar.showMessage('No packages found.')
            else:
                self.status_bar.showMessage(f'Found {count} package(s).')
            self.search_results.setSortingEnabled(True)
            self._active_search_procs = []

    # Apply source filter to search results
    def _apply_search_filter(self, *_):
        try:
            sel = self.search_source_filter.currentText()
        except Exception:
            sel = 'All'
        for i in range(self.search_results.topLevelItemCount()):
            it = self.search_results.topLevelItem(i)
            src = it.text(3)
            hide = False
            if sel in ('Pacman', 'Yay') and src != sel:
                hide = True
            it.setHidden(hide)

    # ---- Installed ----
    def do_list_installed(self):
        # Cancel any previous installed listing procs
        for p in getattr(self, '_active_inst_procs', []):
            try:
                if p.state() != QProcess.NotRunning:
                    p.kill(); p.waitForFinished(500)
            except Exception:
                pass
        self._active_inst_procs = []
        self.installed_view.clear()
        self.installed_view.setSortingEnabled(False)
        self.installed_status.showMessage('Loading installed packages...')
        self._installed_count = 0
        self._installed_done_native = False
        self._installed_done_foreign = False

        # Explicit native (repo) packages
        p_native = QProcess(self)
        p_native.setProgram('pacman')
        p_native.setArguments(['--color', 'never', '-Qen'])
        p_native.setProcessChannelMode(QProcess.MergedChannels)
        self._inst_source_by_proc[p_native] = 'Pacman'
        p_native.readyReadStandardOutput.connect(lambda: self._collect_installed_output_stream2(p_native))
        p_native.finished.connect(lambda _c=0, _s=0, p=p_native: self._installed_proc_finished(p, 'native'))
        p_native.errorOccurred.connect(self._on_installed_error)
        self._active_inst_procs.append(p_native)
        p_native.start()

        # Explicit foreign (AUR) packages
        p_foreign = QProcess(self)
        p_foreign.setProgram('pacman')
        p_foreign.setArguments(['--color', 'never', '-Qem'])
        p_foreign.setProcessChannelMode(QProcess.MergedChannels)
        self._inst_source_by_proc[p_foreign] = 'Yay'
        p_foreign.readyReadStandardOutput.connect(lambda: self._collect_installed_output_stream2(p_foreign))
        p_foreign.finished.connect(lambda _c=0, _s=0, p=p_foreign: self._installed_proc_finished(p, 'foreign'))
        p_foreign.errorOccurred.connect(self._on_installed_error)
        self._active_inst_procs.append(p_foreign)
        p_foreign.start()

    def _collect_installed_output(self):
        self.installed_buffer += bytes(self.installed_proc.readAllStandardOutput()).decode('utf-8', errors='ignore')

    def _installed_finished(self):
        pkgs = parse_yay_installed(self.installed_buffer)
        if not pkgs:
            self.installed_status.showMessage('No explicitly installed packages found.')
            return
        for p in pkgs:
            it = QTreeWidgetItem(self.installed_view)
            it.setText(0, '')
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Unchecked)
            it.setText(1, p['name'])
            it.setText(2, p['version'])
        self.installed_status.showMessage(f'Found {len(pkgs)} package(s).')

    def _collect_installed_output_stream2(self, proc):
        chunk = bytes(proc.readAllStandardOutput()).decode('utf-8', errors='ignore')
        if not chunk:
            return
        buf = (self._inst_pending.get(proc, '') or '') + chunk
        lines = buf.split('\n')
        self._inst_pending[proc] = lines.pop()  # keep tail
        source_label = self._inst_source_by_proc.get(proc, '')
        for raw in lines:
            line = clean_control_codes(raw).strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            if self.installed_view.topLevelItemCount() >= self._installed_max_items:
                continue
            it = QTreeWidgetItem(self.installed_view)
            it.setText(0, '')
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Unchecked)
            it.setText(1, parts[0])
            it.setText(2, parts[1])
            it.setText(3, source_label)
            self._installed_count += 1
        self.installed_status.showMessage(f'Loaded {self._installed_count} installed package(s)...')
        # Re-apply filter if user picked a source/text filter
        try:
            self._filter_installed_list(self.installed_filter.text())
        except Exception:
            pass

    def _installed_proc_finished(self, proc, which):
        # Flush tail for this proc
        tail = clean_control_codes(self._inst_pending.get(proc, '') or '').strip()
        self._inst_pending[proc] = ''
        if tail:
            parts = tail.split()
            if len(parts) >= 2 and self.installed_view.topLevelItemCount() < self._installed_max_items:
                it = QTreeWidgetItem(self.installed_view)
                it.setText(0, '')
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(0, Qt.Unchecked)
                it.setText(1, parts[0])
                it.setText(2, parts[1])
                it.setText(3, self._inst_source_by_proc.get(proc, ''))
                self._installed_count += 1
        if which == 'native':
            self._installed_done_native = True
        else:
            self._installed_done_foreign = True
        if getattr(self, '_installed_done_native', False) and getattr(self, '_installed_done_foreign', False):
            if self._installed_count == 0:
                self.installed_status.showMessage('No explicitly installed packages found.')
            else:
                self.installed_status.showMessage(f'Found {self._installed_count} package(s).')
            self.installed_view.setSortingEnabled(True)

    def _filter_installed_list(self, text):
        q = (text or '').strip().lower()
        sel = 'All'
        try:
            sel = self.installed_source_filter.currentText()
        except Exception:
            pass
        for i in range(self.installed_view.topLevelItemCount()):
            it = self.installed_view.topLevelItem(i)
            hay = f"{it.text(1)} {it.text(2)}".lower()
            visible = True
            if q and q not in hay:
                visible = False
            if sel in ('Pacman', 'Yay') and (it.text(3) != sel):
                visible = False
            it.setHidden(not visible)

    # ---- Updates ----
    def do_list_updates(self):
        # Cancel running processes if any
        for proc in getattr(self, '_active_upd_procs', []):
            try:
                if proc.state() != QProcess.NotRunning:
                    proc.kill(); proc.waitForFinished(1000)
            except Exception:
                pass
        self._active_upd_procs = []

        # Reset state and UI
        self.updates_view.clear()
        self.updates_view.setSortingEnabled(False)
        self._repo_pending = ''
        self._aur_pending = ''
        self._repo_done = False
        self._aur_done = False
        self._repo_count = 0
        self._aur_count = 0
        self.update_status.showMessage('Checking for updates...')
        if hasattr(self, 'select_all_cb'):
            try:
                self.select_all_cb.setChecked(False)
            except Exception:
                pass

        # Reset seen set for deduplication
        self._updates_seen = set()

        # Start repo updates via pacman only (avoid AUR duplication)
        repo = QProcess(self)
        repo.setProgram('pacman')
        repo.setArguments(['--color', 'never', '-Qu'])
        repo.setProcessChannelMode(QProcess.MergedChannels)
        repo.readyReadStandardOutput.connect(lambda: self._collect_updates_output_stream('repo', repo))
        repo.finished.connect(lambda _c=0, _s=0: self._updates_one_finished('repo'))
        repo.errorOccurred.connect(self._on_repo_updates_error)
        self._active_upd_procs.append(repo)
        repo.start()

        # Start AUR updates (AUR only)
        aur = QProcess(self)
        aur.setProgram('yay')
        aur.setArguments(['--color=never', '-Qua'])
        aur.setProcessChannelMode(QProcess.MergedChannels)
        aur.readyReadStandardOutput.connect(lambda: self._collect_updates_output_stream('aur', aur))
        aur.finished.connect(lambda _c=0, _s=0: self._updates_one_finished('aur'))
        aur.errorOccurred.connect(self._on_aur_updates_error)
        self._active_upd_procs.append(aur)
        aur.start()

    def _collect_updates_output_stream(self, source, proc):
        chunk = bytes(proc.readAllStandardOutput()).decode('utf-8', errors='ignore')
        if not chunk:
            return
        if source == 'repo':
            self._repo_pending += chunk
            buf = self._repo_pending
            lines = buf.split('\n')
            self._repo_pending = lines.pop()
        else:
            self._aur_pending += chunk
            buf = self._aur_pending
            lines = buf.split('\n')
            self._aur_pending = lines.pop()
        for raw in lines:
            line = clean_control_codes(raw.rstrip('\r')).strip()
            if not line or line.startswith('::'):
                continue
            m = self._upd_line_re.match(line)
            if not m:
                continue
            name = m.group('name')
            key = (source, name)
            if key in self._updates_seen:
                continue
            self._updates_seen.add(key)
            it = QTreeWidgetItem(self.updates_view)
            it.setText(0, '')
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Unchecked)
            it.setText(1, name)
            it.setText(2, m.group('old'))
            it.setText(3, m.group('new'))
            src_label = 'Pacman' if source == 'repo' else 'Yay'
            it.setText(4, src_label)
            # Apply source filter immediately
            try:
                sel = self.updates_source_filter.currentText()
            except Exception:
                sel = 'All'
            if sel in ('Pacman', 'Yay') and src_label != sel:
                it.setHidden(True)
            if source == 'repo':
                self._repo_count += 1
            else:
                self._aur_count += 1
            self.update_status.showMessage(f"Updates: Repo {self._repo_count}, AUR {self._aur_count} (loading...)")

    def _updates_one_finished(self, source):
        if source == 'repo':
            self._repo_done = True
        else:
            self._aur_done = True
        if self._repo_done and self._aur_done:
            total = self._repo_count + self._aur_count
            if total == 0:
                self.update_status.showMessage('No updates available.')
            else:
                self.update_status.showMessage(f'Found {total} update(s): {self._repo_count} repo, {self._aur_count} AUR.')
            # Re-enable sorting now that we are done
            self.updates_view.setSortingEnabled(True)

    def _filter_updates_list(self, text):
        q = (text or '').strip().lower()
        try:
            sel = self.updates_source_filter.currentText()
        except Exception:
            sel = 'All'
        for i in range(self.updates_view.topLevelItemCount()):
            it = self.updates_view.topLevelItem(i)
            # Match in name, current, new (not source), then apply source filter separately
            hay = ' '.join([
                it.text(1), it.text(2), it.text(3)
            ]).lower()
            visible = True
            if q and q not in hay:
                visible = False
            if sel in ('Pacman', 'Yay') and (it.text(4) != sel):
                visible = False
            it.setHidden(not visible)

    def _toggle_select_all(self, checked: bool):
        # Toggle selection for all visible rows
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.updates_view.topLevelItemCount()):
            it = self.updates_view.topLevelItem(i)
            if not it.isHidden():
                it.setCheckState(0, state)

    def do_update_selected(self):
        names = []
        for i in range(self.updates_view.topLevelItemCount()):
            it = self.updates_view.topLevelItem(i)
            if it.checkState(0) == Qt.Checked:
                names.append(it.text(1))
        if not names:
            QMessageBox.information(self, 'Nothing selected', 'Select at least one package to update.')
            return
        cmd = f"yay -S --needed {' '.join(names)}"
        if QMessageBox.question(self, 'Confirm update', f"Run:\n{cmd}") != QMessageBox.Yes:
            return
        repo_names = []
        aur_names = []
        # Determine sources from column 4
        for i in range(self.updates_view.topLevelItemCount()):
            it = self.updates_view.topLevelItem(i)
            if it.checkState(0) == Qt.Checked:
                if it.text(4).lower().startswith('pacman'):
                    repo_names.append(it.text(1))
                else:
                    aur_names.append(it.text(1))
        yay_ok = self._is_yay_usable()
        if not yay_ok:
            if not repo_names:
                QMessageBox.critical(self, 'Yay not available', 'Yay is broken or missing. Cannot update AUR packages. Fix yay or run repo updates only via pacman.')
                return
            if aur_names:
                if QMessageBox.question(self, 'Yay unavailable', 'Yay is not available. Proceed with repo updates only via pacman?') != QMessageBox.Yes:
                    return
            # Run repo-only via pacman in Konsole (or fallback terminal)
            pcmd = f"sudo pacman -S --needed {' '.join(repo_names)}"
            try:
                if shutil.which('konsole'):
                    self.term.run_konsole_direct(['sudo', 'pacman', '-S', '--needed', *repo_names], keep_open=self.keep_konsole_open)
                else:
                    self.term.run(pcmd)
            except Exception as e:
                QMessageBox.critical(self, 'Terminal error', str(e))
            return
        # yay is usable: split by source to prefer pacman for repo
        cmds_text = []
        if repo_names:
            cmds_text.append(f"sudo pacman -S --needed {' '.join(repo_names)}")
        if aur_names:
            cmds_text.append(f"yay -S --needed {' '.join(aur_names)}")
        if not cmds_text:
            QMessageBox.information(self, 'Nothing selected', 'No packages selected to update.')
            return
        # We've already asked confirmation above; run
        try:
            if shutil.which('konsole'):
                if repo_names:
                    self.term.run_konsole_direct(['sudo', 'pacman', '-S', '--needed', *repo_names], keep_open=self.keep_konsole_open)
                if aur_names:
                    self.term.run_konsole_direct(['yay', '-S', '--needed', *aur_names], keep_open=self.keep_konsole_open)
            else:
                for cmdline in cmds_text:
                    self.term.run(cmdline)
        except Exception as e:
            QMessageBox.critical(self, 'Terminal error', str(e))

    def do_update_all(self):
        cmd = 'yay -Syu'
        if QMessageBox.question(self, 'Confirm full update', f"Run:\n{cmd}") != QMessageBox.Yes:
            return
        if not self._is_yay_usable():
            # Fallback to repo-only update via pacman
            pcmd = 'sudo pacman -Syu'
            if QMessageBox.question(self, 'Yay unavailable', 'Yay is not available. Run repo update only via pacman?') != QMessageBox.Yes:
                return
            try:
                if shutil.which('konsole'):
                    self.term.run_konsole_direct(['sudo', 'pacman', '-Syu'], keep_open=self.keep_konsole_open)
                else:
                    self.term.run(pcmd)
            except Exception as e:
                QMessageBox.critical(self, 'Terminal error', str(e))
            return
        try:
            if shutil.which('konsole'):
                self.term.run_konsole_direct(['yay', '-Syu'], keep_open=self.keep_konsole_open)
            else:
                self.term.run(cmd)
        except Exception as e:
            QMessageBox.critical(self, 'Terminal error', str(e))

    # ---- Actions ----
    def _show_pkg_info(self, item, _col):
        data = item.data(1, Qt.UserRole)
        if not data:
            return
        desc = data.get('description', '').strip()
        key = f"{data.get('repo', '')}/{data.get('name', '')}"
        self._current_info_key = key

        if desc:
            url = data.get('url', '')
            link = f" &nbsp; <b>URL:</b> <a href=\"{url}\">{url}</a>" if url else ''
            details = (
                f"<h3>{data['name']}</h3>"
                f"<p>{desc}</p>"
                f"<p><b>Repo:</b> {data['repo']} &nbsp; <b>Version:</b> {data['version']}{link}</p>"
            )
            self.sidebar_text.setHtml(details)
            return

        # No description parsed from search output — fetch details via -Si
        self.sidebar_text.setHtml(
            f"<h3>{data['name']}</h3><p>Fetching description…</p>"
        )
        try:
            self._fetch_pkg_details(data)
        except Exception as e:
            # Fall back to plain message
            self.sidebar_text.setHtml(
                f"<h3>{data['name']}</h3><p>No description available.</p>"
            )
            self.status_bar.showMessage(f'Info fetch error: {e}')

    def _fetch_pkg_details(self, data):
        name = data.get('name')
        repo = (data.get('repo') or '').lower()
        if not name:
            return
        key = f"{repo}/{name}"
        if key in self._info_procs:
            # Already fetching
            return
        proc = QProcess(self)
        if repo == 'aur':
            proc.setProgram('yay')
            proc.setArguments(['--color=never', '-Si', name, '--aur'])
        else:
            proc.setProgram('pacman')
            proc.setArguments(['--color', 'never', '-Si', name])
        proc.setProcessChannelMode(QProcess.MergedChannels)
        self._info_buffers[key] = ''
        proc.readyReadStandardOutput.connect(lambda: self._collect_info_output(key, proc))
        proc.finished.connect(lambda _c=0, _s=0, k=key, d=data: self._info_finished(k, d))
        proc.errorOccurred.connect(self._on_info_error)
        self._info_procs[key] = proc
        proc.start()

    def _collect_info_output(self, key, proc):
        chunk = bytes(proc.readAllStandardOutput()).decode('utf-8', errors='ignore')
        if not chunk:
            return
        self._info_buffers[key] = self._info_buffers.get(key, '') + chunk

    def _info_finished(self, key, data):
        buf = self._info_buffers.pop(key, '')
        proc = self._info_procs.pop(key, None)
        try:
            desc, url = parse_si_desc_url(buf)
        except Exception:
            desc, url = '', ''
        # Update data so subsequent clicks are instant
        if desc:
            data['description'] = desc
        if url:
            data['url'] = url
        # If user is still viewing this package, refresh the sidebar
        if key == self._current_info_key:
            d = data
            desc_disp = d.get('description', '').strip() or 'No description available.'
            url_disp = d.get('url', '')
            link = f" &nbsp; <b>URL:</b> <a href=\"{url_disp}\">{url_disp}</a>" if url_disp else ''
            details = (
                f"<h3>{d['name']}</h3>"
                f"<p>{desc_disp}</p>"
                f"<p><b>Repo:</b> {d['repo']} &nbsp; <b>Version:</b> {d['version']}{link}</p>"
            )
            self.sidebar_text.setHtml(details)

    def do_install(self):
        names = []
        for i in range(self.search_results.topLevelItemCount()):
            it = self.search_results.topLevelItem(i)
            if it.checkState(0) == Qt.Checked:
                names.append(it.text(1))
        if not names:
            QMessageBox.information(self, 'Nothing selected', 'Select at least one package to install.')
            return
        # Split into repo vs AUR
        repo_names = []
        aur_names = []
        for i in range(self.search_results.topLevelItemCount()):
            it = self.search_results.topLevelItem(i)
            if it.checkState(0) == Qt.Checked:
                data = it.data(1, Qt.UserRole) or {}
                if (data.get('repo') or '').lower() == 'aur':
                    aur_names.append(it.text(1))
                else:
                    repo_names.append(it.text(1))
        yay_ok = self._is_yay_usable()
        if not yay_ok:
            # Offer to install repo packages with pacman
            if not repo_names:
                QMessageBox.critical(self, 'Yay not available', 'Yay is not available or broken. AUR packages cannot be installed. Fix yay first.')
                return
            if aur_names:
                if QMessageBox.question(self, 'Yay unavailable', 'Yay is not available. Proceed with repo packages only via pacman?') != QMessageBox.Yes:
                    return
            pcmd = f"sudo pacman -S --needed {' '.join(repo_names)}"
            try:
                if shutil.which('konsole'):
                    self.term.run_konsole_direct(['sudo', 'pacman', '-S', '--needed', *repo_names], keep_open=self.keep_konsole_open)
                else:
                    self.term.run(pcmd)
            except Exception as e:
                QMessageBox.critical(self, 'Terminal error', str(e))
            return
        # yay is usable. Prefer pacman for repo, yay for AUR.
        cmds_text = []
        if repo_names:
            cmds_text.append(f"sudo pacman -S --needed {' '.join(repo_names)}")
        if aur_names:
            cmds_text.append(f"yay -S {' '.join(aur_names)}")
        if not cmds_text:
            QMessageBox.information(self, 'Nothing selected', 'Select at least one package to install.')
            return
        if QMessageBox.question(self, 'Confirm install', "Run:\n" + "\n".join(cmds_text)) != QMessageBox.Yes:
            return
        try:
            if shutil.which('konsole'):
                if repo_names:
                    self.term.run_konsole_direct(['sudo', 'pacman', '-S', '--needed', *repo_names], keep_open=self.keep_konsole_open)
                if aur_names:
                    self.term.run_konsole_direct(['yay', '-S', *aur_names], keep_open=self.keep_konsole_open)
            else:
                for cmdline in cmds_text:
                    self.term.run(cmdline)
        except Exception as e:
            QMessageBox.critical(self, 'Terminal error', str(e))

    def do_uninstall(self):
        names = []
        repo_names = []
        aur_names = []
        for i in range(self.installed_view.topLevelItemCount()):
            it = self.installed_view.topLevelItem(i)
            if it.checkState(0) == Qt.Checked:
                names.append(it.text(1))
                src = (it.text(3) or '').lower()
                if src.startswith('pacman'):
                    repo_names.append(it.text(1))
                else:
                    aur_names.append(it.text(1))
        if not names:
            QMessageBox.information(self, 'Nothing selected', 'Select at least one package to uninstall.')
            return
        # If yay not usable, run everything via pacman
        if not self._is_yay_usable():
            pcmd = f"sudo pacman -Rns {' '.join(names)}"
            if QMessageBox.question(self, 'Yay unavailable', f"Run via pacman instead?\n{pcmd}") != QMessageBox.Yes:
                return
            try:
                if shutil.which('konsole'):
                    self.term.run_konsole_direct(['sudo', 'pacman', '-Rns', *names], keep_open=self.keep_konsole_open)
                else:
                    self.term.run(pcmd)
            except Exception as e:
                QMessageBox.critical(self, 'Terminal error', str(e))
            return
        # yay is usable: split by source
        cmds_text = []
        if repo_names:
            cmds_text.append(f"sudo pacman -Rns {' '.join(repo_names)}")
        if aur_names:
            cmds_text.append(f"yay -Rns {' '.join(aur_names)}")
        if not cmds_text:
            QMessageBox.information(self, 'Nothing selected', 'No packages selected to uninstall.')
            return
        if QMessageBox.question(self, 'Confirm uninstall', "Run:\n" + "\n".join(cmds_text)) != QMessageBox.Yes:
            return
        try:
            if shutil.which('konsole'):
                if repo_names:
                    self.term.run_konsole_direct(['sudo', 'pacman', '-Rns', *repo_names], keep_open=self.keep_konsole_open)
                if aur_names:
                    self.term.run_konsole_direct(['yay', '-Rns', *aur_names], keep_open=self.keep_konsole_open)
            else:
                # Fallback: run combined in default terminal sequentially
                for cmdline in cmds_text:
                    self.term.run(cmdline)
        except Exception as e:
            QMessageBox.critical(self, 'Terminal error', str(e))


def main():
    _install_exception_hook()
    app = QApplication(sys.argv)
    gui = YayGUI()
    gui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
