import pytest
from PIL import Image

import branding
import build_assets


def test_parse_path_handles_absolute_relative_and_shorthand_commands():
    square = build_assets.parse_path("M0 0 L10 0 L10 10 L0 10 Z")
    assert square == [[(0, 0), (10, 0), (10, 10), (0, 10)]]
    relative = build_assets.parse_path("m0 0 h10 v10 h-10 z")
    assert relative == [[(0, 0), (10, 0), (10, 10), (0, 10)]]
    curve = build_assets.parse_path("M0 0 C0 10 10 10 10 0 S20 -10 20 0 Q25 5 30 0 Z")[0]
    assert curve[0] == (0, 0) and curve[-1] == pytest.approx((30, 0))


def test_parse_path_keeps_separate_subpaths_apart():
    assert len(build_assets.parse_path("M0 0 L1 0 L1 1 Z M5 5 L6 5 L6 6 Z")) == 2


def test_parse_path_refuses_arcs_instead_of_drawing_garbage():
    with pytest.raises(ValueError):
        build_assets.parse_path("M0 0 A5 5 0 0 1 10 0 Z")


def test_the_logo_svg_loads_with_its_color_and_shapes():
    polygons, color, view = build_assets.load_logo()
    assert color == "#e66d28"
    assert len(polygons) == 3  # the body and the two eyes
    assert view == [0, 0, 800, 800]


def test_generated_assets_exist_with_the_expected_sizes():
    assets = branding.ASSETS
    assert Image.open(assets / "logo.png").size == (512, 512)
    assert Image.open(assets / "icon.png").size == (256, 256)
    assert Image.open(assets / "icon_64.png").size == (64, 64)
    assert {(16, 16), (32, 32), (256, 256)} <= set(Image.open(assets / "icon.ico").info["sizes"])


def test_the_mark_is_transparent_and_orange_and_the_icon_is_a_dark_tile():
    mark = branding.mark_image(64)
    assert mark.mode == "RGBA" and mark.getpixel((0, 0))[3] == 0  # transparent corner
    assert mark.getpixel((10, 30)) == (0xE6, 0x6D, 0x28, 255)  # inside the body: exactly the logo orange

    icon = branding.icon_image(64)
    assert icon.size == (64, 64)
    assert icon.getpixel((32, 8))[3] == 255  # inside the tile
