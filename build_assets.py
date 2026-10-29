"""Renders assets/logo.svg into the PNG/ICO files the app uses.

    .venv\Scripts\python build_assets.py

Run it again whenever the logo changes. It understands the path commands M L H V C S Q Z (absolute and relative)
and <path> elements filled with one color; arcs and holes are not supported.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SVG = ASSETS / "logo.svg"

TILE = "#17130f"  # background of the app icon (same as theme.BG)
SS = 4  # supersampling, for smooth edges


def _numbers(text):
    return [float(n) for n in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", text)]


def _bezier(p0, p1, p2, p3, steps=24):
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        out.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    return out


def parse_path(d):
    """Return a list of polygons (lists of (x, y)) from an SVG path."""
    if re.search(r"[Aa]", d):
        raise ValueError("unsupported path command: A (arcs)")
    polygons, poly = [], []
    cur = start = (0.0, 0.0)
    last_ctrl = None
    for cmd, args in re.findall(r"([MmLlHhVvCcSsQqZz])([^MmLlHhVvCcSsQqZz]*)", d):
        nums = _numbers(args)
        rel = cmd.islower()
        c = cmd.upper()
        if c == "Z":
            if poly:
                polygons.append(poly)
            poly, cur, last_ctrl = [], start, None
            continue
        step = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4}.get(c)
        if step is None or not nums:
            raise ValueError(f"unsupported path command: {cmd}")
        for i in range(0, len(nums), step):
            n = nums[i:i + step]
            ox, oy = cur if rel else (0.0, 0.0)
            if c == "M":
                if poly:
                    polygons.append(poly)
                cur = start = (n[0] + ox, n[1] + oy)
                poly = [cur]
                c = "L"  # extra pairs after an M are implicit lines
                last_ctrl = None
            elif c == "L":
                cur = (n[0] + ox, n[1] + oy)
                poly.append(cur)
                last_ctrl = None
            elif c == "H":
                cur = (n[0] + (cur[0] if rel else 0), cur[1])
                poly.append(cur)
                last_ctrl = None
            elif c == "V":
                cur = (cur[0], n[0] + (cur[1] if rel else 0))
                poly.append(cur)
                last_ctrl = None
            elif c in ("C", "S"):
                if c == "C":
                    p1 = (n[0] + ox, n[1] + oy)
                    p2 = (n[2] + ox, n[3] + oy)
                    end = (n[4] + ox, n[5] + oy)
                else:
                    p1 = (2 * cur[0] - last_ctrl[0], 2 * cur[1] - last_ctrl[1]) if last_ctrl else cur
                    p2 = (n[0] + ox, n[1] + oy)
                    end = (n[2] + ox, n[3] + oy)
                poly += _bezier(cur, p1, p2, end)
                cur, last_ctrl = end, p2
            elif c == "Q":
                q = (n[0] + ox, n[1] + oy)
                end = (n[2] + ox, n[3] + oy)
                p1 = (cur[0] + 2 / 3 * (q[0] - cur[0]), cur[1] + 2 / 3 * (q[1] - cur[1]))
                p2 = (end[0] + 2 / 3 * (q[0] - end[0]), end[1] + 2 / 3 * (q[1] - end[1]))
                poly += _bezier(cur, p1, p2, end)
                cur, last_ctrl = end, q
    if poly:
        polygons.append(poly)
    return polygons


def load_logo():
    """Return (polygons, fill color, viewBox) of the logo."""
    root = ET.parse(SVG).getroot()
    view = [float(v) for v in root.get("viewBox").split()]
    css = " ".join(el.text or "" for el in root.iter() if el.tag.endswith("style"))
    color = (re.search(r"fill:\s*(#[0-9a-fA-F]{6})", css) or re.search(r'fill="(#[0-9a-fA-F]{6})"', ET.tostring(root, "unicode")))
    polygons = []
    for el in root.iter():
        if el.tag.endswith("path"):
            polygons += parse_path(el.get("d"))
    return polygons, color.group(1) if color else "#e66d28", view


def bounds(polygons):
    xs = [x for p in polygons for x, _ in p]
    ys = [y for p in polygons for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


def render(size, polygons, color, fit_box, tile=False, fill_ratio=0.62):
    """Draw the logo centered in a size x size image. `fit_box` is the logo bounding box (keeps it centered)."""
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tile:
        d.rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.22), fill=TILE)
    x0, y0, x1, y1 = fit_box
    scale = big * (fill_ratio if tile else 0.94) / max(x1 - x0, y1 - y0)
    ox = (big - (x1 - x0) * scale) / 2 - x0 * scale
    oy = (big - (y1 - y0) * scale) / 2 - y0 * scale
    for poly in polygons:
        d.polygon([(x * scale + ox, y * scale + oy) for x, y in poly], fill=color)
    return img.resize((size, size), Image.LANCZOS)


def main():
    polygons, color, _ = load_logo()
    box = bounds(polygons)
    render(512, polygons, color, box).save(ASSETS / "logo.png")
    render(256, polygons, color, box, tile=True).save(ASSETS / "icon.png")
    render(64, polygons, color, box, tile=True).save(ASSETS / "icon_64.png")  # for the installer window
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [render(s, polygons, color, box, tile=True) for s in sizes]
    # BMP frames: Tk (title bar and taskbar of the window) cannot read the PNG frames Pillow writes by default
    frames[-1].save(ASSETS / "icon.ico", sizes=[(s, s) for s in sizes], append_images=frames[:-1],
                    bitmap_format="bmp")
    print(f"logo color {color}; wrote logo.png, icon.png, icon_64.png and icon.ico to {ASSETS}")


if __name__ == "__main__":
    main()
