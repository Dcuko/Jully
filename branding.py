"""The Jully logo as images, for the window icon, the tray and the header.

The files in assets/ are generated from assets/logo.svg by build_assets.py.
"""
from functools import lru_cache
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent / "assets"


@lru_cache(maxsize=None)
def _load(name):
    return Image.open(ASSETS / name).convert("RGBA")


def icon_image(size=64):
    """The app icon: the logo on a dark rounded tile."""
    return _load("icon.png").resize((size, size), Image.LANCZOS)


def mark_image(size=24):
    """The bare logo on a transparent background, to sit on the app's own colors."""
    return _load("logo.png").resize((size, size), Image.LANCZOS)
