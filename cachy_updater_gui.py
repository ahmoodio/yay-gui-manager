#!/usr/bin/env python3
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import shutil
import shlex

# ------------------------------
#   CONFIG: terminal candidates
# ------------------------------
TERMINAL_CANDIDATES = [
    "kitty",
    "alacritty",
    "konsole",
    "xfce4-terminal",
    "gnome-terminal",
    "wezterm",
    "xterm",
]

# ==============================
#      UPDATE SOURCES
# ==============================

def get_pacman_updates():
    """
    Parse `pacman -Qu` output.
    Handles lines like:
      extra/discord 0.0.116-1 -> 0.0.118-1
      bash 5.2.26-1 -> 5.2.26-2
    Returns list of dicts: {name, current, new, source}
    """
    try:
        output = subprocess.check_output(
            ["pacman", "-Qu"],
            text=True,
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        output = e.output or ""
    except FileNotFoundError:
        return []

    updates = []

    for line in output.strip().splitlines():
        parts = line.split()
        if len(parts) < 4 or "->" not in parts:
            continue

        # First token: may be "extra/discord" or just "bash"
        pkg_token = parts[0]
        if "/" in pkg_token:
            pkg = pkg_token.split("/", 1)[1]
        else:
            pkg = pkg_token

        arrow_index = parts.index("->")

        # Typical pattern: NAME CURRENT -> NEW
        current = parts[1]
        new = parts[arrow_index + 1]

        updates.append({
            "name": pkg,
            "current": current,
            "new": new,
            "source": "pacman"
        })

    return updates


def get_yay_updates():
    """
    Parse `yay -Qua` (AUR-only updates).
    Assumes lines like:
      spotify 1.2.0-1 -> 1.2.1-1
    """
    try:
        output = subprocess.check_output(
            ["yay", "-Qua"],
            text=True,
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        output = e.output or ""
    except FileNotFoundError:
        return []

    updates = []

    for line in output.strip().splitlines():
        parts = line.split()
        if len(parts) < 4 or "->" not in parts:
            continue

        name = parts[0]
        arrow_index = parts.index("->")
        current = parts[1]
        new = parts[arrow_index + 1]

        updates.append({
            "name": name,
            "current": current,
            "new": new,
            "source": "yay"
        })

    return updates


# ==============================
#      TERMINAL LAUNCHER
# ==============================

def launch_in_terminal(cmd_list):
    """
    Launch the given command in an external terminal emulator
    so the user can interact (sudo password, yay prompts, etc.).
    """
    cmd_str = " ".join(shlex.quote(c) for c in cmd_list)

    for term in TERMINAL_CANDIDATES:
        if shutil.which(term):
            try:
                # Most terminals support -e "bash -lc '...'"
                subprocess.Popen(
                    [term, "-e", "bash", "-lc", cmd_str]
                )
                return True
            except Exception:
                continue

    messagebox.showerror(
        "No terminal found",
        "Could not find a terminal emulator.\n\n"
        "Edit TERMINAL_CANDIDATES at the top of the script\n"
        "and add the name of your terminal (e.g. 'foot', 'tilix')."
    )
    return False


# ==============================
#      GUI CLASS
# ==============================

class UpdaterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CachyOS Package Updater (pacman + yay)")
        self.root.geometry("800x450")

        # Store full list so search filter can work
        self.all_updates = []

        self.create_widgets()
        self.refresh_updates()

    def create_widgets(self):
        # ---------- SEARCH BAR ----------
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Search: ").pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.apply_search_filter())

        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.focus()

        # ---------- BUTTONS ----------
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Refresh", command=self.refresh_updates).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Update Selected", command=self.update_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Update All", command=self.update_all).pack(side=tk.LEFT, padx=5)

        # ---------- TABLE ----------
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("name", "current", "new", "source")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        self.tree.heading("name", text="Name")
        self.tree.heading("current", text="Current")
        self.tree.heading("new", text="New")
        self.tree.heading("source", text="Source")

        self.tree.column("name", width=260)
        self.tree.column("current", width=120)
        self.tree.column("new", width=120)
        self.tree.column("source", width=100)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    # ==============================
    #      DATA / FILTERING
    # ==============================

    def refresh_updates(self):
        # Clear table
        for item in self.tree.get_children():
            self.tree.delete(item)

        pac = get_pacman_updates()
        yay = get_yay_updates()
        self.all_updates = pac + yay

        if not self.all_updates:
            messagebox.showinfo("No Updates", "Your system is fully updated 🎉")
            return

        # Fill table initially (unfiltered)
        for pkg in self.all_updates:
            self.tree.insert(
                "",
                tk.END,
                values=(pkg["name"], pkg["current"], pkg["new"], pkg["source"])
            )

        # If user already typed something in search box, reapply filter
        self.apply_search_filter()

    def apply_search_filter(self):
        query = self.search_var.get().lower()

        # clear current rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        # repopulate with items that match query
        for pkg in self.all_updates:
            row_text = f"{pkg['name']} {pkg['current']} {pkg['new']} {pkg['source']}".lower()
            if query in row_text:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(pkg["name"], pkg["current"], pkg["new"], pkg["source"])
                )

    def get_selected_package_names(self):
        names = []
        for item in self.tree.selection():
            vals = self.tree.item(item, "values")
            if vals:
                names.append(vals[0])
        return names

    # ==============================
    #      UPDATE ACTIONS
    # ==============================

    def update_selected(self):
        pkgs = self.get_selected_package_names()
        if not pkgs:
            messagebox.showwarning("No Selection", "Select one or more packages first.")
            return
        self.run_update(pkgs)

    def update_all(self):
        pkgs = [pkg["name"] for pkg in self.all_updates]
        if not pkgs:
            return
        if not messagebox.askyesno("Confirm", "Update ALL listed packages?"):
            return
        self.run_update(pkgs)

    def run_update(self, package_names):
        """
        Build yay command and run it in an external terminal
        so the user can type sudo password, confirm builds, etc.
        """
        cmd = ["yay", "-S"] + package_names
        ok = launch_in_terminal(cmd)
        if ok:
            messagebox.showinfo(
                "Updating",
                "Opened a terminal window running:\n\n" +
                " ".join(cmd) +
                "\n\nUse that terminal to complete the update."
            )


# ==============================
#      MAIN
# ==============================

def main():
    root = tk.Tk()
    UpdaterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
