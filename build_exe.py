"""Builds Jully.exe (the launcher) with PyInstaller.

    .venv\\Scripts\\pip install -r requirements-dev.txt
    .venv\\Scripts\\python build_exe.py

The exe is written next to main.py; it has to stay in this folder.
"""
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"


def make_icon(path):
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((16, 16, 240, 240), fill=(138, 92, 246, 255))
    d.rounded_rectangle((104, 64, 152, 160), radius=24, fill="white")
    d.ellipse((104, 136, 152, 192), fill="white")
    img.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def main():
    BUILD.mkdir(exist_ok=True)
    icon = BUILD / "jully.ico"
    make_icon(icon)
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--onefile", "--noconsole", "--noconfirm", "--name", "Jully",
         "--icon", str(icon), "--distpath", str(ROOT), "--workpath", str(BUILD / "work"),
         "--specpath", str(BUILD), "launcher.py"],
        cwd=ROOT, check=True)
    shutil.rmtree(BUILD, ignore_errors=True)
    print(f"\nBuilt {ROOT / 'Jully.exe'}")


if __name__ == "__main__":
    main()
