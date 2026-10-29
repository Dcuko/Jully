"""Builds Jully.exe (the launcher) with PyInstaller.

    .venv\\Scripts\\pip install -r requirements-dev.txt
    .venv\\Scripts\\python build_exe.py

The exe is written next to main.py; it has to stay in this folder.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import build_assets

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"


def main():
    BUILD.mkdir(exist_ok=True)
    build_assets.main()  # (re)render the icon files from assets/logo.svg
    icon = ROOT / "assets" / "icon.ico"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--onefile", "--noconsole", "--noconfirm", "--name", "Jully",
         "--icon", str(icon), "--add-data", f"{ROOT / 'assets' / 'icon_64.png'};assets", "--distpath", str(ROOT), "--workpath", str(BUILD / "work"),
         "--specpath", str(BUILD), "launcher.py"],
        cwd=ROOT, check=True)
    shutil.rmtree(BUILD, ignore_errors=True)
    print(f"\nBuilt {ROOT / 'Jully.exe'}")


if __name__ == "__main__":
    main()
