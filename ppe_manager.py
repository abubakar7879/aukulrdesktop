"""
Aukulr Service Manager
====================
Client-facing app: double-click to auto-start all services.
Master mode (Ctrl+Shift+M): password-protected config & logs.
License validated against Aukulr admin server on every start.
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
APP_DIR      = Path(os.path.expandvars(r"%LOCALAPPDATA%\AukulrManager"))
CONFIG_FILE  = APP_DIR / "config.enc"
RUNTIME_FILE = APP_DIR / "runtime.dat"
SALT_FILE    = APP_DIR / "salt.bin"
PW_HASH_FILE = APP_DIR / "pw.hash"
LOG_FILE     = APP_DIR / "manager.log"

APP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("AukulrManager")

# ─── Python executable ────────────────────────────────────────────────────────

def _find_python() -> str:
    if not getattr(sys, "frozen", False):
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
log.info(f"Frozen: {getattr(sys, 'frozen', False)}, Python: {PYTHON_EXE}")

# ─── Default configuration ────────────────────────────────────────────────────

DEFAULT_SERVICES = [
    {"folder": "AukulrUI", "cmd": "npm run start",         "enabled": True},
    {"folder": "AukulrB",  "cmd": "npm run dev",           "enabled": True},
    {"folder": "AukulrP",  "cmd": "redis-server",          "enabled": True},
    {"folder": "AukulrP",  "cmd": "python orchestrator.py","enabled": True},
    {"folder": "AukulrP",  "cmd": "python debug_viewer.py","enabled": False},
    {"folder": "AukulrG",  "cmd": "python main.py",        "enabled": False},
]

DEFAULT_CONFIG = {
    "base_path":    str(Path.home() / "Documents"),
    "api_base_url": "http://localhost:3000",
    "services":     DEFAULT_SERVICES,
}

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

# ─── Config persistence ───────────────────────────────────────────────────────

def _save_runtime_config(config: dict):
    RUNTIME_FILE.write_text(base64.b64encode(json.dumps(config).encode()).decode())

def _load_runtime_config() -> dict | None:
    if not RUNTIME_FILE.exists():
        return None
    try:
        return json.loads(base64.b64decode(RUNTIME_FILE.read_text()).decode())
    except Exception:
        return None

def save_config(config: dict, password: str):
    key = _derive_key(password)
    CONFIG_FILE.write_bytes(Fernet(key).encrypt(json.dumps(config).encode()))
    _save_runtime_config(config)

# ─── Hardware ID ──────────────────────────────────────────────────────────────

def _hidden_check_output(cmd: list[str]) -> str:
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = subprocess.CREATE_NO_WINDOW
    return subprocess.check_output(
        cmd, text=True, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL, timeout=5,
        startupinfo=startupinfo, creationflags=creationflags,
    )

def _clean_id(value: str) -> str:
    return "".join(ch for ch in value.strip().upper() if ch.isalnum() or ch in "-_")

def get_cpu_id() -> str | None:
    commands = [
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty ProcessorId).Trim()"],
        ["wmic", "cpu", "get", "ProcessorId"],
    ]
    for cmd in commands:
        try:
            output = _hidden_check_output(cmd)
            for line in output.splitlines():
                line = line.strip()
                if not line or line.lower() == "processorid":
                    continue
                cpu_id = _clean_id(line)
                if cpu_id:
                    return cpu_id
        except Exception as e:
            log.warning(f"CPU ID command failed ({cmd[0]}): {e}")
    return None

# ─── License validation ───────────────────────────────────────────────────────

def validate_license(config: dict, cpu_id: str) -> tuple[bool, str]:
    api_base_url = (config.get("api_base_url") or "").strip().rstrip("/")
    if not api_base_url:
        return False, "API base URL is not configured. Open master panel to set it."

    url = f"{api_base_url}/api/{cpu_id.lower()}"
    log.info(f"Checking license at {api_base_url}/api/****{cpu_id[-6:]}")

    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        log.error(f"License server unreachable: {e}")
        return False, "Cannot reach license server.\nCheck internet connection or contact support."

    try:
        data = resp.json()
    except ValueError:
        log.error(f"Non-JSON response: HTTP {resp.status_code}")
        return False, "License server returned an invalid response. Contact support."

    if resp.status_code == 404 or not data.get("enabled"):
        return False, "NOT_REGISTERED"

    if resp.status_code >= 400:
        return False, f"License server error (HTTP {resp.status_code}). Contact support."

    current_date = data.get("currentDate", "")
    expiry_date  = data.get("expiryDate", "")

    if not current_date or not expiry_date:
        return False, "Invalid license response (missing dates). Contact support."

    if current_date > expiry_date:
        log.warning(f"License expired: {current_date} > {expiry_date}")
        return False, f"License expired on {expiry_date}.\nContact support to renew."

    log.info(f"License valid. Expires: {expiry_date}")
    return True, "valid"

# ─── Registration ─────────────────────────────────────────────────────────────

def submit_registration(config: dict, cpu_id: str, clinic_name: str, contact: str,
                        machine_name: str, windows_user: str) -> tuple[bool, str]:
    api_base_url = (config.get("api_base_url") or "").strip().rstrip("/")
    try:
        resp = requests.post(
            f"{api_base_url}/api/register",
            json={
                "cpuId": cpu_id,
                "clinicName": clinic_name,
                "contact": contact,
                "machineName": machine_name,
                "windowsUser": windows_user,
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("success"):
            return True, data.get("message", "Registration submitted.")
        return False, data.get("message", "Registration failed.")
    except Exception as e:
        log.error(f"Registration request failed: {e}")
        return False, "Could not reach server. Check internet connection."

# ─── Command parsing ──────────────────────────────────────────────────────────

def _parse_cmd(cmd_str: str) -> list[str]:
    parts = cmd_str.strip().split()
    if not parts:
        return []
    exe = parts[0].lower()
    if exe == "python":
        return [PYTHON_EXE] + parts[1:]
    elif exe == "npm":
        return ["npm.cmd"] + parts[1:]
    return parts

def _service_key(svc: dict) -> str:
    return f"{svc['folder']}::{svc['cmd']}"

# ─── Process management ───────────────────────────────────────────────────────

def kill_all_known_processes(config: dict | None = None):
    own_pid = os.getpid()
    try:
        own_tree = {own_pid} | {c.pid for c in psutil.Process(own_pid).children(recursive=True)}
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        own_tree = {own_pid}

    base = (config or {}).get("base_path", "").lower().rstrip("\\/") if config else ""

    targets = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.pid in own_tree:
                continue
            pname   = (proc.info["name"] or "").lower()
            cmdline = " ".join(proc.info["cmdline"] or []).lower()
            # Only kill processes related to the managed service folders
            in_base = base and base in cmdline
            if ("redis-server" in pname or "redis-server" in cmdline
                    or (in_base and "orchestrator.py" in cmdline)
                    or (in_base and "debug_viewer.py" in cmdline)
                    or (in_base and "main.py" in cmdline)
                    or (in_base and "node" in pname)):
                targets.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    for p in targets:
        try: p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    _, alive = psutil.wait_procs(targets, timeout=5)
    for p in alive:
        try: p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    if targets:
        log.info(f"Killed {len(targets)} existing processes.")


class ProcessManager:
    def __init__(self, config: dict):
        self.config  = config
        self.procs: dict[str, subprocess.Popen] = {}

    def is_running(self, key: str) -> bool:
        p = self.procs.get(key)
        return p is not None and p.poll() is None

    def _enabled_services(self) -> list[dict]:
        return [s for s in self.config.get("services", []) if s.get("enabled")]

    def start_all(self, status_callback=None):
        kill_all_known_processes(self.config)
        time.sleep(1)
        self.procs = {}

        base = self.config.get("base_path", "").rstrip("\\/")
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"

        err_log = APP_DIR / "child_errors.log"

        for svc in self._enabled_services():
            key  = _service_key(svc)
            cwd  = os.path.join(base, svc["folder"])
            cmd  = _parse_cmd(svc["cmd"])
            label = f"{svc['folder']} › {svc['cmd']}"

            if not cmd:
                log.warning(f"Empty command for service {key}, skipping.")
                continue

            log.info(f"Starting {label}: cwd={cwd}")
            if status_callback:
                status_callback(f"Starting {label}...")

            try:
                with open(err_log, "a", encoding="utf-8") as ef:
                    ef.write(f"\n{'='*60}\n{datetime.datetime.now()} — {label}\nCMD: {cmd}\nCWD: {cwd}\n{'='*60}\n")

                p = subprocess.Popen(
                    cmd, cwd=cwd,
                    env=child_env,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=open(err_log, "a", encoding="utf-8"),
                    stdin=subprocess.DEVNULL,
                )
                self.procs[key] = p
                time.sleep(2 if "redis" in svc["cmd"].lower() else 1)
                if p.poll() is not None:
                    log.error(f"{label} exited immediately (code {p.poll()}). Check {err_log}")
                else:
                    log.info(f"{label} running (PID {p.pid})")
            except Exception as e:
                log.error(f"Failed to start {label}: {e}")
                if status_callback:
                    status_callback(f"Failed: {label}")

        log.info("Start sequence complete.")

    def stop_all(self):
        log.info("Stopping all managed processes...")
        for key, p in self.procs.items():
            try:
                parent = psutil.Process(p.pid)
                for child in parent.children(recursive=True):
                    try: child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied): pass
                parent.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(1)
        kill_all_known_processes(self.config)
        self.procs.clear()
        log.info("All processes stopped.")

# ─── GUI ──────────────────────────────────────────────────────────────────────

def run_app(config: dict, cpu_id: str):
    import tkinter as tk
    from tkinter import messagebox, scrolledtext
    import tkinter.simpledialog as sd

    # ── License check ──
    log.info("Validating license...")
    ok, msg = validate_license(config, cpu_id)

    if not ok:
        if msg == "NOT_REGISTERED":
            _show_registration_dialog(config, cpu_id)
            return
        log.warning(f"License check failed: {msg}")
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("License Error", f"{msg}\n\nServices were not started.")
        root.destroy()
        sys.exit(0)

    log.info("License valid. Launching service manager.")

    manager = ProcessManager(config)
    master_unlocked = [False]
    started = [False]

    BG      = "#1a1b2e"
    CARD_BG = "#242640"
    GREEN   = "#4ade80"
    RED     = "#f87171"
    AMBER   = "#fbbf24"
    BLUE    = "#60a5fa"
    TEXT    = "#e2e8f0"
    DIM     = "#64748b"

    enabled_svcs = [s for s in config.get("services", []) if s.get("enabled")]
    COLS    = 2
    WIN_W   = 680
    WIN_H   = 300

    root = tk.Tk()
    root.title("Aukulr Services")
    root.geometry(f"{WIN_W}x{WIN_H}")
    root.resizable(False, False)
    root.configure(bg=BG)

    # ── Top bar: title + status + machine ID ──
    top_bar = tk.Frame(root, bg=BG)
    top_bar.pack(fill="x", padx=24, pady=(18, 10))

    tk.Label(top_bar, text="Aukulr Services", font=("Segoe UI", 18, "bold"),
             bg=BG, fg=TEXT).pack(side="left")

    right_info = tk.Frame(top_bar, bg=BG)
    right_info.pack(side="right")
    status_msg = tk.StringVar(value="Starting services...")
    tk.Label(right_info, textvariable=status_msg, font=("Segoe UI", 9),
             bg=BG, fg=DIM).pack(anchor="e")
    tk.Label(right_info, text=f"ID: {cpu_id}", font=("Consolas", 7),
             bg=BG, fg=DIM).pack(anchor="e")

    # ── Service cards grid ──
    card_frame = tk.Frame(root, bg=BG)
    card_frame.pack(padx=20, fill="x")

    service_dots   = {}
    service_labels = {}

    for i, svc in enumerate(enabled_svcs):
        key    = _service_key(svc)
        col    = i % COLS
        row_i  = i // COLS
        card = tk.Frame(card_frame, bg=CARD_BG, padx=14, pady=10)
        card.grid(row=row_i, column=col, padx=5, pady=4, sticky="ew")
        card_frame.columnconfigure(col, weight=1)

        top_row = tk.Frame(card, bg=CARD_BG)
        top_row.pack(fill="x")
        dot = tk.Label(top_row, text="●", font=("Segoe UI", 11), bg=CARD_BG, fg=DIM)
        dot.pack(side="left")
        tk.Label(top_row, text=svc["folder"], font=("Segoe UI", 10, "bold"),
                 bg=CARD_BG, fg=TEXT).pack(side="left", padx=(6, 0))
        stat = tk.Label(top_row, text="...", font=("Consolas", 8), bg=CARD_BG, fg=DIM)
        stat.pack(side="right")

        tk.Label(card, text=svc["cmd"], font=("Consolas", 8),
                 bg=CARD_BG, fg=DIM).pack(anchor="w", padx=(18, 0))

        service_dots[key]   = dot
        service_labels[key] = stat

    # ── Buttons ──
    btn_frame = tk.Frame(root, bg=BG)
    btn_frame.pack(pady=16)
    bs = dict(font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", bd=0, padx=30, pady=10)
    tk.Button(btn_frame, text="⟳  Restart All", bg=BLUE, fg="#1e1e2e",
              activebackground="#93c5fd", command=lambda: _do_restart(), **bs).pack(side="left", padx=10)
    tk.Button(btn_frame, text="■  Stop All", bg=RED, fg="#1e1e2e",
              activebackground="#fca5a5", command=lambda: _do_stop(), **bs).pack(side="left", padx=10)

    # ── Master panel ──
    master_frame = tk.Frame(root, bg="#1e1e2e")

    def toggle_master(event=None):
        if master_unlocked[0]:
            if master_frame.winfo_ismapped():
                master_frame.pack_forget()
                root.geometry(f"{WIN_W}x{WIN_H}")
            else:
                master_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
                root.geometry(f"{WIN_W}x{WIN_H + 500}")
            return
        pw = sd.askstring("Master Mode", "Enter master password:", show="*", parent=root)
        if not pw or not verify_password(pw):
            if pw is not None:
                messagebox.showerror("Access Denied", "Wrong password.", parent=root)
            return
        master_unlocked[0] = True
        _build_master_panel(pw)
        master_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        root.geometry(f"{WIN_W}x{WIN_H + 500}")

    def _build_master_panel(pw):
        for w in master_frame.winfo_children():
            w.destroy()

        tk.Frame(master_frame, bg=AMBER, height=2).pack(fill="x", pady=(0, 6))
        tk.Label(master_frame, text="⚙  Master Panel", font=("Segoe UI", 12, "bold"),
                 bg="#1e1e2e", fg=AMBER).pack(anchor="w")

        # ── Base path + API URL ──
        top_frame = tk.Frame(master_frame, bg="#1e1e2e")
        top_frame.pack(fill="x", pady=4)

        base_var = tk.StringVar(value=config.get("base_path", ""))
        api_var  = tk.StringVar(value=config.get("api_base_url", ""))

        for label, var in [("Base Path", base_var), ("API Base URL", api_var)]:
            row = tk.Frame(top_frame, bg="#1e1e2e")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=("Segoe UI", 9), bg="#1e1e2e", fg=DIM,
                     width=14, anchor="w").pack(side="left")
            tk.Entry(row, textvariable=var, font=("Consolas", 9),
                     bg="#313244", fg=TEXT, insertbackground=TEXT,
                     relief="flat").pack(side="left", fill="x", expand=True, ipady=2)

        # ── Services table ──
        tk.Label(master_frame, text="Services", font=("Segoe UI", 9, "bold"),
                 bg="#1e1e2e", fg=DIM).pack(anchor="w", pady=(8, 2))

        table_frame = tk.Frame(master_frame, bg="#1e1e2e")
        table_frame.pack(fill="x")

        # Header
        hdr = tk.Frame(table_frame, bg="#1e1e2e")
        hdr.pack(fill="x")
        for txt, w in [("Folder", 10), ("Command", 22), ("On", 3)]:
            tk.Label(hdr, text=txt, font=("Segoe UI", 8, "bold"), bg="#1e1e2e",
                     fg=DIM, width=w, anchor="w").pack(side="left", padx=2)
        tk.Label(hdr, text="", width=2, bg="#1e1e2e").pack(side="left")

        svc_rows: list[dict] = []

        def add_svc_row(svc=None):
            row_frame = tk.Frame(table_frame, bg="#1e1e2e")
            row_frame.pack(fill="x", pady=1)

            folder_var  = tk.StringVar(value=(svc or {}).get("folder", ""))
            cmd_var     = tk.StringVar(value=(svc or {}).get("cmd", ""))
            enabled_var = tk.BooleanVar(value=(svc or {}).get("enabled", True))

            tk.Entry(row_frame, textvariable=folder_var, font=("Consolas", 8),
                     bg="#313244", fg=TEXT, insertbackground=TEXT,
                     relief="flat", width=10).pack(side="left", padx=2, ipady=2)
            tk.Entry(row_frame, textvariable=cmd_var, font=("Consolas", 8),
                     bg="#313244", fg=TEXT, insertbackground=TEXT,
                     relief="flat", width=22).pack(side="left", padx=2, ipady=2)
            tk.Checkbutton(row_frame, variable=enabled_var, bg="#1e1e2e",
                           activebackground="#1e1e2e", selectcolor="#313244").pack(side="left", padx=2)

            entry = {"frame": row_frame, "folder": folder_var, "cmd": cmd_var, "enabled": enabled_var}
            svc_rows.append(entry)

            def remove_row():
                row_frame.destroy()
                svc_rows.remove(entry)

            tk.Button(row_frame, text="✕", command=remove_row,
                      font=("Segoe UI", 8), bg="#313244", fg=RED,
                      relief="flat", padx=4, cursor="hand2").pack(side="left", padx=2)

        for svc in config.get("services", DEFAULT_SERVICES):
            add_svc_row(svc)

        tk.Button(table_frame, text="+ Add Service", command=add_svc_row,
                  font=("Segoe UI", 8), bg="#313244", fg=BLUE,
                  relief="flat", padx=8, pady=2, cursor="hand2").pack(anchor="w", pady=(4, 0))

        # ── Save / Change password ──
        def save_changes():
            new_base = base_var.get().strip()
            new_api  = api_var.get().strip()
            if not new_base:
                messagebox.showerror("Error", "Base path is required.", parent=root)
                return
            if not new_api:
                messagebox.showerror("Error", "API base URL is required.", parent=root)
                return
            new_services = []
            for entry in svc_rows:
                folder = entry["folder"].get().strip()
                cmd    = entry["cmd"].get().strip()
                if folder and cmd:
                    new_services.append({
                        "folder":  folder,
                        "cmd":     cmd,
                        "enabled": entry["enabled"].get(),
                    })
            new_cfg = {
                "base_path":    new_base,
                "api_base_url": new_api,
                "services":     new_services,
            }
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

        btn_row = tk.Frame(master_frame, bg="#1e1e2e")
        btn_row.pack(pady=(8, 4))
        tk.Button(btn_row, text="Save Config", command=save_changes,
                  font=("Segoe UI", 9, "bold"), bg=GREEN, fg="#1e1e2e",
                  relief="flat", padx=12, pady=3, cursor="hand2").pack(side="left", padx=4)
        tk.Button(btn_row, text="Change Password", command=change_password,
                  font=("Segoe UI", 9, "bold"), bg=AMBER, fg="#1e1e2e",
                  relief="flat", padx=12, pady=3, cursor="hand2").pack(side="left", padx=4)

        # ── Log viewer ──
        tk.Label(master_frame, text="Activity Log", font=("Segoe UI", 9, "bold"),
                 bg="#1e1e2e", fg=DIM, anchor="w").pack(fill="x", pady=(8, 2))
        log_box = scrolledtext.ScrolledText(
            master_frame, height=8, font=("Consolas", 8),
            bg="#11111b", fg="#94a3b8", insertbackground="#94a3b8",
            relief="flat", state="disabled",
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

    # ── Status polling ──
    def update_status():
        running_count = 0
        total = len(service_dots)
        for key in list(service_dots.keys()):
            if manager.is_running(key):
                service_labels[key].config(text="RUNNING", fg=GREEN)
                service_dots[key].config(fg=GREEN)
                running_count += 1
            else:
                service_labels[key].config(text="STOPPED", fg=RED)
                service_dots[key].config(fg=RED)
        if manager.procs:
            if running_count == total:
                status_msg.set("All services running")
            elif running_count == 0:
                status_msg.set("All services stopped")
            else:
                status_msg.set(f"{running_count}/{total} services running")

    def _start_thread():
        if started[0]:
            return
        started[0] = True
        ok2, msg2 = validate_license(config, cpu_id)
        if not ok2:
            def fail():
                status_msg.set("License check failed")
                messagebox.showerror("License Error",
                                     f"{msg2}\n\nServices were not started.", parent=root)
            root.after(0, fail)
            started[0] = False
            return
        manager.start_all(status_callback=lambda m: root.after(0, lambda mm=m: status_msg.set(mm)))
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
    root.after(500, lambda: periodic())

    def periodic():
        update_status()
        root.after(5000, periodic)

    root.after(600, lambda: threading.Thread(target=_start_thread, daemon=True).start())
    root.mainloop()


def _show_registration_dialog(config: dict, cpu_id: str):
    import tkinter as tk
    from tkinter import messagebox
    import tkinter.simpledialog as sd
    import socket

    machine_name = ""
    windows_user = ""
    try:
        machine_name = socket.gethostname()
    except Exception:
        pass
    try:
        windows_user = os.getlogin()
    except Exception:
        pass

    root = tk.Tk()
    root.title("Register This Device")
    root.geometry("420x340")
    root.resizable(False, False)
    BG   = "#1a1b2e"
    TEXT = "#e2e8f0"
    DIM  = "#64748b"
    BLUE = "#60a5fa"
    root.configure(bg=BG)

    tk.Label(root, text="Register This Device", font=("Segoe UI", 16, "bold"),
             bg=BG, fg=TEXT).pack(pady=(24, 4))
    tk.Label(root, text="This machine is not registered. Fill in your details\nand submit — your administrator will approve access.",
             font=("Segoe UI", 9), bg=BG, fg=DIM, justify="center").pack(pady=(0, 16))

    form_frame = tk.Frame(root, bg=BG)
    form_frame.pack(padx=32, fill="x")

    fields: dict[str, tk.StringVar] = {}
    for label, key, initial, readonly in [
        ("Clinic / Company Name", "clinic_name", "", False),
        ("Contact (phone / email)", "contact",     "", False),
        ("Machine ID",             "cpu_id",       cpu_id,       True),
        ("Hostname",               "machine_name", machine_name, True),
        ("Windows User",           "windows_user", windows_user, True),
    ]:
        row = tk.Frame(form_frame, bg=BG)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, font=("Segoe UI", 9), bg=BG, fg=DIM,
                 width=22, anchor="w").pack(side="left")
        var = tk.StringVar(value=initial)
        state = "readonly" if readonly else "normal"
        entry = tk.Entry(row, textvariable=var, font=("Consolas", 9),
                         bg="#313244" if not readonly else "#1e1e2e",
                         fg=TEXT, insertbackground=TEXT, relief="flat",
                         state=state)
        entry.pack(side="left", fill="x", expand=True, ipady=2)
        fields[key] = var

    submitted = [False]

    def submit():
        clinic = fields["clinic_name"].get().strip()
        contact = fields["contact"].get().strip()
        if not clinic or not contact:
            messagebox.showerror("Required", "Clinic name and contact are required.", parent=root)
            return
        ok, msg = submit_registration(
            config, cpu_id, clinic, contact, machine_name, windows_user
        )
        if ok:
            messagebox.showinfo(
                "Request Submitted",
                f"{msg}\n\nPlease contact your administrator to approve your device.\n"
                f"Share your Machine ID if needed:\n{cpu_id}",
                parent=root,
            )
            submitted[0] = True
            root.destroy()
        else:
            messagebox.showerror("Error", msg, parent=root)

    tk.Button(root, text="Submit Registration", command=submit,
              font=("Segoe UI", 10, "bold"), bg=BLUE, fg="#1e1e2e",
              relief="flat", padx=20, pady=8, cursor="hand2").pack(pady=16)

    root.mainloop()


# ─── First-time setup ─────────────────────────────────────────────────────────

def first_time_setup() -> dict:
    import tkinter as tk
    from tkinter import messagebox
    import tkinter.simpledialog as sd

    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo(
        "First Run Setup",
        "Welcome to Aukulr Service Manager!\n\n"
        "Set a master password to protect configuration.\n"
        "Clients will never see this password.",
        parent=root,
    )

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

    api_base_url = sd.askstring(
        "Server Setup",
        "Enter the Aukulr server URL\n(e.g. http://localhost:3000 for local testing):",
        initialvalue=DEFAULT_CONFIG["api_base_url"],
        parent=root,
    )
    if not api_base_url:
        messagebox.showerror("Error", "Server URL is required.", parent=root)
        root.destroy()
        sys.exit(1)

    config = DEFAULT_CONFIG.copy()
    config["api_base_url"] = api_base_url.strip()

    set_master_password(password)
    save_config(config, password)
    messagebox.showinfo(
        "Setup Complete",
        "Setup complete! The app will now launch.\n\n"
        "Tip: Press Ctrl+Shift+M anytime to open the master panel\n"
        "where you can change the base path and manage services.",
        parent=root,
    )
    root.destroy()
    return config

# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    cpu_id = get_cpu_id()
    if not cpu_id:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk(); r.withdraw()
        messagebox.showerror("Error", "Could not read CPU ID from this machine.\nContact support.")
        r.destroy()
        sys.exit(1)

    log.info(f"CPU ID: ****{cpu_id[-6:]}")

    config = _load_runtime_config()
    if config is None:
        config = first_time_setup()
    else:
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)
        if "services" not in config:
            merged["services"] = DEFAULT_SERVICES
        config = merged

    run_app(config, cpu_id)

if __name__ == "__main__":
    main()
