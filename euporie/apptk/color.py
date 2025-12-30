"""Style related functions."""

from __future__ import annotations

import logging
from colorsys import hls_to_rgb, rgb_to_hls
from functools import partial
from typing import TYPE_CHECKING

from euporie.apptk.cache import SimpleCache

if TYPE_CHECKING:
    from typing import Any


log = logging.getLogger(__name__)

__all__ = ["DEFAULT_COLORS", "ColorPalette", "ColorPaletteColor"]

DEFAULT_COLORS = {
    "bg": "#232627",
    "fg": "#fcfcfc",
    "ansiblack": "#000000",
    "ansired": "#cc0403",
    "ansigreen": "#19cb00",
    "ansiyellow": "#cecb00",
    "ansiblue": "#0d73cc",
    "ansipurple": "#9841bb",
    "ansimagenta": "#cb1ed1",
    "ansicyan": "#0dcdcd",
    "ansiwhite": "#dddddd",
    "ansibrightblack": "#767676",
    "ansigray": "#767676",
    "ansibrightred": "#f2201f",
    "ansibrightgreen": "#23fd00",
    "ansibrightyellow": "#fffd00",
    "ansibrightblue": "#1a8fff",
    "ansibrightpurple": "#fd28ff",
    "ansibrightmagenta": "#fd28ff",
    "ansibrightcyan": "#14ffff",
    "ansibrightwhite": "#ffffff",
}


class ColorPaletteColor:
    """A representation of a color with adjustment methods."""

    _cache: SimpleCache[tuple[str, float, float, float, bool], ColorPaletteColor] = (
        SimpleCache()
    )

    def __init__(self, base: str, _base_override: str = "") -> None:
        """Create a new color.

        Args:
            base: The base color as a hexadecimal string.
            _base_override: An optional base color override.
        """
        self.base_hex = DEFAULT_COLORS.get(base, base)
        self.base = _base_override or base

        color = self.base_hex.lstrip("#")
        self.red, self.green, self.blue = (
            int(color[0:2], 16) / 255,
            int(color[2:4], 16) / 255,
            int(color[4:6], 16) / 255,
        )

        self.hue, self.brightness, self.saturation = rgb_to_hls(
            self.red, self.green, self.blue
        )

        self.is_light = self.brightness > 0.5

    def _adjust_abs(
        self, hue: float = 0.0, brightness: float = 0.0, saturation: float = 0.0
    ) -> ColorPaletteColor:
        hue = (self.hue + hue) % 1
        brightness = max(min(1, self.brightness + brightness), 0)
        saturation = max(min(1, self.saturation + saturation), 0)

        r, g, b = hls_to_rgb(hue, brightness, saturation)
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return ColorPaletteColor(new_color)

    def _adjust_rel(
        self, hue: float = 0.0, brightness: float = 0.0, saturation: float = 0.0
    ) -> ColorPaletteColor:
        hue = min(max(0, hue), 1)
        brightness = min(max(-1, brightness), 1)
        saturation = min(max(-1, saturation), 1)

        new_hue = self.hue + (self.hue * (hue < 0) + (1 - self.hue) * (hue > 0)) * hue

        new_brightness = (
            self.brightness
            + (
                self.brightness * (brightness < 0)
                + (1 - self.brightness) * (brightness > 0)
            )
            * brightness
        )

        new_saturation = (
            self.saturation
            + (
                self.saturation * (saturation < 0)
                + (1 - self.saturation) * (saturation > 0)
            )
            * saturation
        )

        r, g, b = hls_to_rgb(new_hue, new_brightness, new_saturation)
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return ColorPaletteColor(new_color)

    def _adjust(
        self,
        hue: float = 0.0,
        brightness: float = 0.0,
        saturation: float = 0.0,
        rel: bool = True,
    ) -> ColorPaletteColor:
        """Perform a relative of absolute color adjustment.

        Args:
            hue: The hue adjustment.
            brightness: The brightness adjustment.
            saturation: The saturation adjustment.
            rel: If True, perform a relative adjustment.

        Returns:
            The adjusted color.
        """
        if rel:
            return self._adjust_rel(hue, brightness, saturation)
        else:
            return self._adjust_abs(hue, brightness, saturation)

    def adjust(
        self,
        hue: float = 0.0,
        brightness: float = 0.0,
        saturation: float = 0.0,
        rel: bool = True,
    ) -> ColorPaletteColor:
        """Adjust the hue, saturation, or brightness of the color.

        Args:
            hue: The hue adjustment.
            brightness: The brightness adjustment.
            saturation: The saturation adjustment.
            rel: If True, perform a relative adjustment.

        Returns:
            The adjusted color.
        """
        key = (self.base_hex, hue, brightness, saturation, rel)
        return self._cache.get(
            key, partial(self._adjust, hue, brightness, saturation, rel)
        )

    def lighter(self, amount: float, rel: bool = True) -> ColorPaletteColor:
        """Make the color lighter.

        Args:
            amount: The amount to lighten the color by.
            rel: If True, perform a relative adjustment.

        Returns:
            The lighter color.
        """
        return self.adjust(brightness=amount, rel=rel)

    def darker(self, amount: float, rel: bool = True) -> ColorPaletteColor:
        """Make the color darker.

        Args:
            amount: The amount to darken the color by.
            rel: If True, perform a relative adjustment.

        Returns:
            The darker color.
        """
        return self.adjust(brightness=-amount, rel=rel)

    def more(self, amount: float, rel: bool = True) -> ColorPaletteColor:
        """Make bright colors darker and dark colors brighter.

        Args:
            amount: The amount to adjust the color by.
            rel: If True, perform a relative adjustment.

        Returns:
            The adjusted color.
        """
        if self.is_light:
            amount *= -1
        return self.adjust(brightness=amount, rel=rel)

    def less(self, amount: float, rel: bool = True) -> ColorPaletteColor:
        """Make bright colors brighter and dark colors darker.

        Args:
            amount: The amount to adjust the color by.
            rel: If True, perform a relative adjustment.

        Returns:
            The adjusted color.
        """
        if self.is_light:
            amount *= -1
        return self.adjust(brightness=-amount, rel=rel)

    def towards(self, other: ColorPaletteColor, amount: float) -> ColorPaletteColor:
        """Interpolate between two colors."""
        amount = min(max(0, amount), 1)
        r = (other.red - self.red) * amount + self.red
        g = (other.green - self.green) * amount + self.green
        b = (other.blue - self.blue) * amount + self.blue
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return ColorPaletteColor(new_color)

    def __repr__(self) -> str:
        """Return a representation of the color."""
        return f"Color({self.base})"

    def __str__(self) -> str:
        """Return a string representation of the color."""
        return self.base_hex


class ColorPalette:
    """Define a collection of colors."""

    def __init__(self) -> None:
        """Create a new color-palette."""
        self.colors: dict[str, ColorPaletteColor] = {}

    def add_color(self, name: str, base: str, _base_override: str = "") -> ColorPalette:
        """Add a color to the palette."""
        self.colors[name] = ColorPaletteColor(base, _base_override)
        return self

    def __getattr__(self, name: str) -> Any:
        """Enable access of palette colors via dotted attributes.

        Args:
            name: The name of the attribute to access.

        Returns:
            The color-palette color.

        """
        return self.colors[name]
