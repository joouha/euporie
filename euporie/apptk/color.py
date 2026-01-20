"""Style related functions."""

from __future__ import annotations

import logging
from colorsys import hls_to_rgb, rgb_to_hls
from functools import partial
from typing import TYPE_CHECKING

from euporie.apptk.application.current import get_app
from euporie.apptk.utils import to_str

from euporie.apptk.cache import SimpleCache
from euporie.apptk.output.vt100 import TERMINAL_COLORS_TO_RGB

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable
    from typing import Any


log = logging.getLogger(__name__)

__all__ = ["Color", "ColorPalette"]

_COLOR_CONV_CACHE: SimpleCache[tuple[Color, float, float, float, bool], Color] = (
    SimpleCache()
)


class Color(str):
    """A string representation of a color with adjustment methods."""

    def __new__(cls, value: str, name: str = "") -> Color:
        """Create a new color from a hex code."""
        # Perform validation
        parsed = value.upper()
        if parsed[0] != "#":
            parsed = f"#{parsed}"
        if any(c not in "0123456789ABCDEF" for c in parsed[1:]):
            raise ValueError(f"'{value}' not a color hex code")
        if len(parsed[1:]) == 3:
            parsed = (
                f"#{parsed[1]}{parsed[1]}{parsed[2]}{parsed[2]}{parsed[3]}{parsed[3]}"
            )
        # Create and return the instance
        instance = super().__new__(cls, name or parsed)
        instance.hex = parsed
        return instance

    def __init__(self, value: str, name: str = "") -> None:
        """Compute color properties."""
        self.red = int(self.hex[1:3], 16) / 255
        self.green = int(self.hex[3:5], 16) / 255
        self.blue = int(self.hex[5:7], 16) / 255
        self.hue, self.brightness, self.saturation = rgb_to_hls(
            self.red, self.green, self.blue
        )
        self.is_light = self.brightness > 0.5

    @classmethod
    def from_rgb(
        cls, r: int | float, g: int | float, b: int | float, name: str = ""
    ) -> Color:
        """Create a new color from RGB values."""
        if isinstance(r, float):
            r = int(r * 255)
        if isinstance(g, float):
            g = int(g * 255)
        if isinstance(b, float):
            b = int(b * 255)
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return cls(f"#{r:02x}{g:02x}{b:02x}", name=name)

    @classmethod
    def from_hsl(cls, h: float, l: float, s: float, name: str = "") -> Color:  # noqa: E741
        """Create a new color from float HLS values."""
        return cls.from_rgb(*hls_to_rgb(h, l, s), name=name)

    def _adjust_abs(
        self, hue: float = 0.0, brightness: float = 0.0, saturation: float = 0.0
    ) -> Color:
        hue = (self.hue + hue) % 1
        brightness = max(min(1, self.brightness + brightness), 0)
        saturation = max(min(1, self.saturation + saturation), 0)

        r, g, b = hls_to_rgb(hue, brightness, saturation)
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return Color(new_color)

    def _adjust_rel(
        self, hue: float = 0.0, brightness: float = 0.0, saturation: float = 0.0
    ) -> Color:
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
        return Color(new_color)

    def _adjust(
        self,
        hue: float = 0.0,
        brightness: float = 0.0,
        saturation: float = 0.0,
        rel: bool = True,
    ) -> Color:
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
    ) -> Color:
        """Adjust the hue, saturation, or brightness of the color.

        Args:
            hue: The hue adjustment.
            brightness: The brightness adjustment.
            saturation: The saturation adjustment.
            rel: If True, perform a relative adjustment.

        Returns:
            The adjusted color.
        """
        key = (self, hue, brightness, saturation, rel)
        return _COLOR_CONV_CACHE.get(
            key, partial(self._adjust, hue, brightness, saturation, rel)
        )

    def lighter(self, amount: float, rel: bool = True) -> Color:
        """Make the color lighter.

        Args:
            amount: The amount to lighten the color by.
            rel: If True, perform a relative adjustment.

        Returns:
            The lighter color.
        """
        return self.adjust(brightness=amount, rel=rel)

    def darker(self, amount: float, rel: bool = True) -> Color:
        """Make the color darker.

        Args:
            amount: The amount to darken the color by.
            rel: If True, perform a relative adjustment.

        Returns:
            The darker color.
        """
        return self.adjust(brightness=-amount, rel=rel)

    def more(self, amount: float, rel: bool = True) -> Color:
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

    def less(self, amount: float, rel: bool = True) -> Color:
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

    def towards(self, other: Color, amount: float) -> Color:
        """Interpolate between two colors."""
        amount = min(max(0, amount), 1)
        r = (other.red - self.red) * amount + self.red
        g = (other.green - self.green) * amount + self.green
        b = (other.blue - self.blue) * amount + self.blue
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return Color(new_color)

    def __hash__(self) -> int:
        """Generate unique hash of color based on hex value."""
        return super().__hash__() + hash(self.hex)


class ColorPalette(dict[str, Color]):
    """Define a collection of colors."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Ensure all values are :py:class:`Color`s."""
        super().__init__(*args, **kwargs)
        for k, v in self.items():
            if not isinstance(v, Color):
                self[k] = Color(v)

    def __setitem__(self, key: str, value: str | Color) -> None:
        """Set an item, automatically casting to Color."""
        if not isinstance(value, Color):
            value = Color(value)
        super().__setitem__(key, value)

    def add(self, name: str, hex_code: str, override: str = "") -> ColorPalette:
        """Add a color to the palette."""
        self[name] = Color(hex_code, name=override)
        return self

    def __getattr__(self, name: str) -> Any:
        """Enable access of palette colors via dotted attributes.

        Args:
            name: The name of the attribute to access.

        Returns:
            The color-palette color.

        Raises:
            AttributeError: If the color name is not found.
        """
        try:
            return self[name]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    def __hash__(self) -> int:
        """Return a content-based hash."""
        return hash(tuple(self.items()))


_STYLE_COLOR_CACHE: SimpleCache[
    tuple[str, tuple[int, int, int], tuple[int, int, int], Hashable, Hashable],
    tuple[Color, Color],
] = SimpleCache(maxsize=1024)


def style_fg_bg(style: str | Callable[[], str]) -> tuple[Color, Color]:
    """Get foreground and background colors for a given style string."""
    app = get_app()

    key = (
        style_str := to_str(style),
        fg_default := TERMINAL_COLORS_TO_RGB["fg"],
        bg_default := TERMINAL_COLORS_TO_RGB["bg"],
        app.renderer.style.invalidation_hash(),
        app.style_transformation.invalidation_hash(),
    )

    def _get_style_colors() -> tuple[str, str]:
        attrs_for_style = app.renderer._attrs_for_style
        attrs = attrs_for_style[style_str] if attrs_for_style else None
        fg = (
            Color(attrs.color) if attrs and attrs.color else Color.from_rgb(*fg_default)
        )
        bg = (
            Color(attrs.bgcolor)
            if attrs and attrs.bgcolor
            else Color.from_rgb(*bg_default)
        )
        return fg, bg

    return _STYLE_COLOR_CACHE.get(key, _get_style_colors)
