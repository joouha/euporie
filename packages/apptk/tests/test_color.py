"""Tests for color manipulation."""

import pytest
from apptk.color import Color, ColorPalette

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
        palette[name] = Color(color)
    return palette


def test_color_palette_add_color() -> None:
    """Test adding a color to the ColorPalette."""
    palette = ColorPalette()
    assert dict(palette) == {}
    palette["test_color"] = Color("#123456")
    assert "test_color" in palette
    assert isinstance(palette.test_color, Color)
    assert palette.test_color.hex == "#123456"


def test_color_palette_access_color(color_palette: ColorPalette) -> None:
    """Test accessing a color from the ColorPalette."""
    assert isinstance(color_palette.red, Color)
    assert color_palette.red.hex == test_colors["red"]


def test_color_palette_access_invalid_color(color_palette: ColorPalette) -> None:
    """Test accessing an invalid color from the ColorPalette."""
    with pytest.raises(AttributeError):
        color_palette.invalid_color  # noqa B018


def test_color_palette_color_adjustments(color_palette: ColorPalette) -> None:
    """Test color adjustments in the ColorPalette."""
    red = color_palette.red

    # Test lighter()
    lighter_red = red.lighter(0.1)
    assert isinstance(lighter_red, Color)
    assert lighter_red.hex != red.hex
    assert lighter_red.brightness > red.brightness

    # Test darker()
    darker_red = red.darker(0.1)
    assert isinstance(darker_red, Color)
    assert darker_red.hex != red.hex
    assert darker_red.brightness < red.brightness

    # Test more()
    more_red = red.more(0.1)
    assert isinstance(more_red, Color)
    assert more_red.hex != red.hex
    assert (
        (more_red.brightness < red.brightness)
        if red.is_light
        else (more_red.brightness > red.brightness)
    )

    # Test less()
    less_red = red.less(0.1)
    assert isinstance(less_red, Color)
    assert less_red.hex != red.hex
    assert (
        (less_red.brightness > red.brightness)
        if red.is_light
        else (less_red.brightness < red.brightness)
    )

    # Test towards()
    blue = color_palette.blue
    blended_color = red.towards(blue, 0.5)
    assert isinstance(blended_color, Color)
    assert blended_color.hex != red.hex
    assert blended_color.hex != blue.hex


def test_color_palette_color_adjustment_relative(color_palette: ColorPalette) -> None:
    """Test relative color adjustments in the ColorPalette."""
    red = color_palette.red

    # Test relative adjustments
    lighter_red = red.lighter(0.1, rel=True)
    darker_red = red.darker(0.1, rel=True)
    more_red = red.more(0.1, rel=True)
    less_red = red.less(0.1, rel=True)
    blended_color = red.towards(color_palette.blue, 0.5)

    assert lighter_red.hex != red.hex
    assert darker_red.hex != red.hex
    assert more_red.hex != red.hex
    assert less_red.hex != red.hex
    assert blended_color.hex != red.hex


def test_color_palette_color_adjustment_absolute(color_palette: ColorPalette) -> None:
    """Test absolute color adjustments in the ColorPalette."""
    red = color_palette.red

    # Test absolute adjustments
    lighter_red = red.lighter(0.1, rel=False)
    darker_red = red.darker(0.1, rel=False)
    more_red = red.more(0.1, rel=False)
    less_red = red.less(0.1, rel=False)
    blended_color = red.towards(color_palette.blue, 0.5)

    assert lighter_red.hex != red.hex
    assert darker_red.hex != red.hex
    assert more_red.hex != red.hex
    assert less_red.hex != red.hex
    assert blended_color.hex != red.hex
