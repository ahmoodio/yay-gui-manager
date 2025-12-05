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
    QTabWidget, QFrame
)
from PyQt5.QtCore import Qt, QProcess


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

        root = QVBoxLayout(self)
        # Global option: keep Konsole open
        from PyQt5.QtWidgets import QCheckBox
        self.keep_open_cb = QCheckBox('Keep Konsole open after finish')
        self.keep_open_cb.setChecked(True)
        root.addWidget(self.keep_open_cb)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.tabs.addTab(self._build_search_tab(), 'Search & Install')
        self.tabs.addTab(self._build_installed_tab(), 'Installed Packages')
        self.tabs.addTab(self._build_update_tab(), 'Update')

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
        self.search_input.setPlaceholderText('Search (yay -Ss)')
        self.search_input.returnPressed.connect(self.do_search)
        btn = QPushButton('Search')
        btn.clicked.connect(self.do_search)
        top.addWidget(self.search_input)
        top.addWidget(btn)
        left.addLayout(top)

        self.search_results = QTreeWidget()
        self.search_results.setHeaderLabels(['Select', 'Package', 'Version'])
        self.search_results.setColumnCount(3)
        self.search_results.setSortingEnabled(False)
        self.search_results.setUniformRowHeights(True)
        header = self.search_results.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
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

    def _build_installed_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)
        top = QHBoxLayout()
        self.installed_status = QStatusBar()
        self.installed_status.showMessage("Click Refresh to load explicitly installed packages (yay -Qe)")
        refresh = QPushButton('Refresh (yay -Qe)')
        refresh.clicked.connect(self.do_list_installed)
        top.addWidget(self.installed_status, 1)
        top.addWidget(refresh)
        v.addLayout(top)

        # Filter bar
        from PyQt5.QtWidgets import QLineEdit
        filter_bar = QHBoxLayout()
        self.installed_filter = QLineEdit()
        self.installed_filter.setPlaceholderText('Filter installed...')
        self.installed_filter.textChanged.connect(self._filter_installed_list)
        filter_bar.addWidget(self.installed_filter)
        v.addLayout(filter_bar)

        self.installed_view = QTreeWidget()
        self.installed_view.setHeaderLabels(['Select', 'Package', 'Version'])
        self.installed_view.setColumnCount(3)
        self.installed_view.setUniformRowHeights(True)
        header = self.installed_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        v.addWidget(self.installed_view)

        remove = QPushButton('Uninstall Selected (yay -Rns)')
        remove.clicked.connect(self.do_uninstall)
        v.addWidget(remove)
        return tab

    def _build_update_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)

        # Top bar with status and refresh
        top = QHBoxLayout()
        self.update_status = QStatusBar()
        self.update_status.showMessage('Click Refresh to check for updates (yay -Qu + -Qua)')
        refresh = QPushButton('Refresh Updates')
        refresh.clicked.connect(self.do_list_updates)
        top.addWidget(self.update_status, 1)
        top.addWidget(refresh)
        v.addLayout(top)

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

        # Filter + Action buttons
        btns = QHBoxLayout()
        from PyQt5.QtWidgets import QLineEdit
        self.update_filter = QLineEdit()
        self.update_filter.setPlaceholderText('Filter updates...')
        self.update_filter.textChanged.connect(self._filter_updates_list)
        btns.addWidget(self.update_filter, 2)
        update_btn = QPushButton('Update Selected (yay -S)')
        update_btn.clicked.connect(self.do_update_selected)
        btns.addWidget(update_btn)
        update_all_btn = QPushButton('Update All (yay -Syu)')
        update_all_btn.clicked.connect(self.do_update_all)
        btns.addWidget(update_all_btn)
        btns.addStretch(1)
        v.addLayout(btns)

        return tab

    # ---- Search ----
    def do_search(self):
        term = self.search_input.text().strip()
        if not term:
            QMessageBox.warning(self, 'Missing', 'Please enter a search term.')
            return
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
        repo.errorOccurred.connect(lambda e: self.status_bar.showMessage(f'Repo search error: {e}'))
        self._active_search_procs.append(repo)
        repo.start()

        # AUR search via yay (AUR only)
        aur = QProcess(self)
        aur.setProgram('yay')
        aur.setArguments(['--color=never', '-Ss', term, '--aur'])
        aur.setProcessChannelMode(QProcess.MergedChannels)
        aur.readyReadStandardOutput.connect(lambda: self._collect_search_output_streaming('aur', aur))
        aur.finished.connect(lambda _c=0, _s=0: self._search_one_finished('aur'))
        aur.errorOccurred.connect(lambda e: self.status_bar.showMessage(f'AUR search error: {e}'))
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
                it = QTreeWidgetItem(self.search_results)
                it.setText(0, '')
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(0, Qt.Unchecked)
                it.setText(1, p['name'])
                it.setText(2, p['version'])
                it.setData(1, Qt.UserRole, p)
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

    # ---- Installed ----
    def do_list_installed(self):
        if self.installed_proc and self.installed_proc.state() != QProcess.NotRunning:
            self.installed_proc.kill()
            self.installed_proc.waitForFinished(1000)
        self.installed_view.clear()
        self.installed_view.setSortingEnabled(False)
        self.installed_status.showMessage('Loading installed packages...')
        self.installed_buffer = ''
        self._installed_pending = ''
        self._installed_count = 0
        self.installed_proc = QProcess(self)
        # Use pacman for speed and to avoid TTY prompts
        self.installed_proc.setProgram('pacman')
        self.installed_proc.setArguments(['--color', 'never', '-Qe'])
        self.installed_proc.setProcessChannelMode(QProcess.MergedChannels)
        self.installed_proc.readyReadStandardOutput.connect(self._collect_installed_output_stream)
        self.installed_proc.finished.connect(self._installed_finished_stream)
        self.installed_proc.errorOccurred.connect(lambda e: self.installed_status.showMessage(f'Error: {e}'))
        self.installed_proc.start()

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

    def _collect_installed_output_stream(self):
        chunk = bytes(self.installed_proc.readAllStandardOutput()).decode('utf-8', errors='ignore')
        if not chunk:
            return
        self._installed_pending += chunk
        lines = self._installed_pending.split('\n')
        self._installed_pending = lines.pop()
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
            self._installed_count += 1
        self.installed_status.showMessage(f'Loaded {self._installed_count} installed package(s)...')

    def _installed_finished_stream(self):
        # Flush tail
        tail = clean_control_codes(self._installed_pending).strip()
        if tail:
            parts = tail.split()
            if len(parts) >= 2 and self.installed_view.topLevelItemCount() < self._installed_max_items:
                it = QTreeWidgetItem(self.installed_view)
                it.setText(0, '')
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(0, Qt.Unchecked)
                it.setText(1, parts[0])
                it.setText(2, parts[1])
                self._installed_count += 1
        if self._installed_count == 0:
            self.installed_status.showMessage('No explicitly installed packages found.')
        else:
            self.installed_status.showMessage(f'Found {self._installed_count} package(s).')
        self.installed_view.setSortingEnabled(True)

    def _filter_installed_list(self, text):
        q = (text or '').strip().lower()
        for i in range(self.installed_view.topLevelItemCount()):
            it = self.installed_view.topLevelItem(i)
            hay = f"{it.text(1)} {it.text(2)}".lower()
            it.setHidden(False if not q else (q not in hay))

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

        # Start repo updates
        repo = QProcess(self)
        repo.setProgram('yay')
        repo.setArguments(['--color=never', '-Qu'])
        repo.setProcessChannelMode(QProcess.MergedChannels)
        repo.readyReadStandardOutput.connect(lambda: self._collect_updates_output_stream('repo', repo))
        repo.finished.connect(lambda _c=0, _s=0: self._updates_one_finished('repo'))
        repo.errorOccurred.connect(lambda e: self.update_status.showMessage(f'Repo update error: {e}'))
        self._active_upd_procs.append(repo)
        repo.start()

        # Start AUR updates
        aur = QProcess(self)
        aur.setProgram('yay')
        aur.setArguments(['--color=never', '-Qua'])
        aur.setProcessChannelMode(QProcess.MergedChannels)
        aur.readyReadStandardOutput.connect(lambda: self._collect_updates_output_stream('aur', aur))
        aur.finished.connect(lambda _c=0, _s=0: self._updates_one_finished('aur'))
        aur.errorOccurred.connect(lambda e: self.update_status.showMessage(f'AUR update error: {e}'))
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
            it = QTreeWidgetItem(self.updates_view)
            it.setText(0, '')
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Unchecked)
            it.setText(1, m.group('name'))
            it.setText(2, m.group('old'))
            it.setText(3, m.group('new'))
            it.setText(4, 'Repo' if source == 'repo' else 'AUR')
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
        for i in range(self.updates_view.topLevelItemCount()):
            it = self.updates_view.topLevelItem(i)
            # Match in name, current, new, source
            hay = ' '.join([
                it.text(1), it.text(2), it.text(3), it.text(4)
            ]).lower()
            it.setHidden(False if not q else (q not in hay))

    def do_update_selected(self):
        names = []
        for i in range(self.updates_view.topLevelItemCount()):
            it = self.updates_view.topLevelItem(i)
            if it.checkState(0) == Qt.Checked:
                names.append(it.text(1))
        if not names:
            QMessageBox.information(self, 'Nothing selected', 'Select at least one package to update.')
            return
        display_cmd = f"yay -S --needed {' '.join(names)}"
        if QMessageBox.question(self, 'Confirm update', f"Run in Konsole:\n{display_cmd}") != QMessageBox.Yes:
            return
        try:
            if shutil.which('konsole'):
                self.term.run_konsole_direct(['yay', '-S', '--needed', *names], keep_open=self.keep_open_cb.isChecked())
            else:
                self.term.run(display_cmd)
        except Exception as e:
            QMessageBox.critical(self, 'Terminal error', str(e))

    def do_update_all(self):
        cmd = 'yay -Syu'
        if QMessageBox.question(self, 'Confirm full update', f"Run in Konsole:\n{cmd}") != QMessageBox.Yes:
            return
        try:
            if shutil.which('konsole'):
                self.term.run_konsole_direct(['yay', '-Syu'], keep_open=self.keep_open_cb.isChecked())
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
        proc.errorOccurred.connect(lambda e: self.status_bar.showMessage(f'Info fetch error: {e}'))
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
        # Run directly in Konsole as requested
        display_cmd = f"yay -S {' '.join(names)}"
        if QMessageBox.question(self, 'Confirm install', f"Run in Konsole:\n{display_cmd}") != QMessageBox.Yes:
            return
        try:
            if shutil.which('konsole'):
                self.term.run_konsole_direct(['yay', '-S', *names], keep_open=self.keep_open_cb.isChecked())
            else:
                # Fallback to generic terminal wrapper
                self.term.run(display_cmd)
        except Exception as e:
            QMessageBox.critical(self, 'Terminal error', str(e))

    def do_uninstall(self):
        names = []
        for i in range(self.installed_view.topLevelItemCount()):
            it = self.installed_view.topLevelItem(i)
            if it.checkState(0) == Qt.Checked:
                names.append(it.text(1))
        if not names:
            QMessageBox.information(self, 'Nothing selected', 'Select at least one package to uninstall.')
            return
        display_cmd = f"yay -Rns {' '.join(names)}"
        if QMessageBox.question(self, 'Confirm uninstall', f"Run in Konsole:\n{display_cmd}") != QMessageBox.Yes:
            return
        try:
            if shutil.which('konsole'):
                self.term.run_konsole_direct(['yay', '-Rns', *names], keep_open=self.keep_open_cb.isChecked())
            else:
                self.term.run(display_cmd)
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
