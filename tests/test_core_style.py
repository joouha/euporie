"""Tests for color manipulation."""

import pytest

from euporie.apptk.color import ColorPalette, ColorPaletteColor

# Define some test data
test_colors = {
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
}


@pytest.fixture
def color_palette() -> ColorPalette:
    """Fixture for creating a ColorPalette with test colors."""
    palette = ColorPalette()
    for name, color in test_colors.items():
        palette.add_color(name, color)
    return palette


def test_color_palette_add_color() -> None:
    """Test adding a color to the ColorPalette."""
    palette = ColorPalette()
    assert palette.colors == {}
    palette.add_color("test_color", "#123456")
    assert "test_color" in palette.colors
    assert isinstance(palette.test_color, ColorPaletteColor)
    assert palette.test_color.base_hex == "#123456"


def test_color_palette_access_color(color_palette: ColorPalette) -> None:
    """Test accessing a color from the ColorPalette."""
    assert isinstance(color_palette.red, ColorPaletteColor)
    assert color_palette.red.base_hex == test_colors["red"]


def test_color_palette_access_invalid_color(color_palette: ColorPalette) -> None:
    """Test accessing an invalid color from the ColorPalette."""
    with pytest.raises(KeyError):
        color_palette.invalid_color  # noqa B018


def test_color_palette_color_adjustments(color_palette: ColorPalette) -> None:
    """Test color adjustments in the ColorPalette."""
    red = color_palette.red

    # Test lighter()
    lighter_red = red.lighter(0.1)
    assert isinstance(lighter_red, ColorPaletteColor)
    assert lighter_red.base_hex != red.base_hex
    assert lighter_red.brightness > red.brightness

    # Test darker()
    darker_red = red.darker(0.1)
    assert isinstance(darker_red, ColorPaletteColor)
    assert darker_red.base_hex != red.base_hex
    assert darker_red.brightness < red.brightness

    # Test more()
    more_red = red.more(0.1)
    assert isinstance(more_red, ColorPaletteColor)
    assert more_red.base_hex != red.base_hex
    assert (
        (more_red.brightness < red.brightness)
        if red.is_light
        else (more_red.brightness > red.brightness)
    )

    # Test less()
    less_red = red.less(0.1)
    assert isinstance(less_red, ColorPaletteColor)
    assert less_red.base_hex != red.base_hex
    assert (
        (less_red.brightness > red.brightness)
        if red.is_light
        else (less_red.brightness < red.brightness)
    )

    # Test towards()
    blue = color_palette.blue
    blended_color = red.towards(blue, 0.5)
    assert isinstance(blended_color, ColorPaletteColor)
    assert blended_color.base_hex != red.base_hex
    assert blended_color.base_hex != blue.base_hex


def test_color_palette_color_adjustment_relative(color_palette: ColorPalette) -> None:
    """Test relative color adjustments in the ColorPalette."""
    red = color_palette.red

    # Test relative adjustments
    lighter_red = red.lighter(0.1, rel=True)
    darker_red = red.darker(0.1, rel=True)
    more_red = red.more(0.1, rel=True)
    less_red = red.less(0.1, rel=True)
    blended_color = red.towards(color_palette.blue, 0.5)

    assert lighter_red.base_hex != red.base_hex
    assert darker_red.base_hex != red.base_hex
    assert more_red.base_hex != red.base_hex
    assert less_red.base_hex != red.base_hex
    assert blended_color.base_hex != red.base_hex


def test_color_palette_color_adjustment_absolute(color_palette: ColorPalette) -> None:
    """Test absolute color adjustments in the ColorPalette."""
    red = color_palette.red

    # Test absolute adjustments
    lighter_red = red.lighter(0.1, rel=False)
    darker_red = red.darker(0.1, rel=False)
    more_red = red.more(0.1, rel=False)
    less_red = red.less(0.1, rel=False)
    blended_color = red.towards(color_palette.blue, 0.5)

    assert lighter_red.base_hex != red.base_hex
    assert darker_red.base_hex != red.base_hex
    assert more_red.base_hex != red.base_hex
    assert less_red.base_hex != red.base_hex
    assert blended_color.base_hex != red.base_hex
