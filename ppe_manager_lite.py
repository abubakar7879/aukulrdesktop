"""
Aukulr Service Manager (Lite)
==============================
Runs only Redis + Orchestrator.
Master mode (Ctrl+Shift+M): password-protected config & logs.
Built-in expiry with online date verification.
"""

import subprocess
import sys
import os
import json
import time
import hashlib
import base64
import shutil
import threading
import datetime
import logging
from pathlib import Path

# ─── Auto-install dependencies ────────────────────────────────────────────────
REQUIRED = ["cryptography", "requests", "psutil"]
for pkg in REQUIRED:
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

import requests
import psutil
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ─── Constants ────────────────────────────────────────────────────────────────
APP_DIR = Path(os.path.expandvars(r"%LOCALAPPDATA%\AukulrManagerLite"))
CONFIG_FILE = APP_DIR / "config.enc"
RUNTIME_FILE = APP_DIR / "runtime.dat"
SALT_FILE = APP_DIR / "salt.bin"

def _find_python() -> str:
    if not getattr(sys, 'frozen', False):
        return sys.executable
    candidates = [
        shutil.which("python"),
        shutil.which("python3"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python310\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python39\python.exe"),
        r"C:\Python312\python.exe",
        r"C:\Python311\python.exe",
        r"C:\Python310\python.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return "python"

PYTHON_EXE = _find_python()
PW_HASH_FILE = APP_DIR / "pw.hash"
LOG_FILE = APP_DIR / "manager.log"

APP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("AukulrManagerLite")
log.info(f"Frozen: {getattr(sys, 'frozen', False)}, Python: {PYTHON_EXE}, sys.executable: {sys.executable}")

# ─── Default configuration ────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "redis_dir":        r"C:\Users\pc\Documents\PPE",
    "orchestrator_dir": r"C:\Users\pc\Documents\PPE",
    "expiry_date":      "2026-06-01",
}

DATETIME_APIS = [
    "https://worldtimeapi.org/api/timezone/Etc/UTC",
    "http://worldclockapi.com/api/json/utc/now",
    "https://timeapi.io/api/time/current/zone?timeZone=UTC",
]

# ─── Crypto helpers ───────────────────────────────────────────────────────────

def _get_salt():
    if SALT_FILE.exists():
        return SALT_FILE.read_bytes()
    salt = os.urandom(16)
    SALT_FILE.write_bytes(salt)
    return salt

def _derive_key(password: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32,
        salt=_get_salt(), iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def _hash_password(password: str) -> str:
    return hashlib.sha256((_get_salt() + password.encode())).hexdigest()

def set_master_password(password: str):
    PW_HASH_FILE.write_text(_hash_password(password))

def verify_password(password: str) -> bool:
    if not PW_HASH_FILE.exists():
        return False
    return PW_HASH_FILE.read_text() == _hash_password(password)

# ─── Config: encrypted + obfuscated runtime copy ─────────────────────────────

def _save_runtime_config(config: dict):
    data = base64.b64encode(json.dumps(config).encode()).decode()
    RUNTIME_FILE.write_text(data)

def _load_runtime_config() -> dict | None:
    if not RUNTIME_FILE.exists():
        return None
    try:
        return json.loads(base64.b64decode(RUNTIME_FILE.read_text()).decode())
    except Exception:
        return None

def save_config(config: dict, password: str):
    key = _derive_key(password)
    f = Fernet(key)
    CONFIG_FILE.write_bytes(f.encrypt(json.dumps(config).encode()))
    _save_runtime_config(config)

# ─── Online date check ────────────────────────────────────────────────────────

def get_online_date() -> datetime.date | None:
    for url in DATETIME_APIS:
        try:
            r = requests.get(url, timeout=8)
            data = r.json()
            if "datetime" in data:
                return datetime.date.fromisoformat(data["datetime"][:10])
            if "currentDateTime" in data:
                return datetime.date.fromisoformat(data["currentDateTime"][:10])
            if "year" in data and "month" in data and "day" in data:
                return datetime.date(data["year"], data["month"], data["day"])
        except Exception as e:
            log.warning(f"API {url} failed: {e}")
    log.warning("All online date APIs failed – cannot verify date.")
    return None

# ─── Expiry cleanup ──────────────────────────────────────────────────────────

def perform_expiry_cleanup(config: dict):
    log.warning("EXPIRY REACHED – performing cleanup...")
    dirs_to_clean = list(set([
        config["redis_dir"], config["orchestrator_dir"],
    ]))

    for d in dirs_to_clean:
        dp = Path(d)
        if dp.exists():
            for item in dp.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    log.info(f"Deleted: {item}")
                except Exception as e:
                    log.error(f"Failed to delete {item}: {e}")

    log.warning("Cleanup complete.")

# ─── Process management ──────────────────────────────────────────────────────

def find_existing_processes() -> dict[str, list[int]]:
    found = {"redis": [], "orchestrator": []}
    own_pid = os.getpid()
    try:
        own_proc = psutil.Process(own_pid)
        own_tree = {own_pid} | {c.pid for c in own_proc.children(recursive=True)}
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        own_tree = {own_pid}

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.pid in own_tree:
                continue
            pname = (proc.info["name"] or "").lower()
            cmdline = " ".join(proc.info["cmdline"] or []).lower()
            if "redis-server" in pname or "redis-server" in cmdline:
                found["redis"].append(proc.pid)
            elif "orchestrator.py" in cmdline:
                found["orchestrator"].append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found

def kill_processes(pid_dict: dict[str, list[int]]):
    all_pids = [pid for pids in pid_dict.values() for pid in pids]
    if not all_pids:
        return
    log.info(f"Killing existing processes: {pid_dict}")
    procs = []
    for pid in all_pids:
        try:
            p = psutil.Process(pid)
            p.terminate()
            procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _, alive = psutil.wait_procs(procs, timeout=5)
    for p in alive:
        try:
            p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


class ProcessManager:
    def __init__(self, config: dict):
        self.config = config
        self.processes: dict[str, subprocess.Popen] = {}

    def is_running(self, name: str) -> bool:
        p = self.processes.get(name)
        if p is None:
            return False
        return p.poll() is None

    def start_all(self, status_callback=None):
        existing = find_existing_processes()
        kill_processes(existing)
        time.sleep(1)
        self.processes = {}

        steps = [
            ("redis",        ["redis-server"],                   self.config["redis_dir"]),
            ("orchestrator", [PYTHON_EXE, "orchestrator.py"],    self.config["orchestrator_dir"]),
        ]

        # Hide all child windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

        # Force UTF-8 for child processes
        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"

        err_log = APP_DIR / "child_errors.log"

        for name, cmd, cwd in steps:
            log.info(f"Starting {name}: cmd={cmd}, cwd={cwd}")
            if status_callback:
                status_callback(f"Starting {name}...")
            try:
                err_file = open(err_log, "a", encoding="utf-8")
                err_file.write(f"\n{'='*60}\n{datetime.datetime.now()} - Starting {name}\n")
                err_file.write(f"CMD: {cmd}\nCWD: {cwd}\n{'='*60}\n")
                err_file.flush()

                p = subprocess.Popen(
                    cmd, cwd=cwd,
                    env=child_env,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=err_file,
                    stdin=subprocess.DEVNULL,
                )
                self.processes[name] = p

                time.sleep(2 if name == "redis" else 1)
                ret = p.poll()
                if ret is not None:
                    log.error(f"{name} exited immediately with code {ret}. Check {err_log}")
                    if status_callback:
                        status_callback(f"{name} failed (code {ret})")
                else:
                    log.info(f"{name} running (PID {p.pid})")

            except Exception as e:
                log.error(f"Failed to start {name}: {e}")
                if status_callback:
                    status_callback(f"Failed: {name}")

        log.info("All processes started.")

    def stop_all(self):
        log.info("Stopping all processes...")
        for name, p in self.processes.items():
            try:
                parent = psutil.Process(p.pid)
                for child in parent.children(recursive=True):
                    try: child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied): pass
                parent.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(1)
        kill_processes(find_existing_processes())
        self.processes.clear()
        log.info("All processes stopped.")

# ─── GUI ──────────────────────────────────────────────────────────────────────

def run_app(config: dict):
    import tkinter as tk
    from tkinter import messagebox, scrolledtext
    import tkinter.simpledialog as sd

    # ── Step 1: Check expiry BEFORE showing anything ──
    log.info("Checking expiry before launch...")
    today = get_online_date()

    if today is not None:
        expiry = datetime.date.fromisoformat(config["expiry_date"])
        if today > expiry:
            log.warning(f"EXPIRED: {today} > {expiry}")
            perform_expiry_cleanup(config)
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Application Expired",
                "This application has expired.\nPlease contact support."
            )
            root.destroy()
            sys.exit(0)
        else:
            log.info(f"Expiry check passed: {today} <= {expiry}")
    else:
        log.warning("Could not verify date online – skipping expiry check.")

    # ── Step 2: Build the GUI ──
    manager = ProcessManager(config)
    master_unlocked = [False]
    started = [False]

    BG       = "#1a1b2e"
    CARD_BG  = "#242640"
    GREEN    = "#4ade80"
    RED      = "#f87171"
    AMBER    = "#fbbf24"
    BLUE     = "#60a5fa"
    TEXT     = "#e2e8f0"
    DIM      = "#64748b"

    root = tk.Tk()
    root.title("Aukulr Services")
    root.geometry("420x250")
    root.resizable(False, False)
    root.configure(bg=BG)

    SERVICE_NAMES = ["redis", "orchestrator"]
    DISPLAY = {"redis": "Redis Server", "orchestrator": "Orchestrator"}
    service_dots = {}
    service_labels = {}

    tk.Label(root, text="Aukulr Services", font=("Segoe UI", 20, "bold"), bg=BG, fg=TEXT).pack(pady=(20, 4))

    status_msg = tk.StringVar(value="Starting services...")
    tk.Label(root, textvariable=status_msg, font=("Segoe UI", 10), bg=BG, fg=DIM).pack(pady=(0, 14))

    card_frame = tk.Frame(root, bg=BG)
    card_frame.pack(padx=30, fill="x")

    for svc in SERVICE_NAMES:
        row = tk.Frame(card_frame, bg=CARD_BG, padx=14, pady=10)
        row.pack(fill="x", pady=3)
        dot = tk.Label(row, text="\u25cf", font=("Segoe UI", 14), bg=CARD_BG, fg=DIM)
        dot.pack(side="left")
        service_dots[svc] = dot
        tk.Label(row, text=DISPLAY[svc], font=("Segoe UI", 11), bg=CARD_BG, fg=TEXT).pack(side="left", padx=(8, 0))
        stat = tk.Label(row, text="...", font=("Consolas", 9), bg=CARD_BG, fg=DIM)
        stat.pack(side="right")
        service_labels[svc] = stat

    btn_frame = tk.Frame(root, bg=BG)
    btn_frame.pack(pady=18)
    btn_style = dict(font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", bd=0, padx=18, pady=6)

    tk.Button(btn_frame, text="\u27f3  Restart All", bg=BLUE, fg="#1e1e2e",
              activebackground="#93c5fd", command=lambda: _do_restart(), **btn_style).pack(side="left", padx=6)
    tk.Button(btn_frame, text="\u25a0  Stop All", bg=RED, fg="#1e1e2e",
              activebackground="#fca5a5", command=lambda: _do_stop(), **btn_style).pack(side="left", padx=6)

    # ── Hidden master panel ──
    master_frame = tk.Frame(root, bg="#1e1e2e")

    def toggle_master(event=None):
        if master_unlocked[0]:
            if master_frame.winfo_ismapped():
                master_frame.pack_forget()
                root.geometry("420x250")
            else:
                master_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
                root.geometry("420x560")
            return

        pw = sd.askstring("Master Mode", "Enter master password:", show="*", parent=root)
        if not pw or not verify_password(pw):
            if pw is not None:
                messagebox.showerror("Access Denied", "Wrong password.", parent=root)
            return

        master_unlocked[0] = True
        _build_master_panel(pw)
        master_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        root.geometry("420x560")

    def _build_master_panel(pw):
        for w in master_frame.winfo_children():
            w.destroy()

        tk.Frame(master_frame, bg=AMBER, height=2).pack(fill="x", pady=(0, 8))
        tk.Label(master_frame, text="\u2699  Master Panel", font=("Segoe UI", 12, "bold"),
                 bg="#1e1e2e", fg=AMBER).pack(anchor="w")

        cfg_frame = tk.Frame(master_frame, bg="#1e1e2e")
        cfg_frame.pack(fill="x", pady=6)

        fields = {}
        for key, label in [
            ("redis_dir", "Redis Dir"),
            ("orchestrator_dir", "Orchestrator Dir"),
            ("expiry_date", "Expiry (YYYY-MM-DD)"),
        ]:
            row = tk.Frame(cfg_frame, bg="#1e1e2e")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=("Segoe UI", 9), bg="#1e1e2e", fg=DIM,
                     width=18, anchor="w").pack(side="left")
            var = tk.StringVar(value=config.get(key, ""))
            tk.Entry(row, textvariable=var, font=("Consolas", 9),
                     bg="#313244", fg=TEXT, insertbackground=TEXT, relief="flat"
                     ).pack(side="left", fill="x", expand=True, ipady=2)
            fields[key] = var

        def save_changes():
            new_cfg = {k: v.get().strip() for k, v in fields.items()}
            try:
                datetime.date.fromisoformat(new_cfg["expiry_date"])
            except ValueError:
                messagebox.showerror("Error", "Invalid date. Use YYYY-MM-DD.", parent=root)
                return
            save_config(new_cfg, pw)
            config.update(new_cfg)
            manager.config = config
            messagebox.showinfo("Saved", "Config saved. Restart services to apply.", parent=root)

        def change_password():
            new_pw = sd.askstring("Change Password", "New master password:", show="*", parent=root)
            if not new_pw or len(new_pw) < 4:
                messagebox.showerror("Error", "Min 4 characters.", parent=root)
                return
            confirm = sd.askstring("Confirm", "Confirm new password:", show="*", parent=root)
            if new_pw != confirm:
                messagebox.showerror("Error", "Passwords don't match.", parent=root)
                return
            SALT_FILE.unlink(missing_ok=True)
            set_master_password(new_pw)
            save_config(config, new_pw)
            messagebox.showinfo("Done", "Password changed.", parent=root)

        btn_row = tk.Frame(cfg_frame, bg="#1e1e2e")
        btn_row.pack(pady=(6, 4))
        tk.Button(btn_row, text="Save Config", command=save_changes,
                  font=("Segoe UI", 9, "bold"), bg=GREEN, fg="#1e1e2e",
                  relief="flat", padx=12, pady=3, cursor="hand2").pack(side="left", padx=4)
        tk.Button(btn_row, text="Change Password", command=change_password,
                  font=("Segoe UI", 9, "bold"), bg=AMBER, fg="#1e1e2e",
                  relief="flat", padx=12, pady=3, cursor="hand2").pack(side="left", padx=4)

        tk.Label(master_frame, text="Activity Log", font=("Segoe UI", 9, "bold"),
                 bg="#1e1e2e", fg=DIM, anchor="w").pack(fill="x", pady=(6, 2))
        log_box = scrolledtext.ScrolledText(
            master_frame, height=8, font=("Consolas", 8),
            bg="#11111b", fg="#94a3b8", insertbackground="#94a3b8",
            relief="flat", state="disabled"
        )
        log_box.pack(fill="both", expand=True)
        try:
            if LOG_FILE.exists():
                lines = LOG_FILE.read_text(encoding="utf-8").strip().split("\n")[-50:]
                log_box.configure(state="normal")
                log_box.insert("1.0", "\n".join(lines) + "\n")
                log_box.see(tk.END)
                log_box.configure(state="disabled")
        except Exception:
            pass

    root.bind("<Control-Shift-M>", toggle_master)
    root.bind("<Control-Shift-m>", toggle_master)

    # ── Status updates ──
    def update_status():
        all_up = True
        for svc in SERVICE_NAMES:
            if manager.is_running(svc):
                service_labels[svc].config(text="RUNNING", fg=GREEN)
                service_dots[svc].config(fg=GREEN)
            else:
                service_labels[svc].config(text="STOPPED", fg=RED)
                service_dots[svc].config(fg=RED)
                all_up = False
        if all_up and manager.processes:
            status_msg.set("All services running")

    def _start_thread():
        if started[0]:
            log.info("Start already in progress, skipping duplicate call.")
            return
        started[0] = True
        def cb(msg):
            root.after(0, lambda m=msg: status_msg.set(m))
        manager.start_all(status_callback=cb)
        root.after(0, lambda: status_msg.set("All services running"))
        root.after(0, update_status)
        started[0] = False

    def _stop_thread():
        manager.stop_all()
        root.after(0, lambda: status_msg.set("Services stopped"))
        root.after(0, update_status)

    def _do_restart():
        status_msg.set("Restarting services...")
        threading.Thread(target=_start_thread, daemon=True).start()

    def _do_stop():
        status_msg.set("Stopping services...")
        threading.Thread(target=_stop_thread, daemon=True).start()

    def on_close():
        manager.stop_all()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    def periodic():
        update_status()
        root.after(5000, periodic)

    root.after(200, periodic)
    root.after(500, lambda: threading.Thread(target=_start_thread, daemon=True).start())

    root.mainloop()

# ─── First-time setup ────────────────────────────────────────────────────────

def first_time_setup():
    import tkinter as tk
    from tkinter import messagebox
    import tkinter.simpledialog as sd

    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo("First Run Setup",
        "Welcome! Set a master password to protect configuration.\n"
        "The client will never see this.", parent=root)

    password = sd.askstring("Setup", "Create master password:", show="*", parent=root)
    if not password or len(password) < 4:
        messagebox.showerror("Error", "Password must be at least 4 characters.", parent=root)
        root.destroy()
        sys.exit(1)
    confirm = sd.askstring("Setup", "Confirm password:", show="*", parent=root)
    if password != confirm:
        messagebox.showerror("Error", "Passwords don't match.", parent=root)
        root.destroy()
        sys.exit(1)

    set_master_password(password)
    save_config(DEFAULT_CONFIG, password)
    messagebox.showinfo("Done", "Setup complete! The app will now launch.\n\n"
        "Tip: Press Ctrl+Shift+M anytime to access master panel.", parent=root)
    root.destroy()
    return DEFAULT_CONFIG.copy()

# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    config = _load_runtime_config()

    if config is None:
        config = first_time_setup()
        if config is None:
            sys.exit(0)

    run_app(config)

if __name__ == "__main__":
    main()