"""
Build script – creates a standalone Aukulr Manager Lite .exe
Run:  python build_exe_lite.py
"""
import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"])

subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "AukulrManagerLite",
    "--add-data", "ppe_manager_lite.py;.",
    "--hidden-import", "cryptography",
    "--hidden-import", "requests",
    "--hidden-import", "psutil",
    "ppe_manager_lite.py"
], check=True)

print("\n✅  Build complete!")
print("   → dist/AukulrManagerLite.exe")