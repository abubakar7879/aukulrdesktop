"""
Build script – creates a standalone Aukulr Manager .exe
Run:  python build_exe.py
"""
import subprocess
import sys

# Install PyInstaller if needed
subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"])

# Build
subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",                          # no console window
    "--name", "AukulrManager",
    "--hidden-import", "cryptography",
    "--hidden-import", "requests",
    "--hidden-import", "psutil",
    "ppe_manager.py"
], check=True)

print("\n✅  Build complete!")
print("   → dist/AukulrManager.exe")