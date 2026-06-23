"""
Aukulr Service Manager
====================
Client-facing app: double-click to auto-start all services.
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
APP_DIR = Path(os.path.expandvars(r"%LOCALAPPDATA%\AukulrManager"))
CONFIG_FILE = APP_DIR / "config.enc"
RUNTIME_FILE = APP_DIR / "runtime.dat"
SALT_FILE = APP_DIR / "salt.bin"

def _find_python() -> str:
    """
    Find the real python.exe path.
    When running as a PyInstaller .exe, sys.executable points to the .exe itself,
    NOT to python.exe. We must find the actual Python interpreter.
    """
    # If not frozen (running as .py script), sys.executable is correct
    if not getattr(sys, 'frozen', False):
        return sys.executable

    # If frozen, search for python.exe in common locations
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

    # Last resort — hope 'python' is in PATH
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
log = logging.getLogger("AukulrManager")
log.info(f"Frozen: {getattr(sys, 'frozen', False)}, Python: {PYTHON_EXE}, sys.executable: {sys.executable}")

# ─── Default configuration ────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "redis_dir":        r"C:\Users\pc\Documents\PPE",
    "orchestrator_dir": r"C:\Users\pc\Documents\PPE",
    "backend_dir":      r"C:\Users\pc\Documents\PPEB",
    "frontend_dir":     r"C:\Users\pc\Documents\PPEUI",
    "license_api_url":  "https://license.aukulr.ai/api/license/validate",
    "license_token":    "",
}

APP_VERSION = "1.0.0"

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

# ─── License validation ──────────────────────────────────────────────────────

def _hidden_check_output(cmd: list[str]) -> str:
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = subprocess.CREATE_NO_WINDOW
    return subprocess.check_output(
        cmd,
        text=True,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        timeout=5,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )

def _clean_id(value: str) -> str:
    value = value.strip().upper()
    return "".join(ch for ch in value if ch.isalnum() or ch in "-_")

def get_cpu_id() -> str | None:
    """Return the processor ID used as the MVP hardware ID."""
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

def _mask_token(token: str) -> str:
    token = token.strip()
    if len(token) <= 4:
        return "****"
    return f"****{token[-4:]}"

def validate_license(config: dict) -> tuple[bool, str, dict]:
    api_url = (config.get("license_api_url") or "").strip()
    token = (config.get("license_token") or "").strip()

    if not api_url:
        return False, "License API URL is missing. Please contact support.", {}
    if not token:
        return False, "License token is missing. Please contact support.", {}

    cpu_id = get_cpu_id()
    if not cpu_id:
        return False, "Could not read CPU ID for license validation. Please contact support.", {}

    payload = {
        "hardwareId": cpu_id,
        "hardwareType": "cpu_id",
        "token": token,
        "app": "AukulrManager",
        "appVersion": APP_VERSION,
    }

    log.info(f"Validating license for CPU ID ending {cpu_id[-6:]} with token {_mask_token(token)}")
    try:
        response = requests.post(api_url, json=payload, timeout=10)
    except requests.RequestException as e:
        log.error(f"License server unreachable: {e}")
        return False, "License server is unreachable. Please check internet connection or contact support.", {}

    try:
        data = response.json()
    except ValueError:
        log.error(f"License server returned non-JSON response: HTTP {response.status_code}")
        return False, "License server returned an invalid response. Please contact support.", {}

    if response.status_code >= 400:
        reason = data.get("reason") or f"http_{response.status_code}"
        message = data.get("message") or f"License validation failed: {reason}"
        log.warning(f"License rejected: {reason}")
        return False, message, data

    if data.get("valid") is True:
        log.info("License validation passed.")
        return True, data.get("message", "License valid."), data

    reason = data.get("reason") or "invalid"
    message = data.get("message") or f"License validation failed: {reason}"
    log.warning(f"License rejected: {reason}")
    return False, message, data

# ─── Process management ──────────────────────────────────────────────────────

def find_existing_processes() -> dict[str, list[int]]:
    found = {"redis": [], "orchestrator": [], "backend": [], "frontend": []}
    own_pid = os.getpid()
    # Collect own PID + all child PIDs so we never kill ourselves
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
            elif "node" in pname:
                norm = cmdline.replace("\\", "/").lower()
                if "ppeb" in norm:
                    found["backend"].append(proc.pid)
                elif "ppeui" in norm:
                    found["frontend"].append(proc.pid)
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
        """Check if a managed process is still alive."""
        p = self.processes.get(name)
        if p is None:
            return False
        return p.poll() is None  # None means still running

    def start_all(self, status_callback=None):
        existing = find_existing_processes()
        kill_processes(existing)
        time.sleep(1)
        self.processes = {}

        steps = [
            ("redis",        ["redis-server"],                                    self.config["redis_dir"]),
            ("orchestrator", [PYTHON_EXE, "orchestrator.py"],                     self.config["orchestrator_dir"]),
            ("backend",      ["npm.cmd", "run", "dev", "--", "-H", "0.0.0.0"],    self.config["backend_dir"]),
            ("frontend",     ["npm.cmd", "run", "dev", "--", "-H", "0.0.0.0"],    self.config["frontend_dir"]),
        ]

        # Hide all child windows completely
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

        # Force UTF-8 for child processes so emoji/unicode output doesn't crash them
        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"

        # Log file for child process errors
        err_log = APP_DIR / "child_errors.log"

        for name, cmd, cwd in steps:
            log.info(f"Starting {name}: cmd={cmd}, cwd={cwd}")
            if status_callback:
                status_callback(f"Starting {name}...")
            try:
                # Open error log for this process so we can see why it fails
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

                # Wait a moment and check if it died immediately
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

    # Validate license before showing the service dashboard or starting anything.
    log.info("Validating license before launch...")
    license_ok, license_message, _ = validate_license(config)
    if not license_ok:
        log.warning(f"License validation failed before launch: {license_message}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "License Validation Failed",
            f"{license_message}\n\nServices were not started."
        )
        root.destroy()
        sys.exit(0)
    log.info("License validation passed before launch.")

    # ── Step 2: Build the GUI ──
    manager = ProcessManager(config)
    master_unlocked = [False]
    started = [False]  # guard against double-start

    # Colors
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
    root.geometry("420x340")
    root.resizable(False, False)
    root.configure(bg=BG)

    SERVICE_NAMES = ["redis", "orchestrator", "backend", "frontend"]
    DISPLAY = {"redis": "Redis Server", "orchestrator": "Orchestrator", "backend": "Backend API", "frontend": "Frontend UI"}
    service_dots = {}
    service_labels = {}

    # Title
    tk.Label(root, text="Aukulr Services", font=("Segoe UI", 20, "bold"), bg=BG, fg=TEXT).pack(pady=(20, 4))

    status_msg = tk.StringVar(value="Starting services...")
    tk.Label(root, textvariable=status_msg, font=("Segoe UI", 10), bg=BG, fg=DIM).pack(pady=(0, 14))

    # Service status cards
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

    # Buttons
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
                root.geometry("420x340")
            else:
                master_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
                root.geometry("420x660")
            return

        pw = sd.askstring("Master Mode", "Enter master password:", show="*", parent=root)
        if not pw or not verify_password(pw):
            if pw is not None:
                messagebox.showerror("Access Denied", "Wrong password.", parent=root)
            return

        master_unlocked[0] = True
        _build_master_panel(pw)
        master_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        root.geometry("420x660")

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
            ("backend_dir", "Backend Dir"),
            ("frontend_dir", "Frontend Dir"),
            ("license_api_url", "License API"),
            ("license_token", "License Token"),
        ]:
            row = tk.Frame(cfg_frame, bg="#1e1e2e")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=("Segoe UI", 9), bg="#1e1e2e", fg=DIM,
                     width=18, anchor="w").pack(side="left")
            var = tk.StringVar(value=config.get(key, ""))
            tk.Entry(row, textvariable=var, font=("Consolas", 9),
                     bg="#313244", fg=TEXT, insertbackground=TEXT, relief="flat",
                     show="*" if key == "license_token" else ""
                     ).pack(side="left", fill="x", expand=True, ipady=2)
            fields[key] = var

        def save_changes():
            new_cfg = {k: v.get().strip() for k, v in fields.items()}
            if not new_cfg["license_api_url"]:
                messagebox.showerror("Error", "License API URL is required.", parent=root)
                return
            if not new_cfg["license_token"]:
                messagebox.showerror("Error", "License token is required.", parent=root)
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

        # Log viewer
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
        license_ok, license_message, _ = validate_license(config)
        if not license_ok:
            log.warning(f"License validation failed before service start: {license_message}")
            def fail():
                status_msg.set("License validation failed")
                messagebox.showerror(
                    "License Validation Failed",
                    f"{license_message}\n\nServices were not started.",
                    parent=root,
                )
            root.after(0, fail)
            started[0] = False
            return
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

    # Auto-start services after license validation has passed.
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

    license_api_url = sd.askstring(
        "License Setup",
        "Validation API URL:",
        initialvalue=DEFAULT_CONFIG["license_api_url"],
        parent=root,
    )
    if not license_api_url:
        messagebox.showerror("Error", "License API URL is required.", parent=root)
        root.destroy()
        sys.exit(1)

    license_token = sd.askstring("License Setup", "License token:", show="*", parent=root)
    if not license_token:
        messagebox.showerror("Error", "License token is required.", parent=root)
        root.destroy()
        sys.exit(1)

    config = DEFAULT_CONFIG.copy()
    config["license_api_url"] = license_api_url.strip()
    config["license_token"] = license_token.strip()

    set_master_password(password)
    save_config(config, password)
    messagebox.showinfo("Done", "Setup complete! The app will now launch.\n\n"
        "Tip: Press Ctrl+Shift+M anytime to access master panel.", parent=root)
    root.destroy()
    return config

# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    config = _load_runtime_config()

    if config is None:
        config = first_time_setup()
        if config is None:
            sys.exit(0)
    else:
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        config = merged_config

    run_app(config)

if __name__ == "__main__":
    main()
