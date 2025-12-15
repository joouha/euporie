"""Style related functions."""

from __future__ import annotations

import logging
from colorsys import hls_to_rgb, rgb_to_hls
from functools import cache, partial
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.styles.defaults import default_ui_style
from prompt_toolkit.styles.style import Style
from pygments.styles import get_style_by_name as pyg_get_style_by_name

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from pygments.style import Style as PygmentsStyle


log = logging.getLogger(__name__)


KERNEL_STATUS_REPR = {
    "stopped": "⨂",
    "starting": "◍",
    "idle": "○",
    "busy": "●",
    "error": "☹",
}


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


MIME_STYLE = [
    ("mime-stream-stderr", "fg:ansired"),
]

HTML_STYLE = [
    ("html h1", "bold underline"),
    ("html h1 border", "fg:ansiyellow nounderline"),
    ("html h2", "bold"),
    ("html h2 border", "fg:grey nobold"),
    ("html h3", "bold"),
    ("html h4", "bold italic"),
    ("html h5", "underline"),
    ("html h6", "italic"),
    # ("html code", "bg:#333"),
    # ("html kbd", "fg:#fff bg:#333"),
    # ("html samp", "fg:#fff bg:#333"),
    # ("html b", "bold"),
    # ("html strong", "bold"),
    # ("html i", "italic"),
    # ("html em", "italic"),
    # ("html cite", "italic"),
    # ("html dfn", "italic"),
    # ("html var", "italic"),
    # ("html u", "underline"),
    # ("html ins", "underline"),
    # ("html s", "strike"),
    # ("html del", "strike"),
    # ("html mark", "fg:black bg:ansiyellow"),
    # ("html hr", "fg:ansired"),
    ("html ul bullet", "fg:ansiyellow"),
    ("html ol bullet", "fg:ansicyan"),
    ("html blockquote", "fg:ansipurple"),
    ("html blockquote margin", "fg:grey"),
    ("html th", "bold"),
    ("html img", "bg:cyan fg:black"),
    ("html img border", "fg:cyan bg:default"),
    ("html caption", "italic"),
]


IPYWIDGET_STYLE = [
    ("ipywidget", "bg:default"),
    ("ipywidget focused", ""),
    ("ipywidget button face", "fg:black bg:#d4d0c8"),
    ("ipywidget button face selection", "bg:#e9e7e3"),
    ("ipywidget button face primary", "bg:ansiblue"),
    ("ipywidget button face success", "bg:ansigreen"),
    ("ipywidget button face info", "bg:ansicyan"),
    ("ipywidget button face warning", "bg:ansiyellow"),
    ("ipywidget button face danger", "bg:ansired"),
    ("ipywidget button border right", "fg:#606060"),
    ("ipywidget button border bottom", "fg:#606060"),
    ("ipywidget button border left", "fg:#ffffff"),
    ("ipywidget button border top", "fg:#ffffff"),
    ("ipywidget button face disabled", "fg:#888888"),
    ("ipywidget selection border right", "fg:#ffffff"),
    ("ipywidget selection border bottom", "fg:#ffffff"),
    ("ipywidget selection border left", "fg:#606060"),
    ("ipywidget selection border top", "fg:#606060"),
    # ("ipywidget primary border left", "fg:ansibrightblue"),
    # ("ipywidget primary border top", "fg:ansibrightblue"),
    # ("ipywidget success border left", "fg:ansibrightgreen"),
    # ("ipywidget success border top", "fg:ansibrightgreen"),
    # ("ipywidget info border left", "fg:ansibrightcyan"),
    # ("ipywidget info border top", "fg:ansibrightcyan"),
    # ("ipywidget warning border left", "fg:ansibrightyellow"),
    # ("ipywidget warning border top", "fg:ansibrightyellow"),
    # ("ipywidget danger border left", "fg:ansibrightred"),
    # ("ipywidget danger border top", "fg:ansibrightred"),
    # ("ipywidget border left selection", "fg:#606060"),
    # ("ipywidget border top selection", "fg:#606060"),
    # ("ipywidget primary border right selection", "fg:ansibrightblue"),
    # ("ipywidget primary border bottom selection", "fg:ansibrightblue"),
    # ("ipywidget primary border right selection", "fg:ansibrightblue"),
    # ("ipywidget primary border bottom selection", "fg:ansibrightblue"),
    # ("ipywidget success border right selection", "fg:ansibrightgreen"),
    # ("ipywidget success border bottom selection", "fg:ansibrightgreen"),
    # ("ipywidget success border right selection", "fg:ansibrightgreen"),
    # ("ipywidget success border bottom selection", "fg:ansibrightgreen"),
    # ("ipywidget info border right selection", "fg:ansibrightcyan"),
    # ("ipywidget info border bottom selection", "fg:ansibrightcyan"),
    # ("ipywidget danger border right selection", "fg:ansibrightred"),
    # ("ipywidget danger border bottom selection", "fg:ansibrightred"),
    ("ipywidget text text-area", "fg:black bg:white"),
    ("ipywidget text text-area disabled", "fg:#888888"),
    ("ipywidget text text-area focused", "fg:black bg:white"),
    ("ipywidget text placeholder", "fg:#AAAAAA bg:white"),
    ("ipywidget text border right", "fg:#E9E7E3"),
    ("ipywidget text border top", "fg:#606060"),
    ("ipywidget text border bottom", "fg:#E9E7E3"),
    ("ipywidget text border left", "fg:#606060"),
    ("ipywidget text border top invalid", "fg:ansidarkred"),
    ("ipywidget text border right invalid", "fg:ansired"),
    ("ipywidget text border bottom invalid", "fg:ansired"),
    ("ipywidget text border left invalid", "fg:ansidarkred"),
    ("ipywidget slider track selection", "fg:ansiblue"),
    ("ipywidget slider handle focused", "fg:white"),
    ("ipywidget slider handle selection", ""),
    ("ipywidget slider handle selection focused", "fg:ansiblue"),
    ("ipywidget progress", "fg:ansidarkblue bg:#d4d0c8"),
    ("ipywidget progress primary", "fg:ansiblue"),
    ("ipywidget progress success", "fg:ansigreen"),
    ("ipywidget progress info", "fg:ansicyan"),
    ("ipywidget progress warning", "fg:ansiyellow"),
    ("ipywidget progress danger", "fg:ansired"),
    ("ipywidget progress border", "bg:default"),
    ("ipywidget progress border top", "fg:#E9E7E3"),
    ("ipywidget progress border right", "fg:#606060"),
    ("ipywidget progress border bottom", "fg:#606060"),
    ("ipywidget progress border left", "fg:#E9E7E3"),
    ("ipywidget dropdown dropdown.menu", "fg:#000000 bg:#ffffff"),
    ("ipywidget dropdown dropdown.menu hovered", "fg:#ffffff bg:ansiblue"),
    ("ipywidget checkbox selection", "fg:default"),
    ("ipywidget checkbox prefix selection", "fg:ansiblue"),
    ("ipywidget checkbox disabled", "fg:#888888"),
    ("ipywidget checkbox prefix selection disabled", "fg:#888888"),
    ("ipywidget valid prefix", "fg:ansired"),
    ("ipywidget valid prefix selection", "fg:ansigreen"),
    ("ipywidget radio-buttons selection", "fg:default"),
    ("ipywidget radio-buttons selection disabled", "fg:#888888"),
    ("ipywidget radio-buttons prefix selection", "fg:ansiblue"),
    ("ipywidget select face", "fg:black bg:white"),
    ("ipywidget select face selection", "fg:white bg:ansiblue"),
    ("ipywidget select face hovered", "fg:black bg:#f0f0f0"),
    ("ipywidget select face hovered selection", "fg:white bg:ansiblue"),
    ("ipywidget select border top", "fg:#606060"),
    ("ipywidget select border right", "fg:#E9E7E3"),
    ("ipywidget select border bottom", "fg:#E9E7E3"),
    ("ipywidget select border left", "fg:#606060"),
    ("ipywidget select disabled", "fg:#888888"),
    ("ipywidget select selection disabled", "fg:#888888"),
    ("ipywidget inset border right", "fg:#E9E7E3"),
    ("ipywidget inset border top", "fg:#606060"),
    ("ipywidget inset border bottom", "fg:#E9E7E3"),
    ("ipywidget inset border left", "fg:#606060"),
    ("ipywidget swatch border right", "fg:#E9E7E3"),
    ("ipywidget swatch border top", "fg:#606060"),
    ("ipywidget swatch border bottom", "fg:#E9E7E3"),
    ("ipywidget swatch border left", "fg:#606060"),
    ("ipywidget tabbed-split tab-bar tab active border top default", "fg:ansiblue"),
    ("ipywidget tabbed-split tab-bar tab active border top primary", "fg:ansiblue"),
    ("ipywidget tabbed-split tab-bar tab active border top success", "fg:ansigreen"),
    ("ipywidget tabbed-split tab-bar tab active border top info", "fg:ansicyan"),
    ("ipywidget tabbed-split tab-bar tab active border top warning", "fg:ansiyellow"),
    ("ipywidget tabbed-split tab-bar tab active border top danger", "fg:ansired"),
    ("ipywidget accordion border primary", "fg:ansiblue"),
    ("ipywidget accordion border success", "fg:ansigreen"),
    ("ipywidget accordion border info", "fg:ansicyan"),
    ("ipywidget accordion border warning", "fg:ansiyellow"),
    ("ipywidget accordion border danger", "fg:ansired"),
    ("ipywidget accordion selection", "fg:ansiblue"),
]


LOG_STYLE = [
    ("log.level.nonset", "fg:ansigray"),
    ("log.level.debug", "fg:ansigreen"),
    ("log.level.info", "fg:ansiblue"),
    ("log.level.warning", "fg:ansiyellow"),
    ("log.level.error", "fg:ansired"),
    ("log.level.critical", "fg:ansiwhite bg:ansired bold"),
    # ("log.level.nonset", "fg:grey"),
    # ("log.level.debug", "fg:green"),
    # ("log.level.info", "fg:blue"),
    # ("log.level.warning", "fg:yellow"),
    # ("log.level.error", "fg:red"),
    # ("log.level.critical", "fg:red bold"),
    ("log.ref", "fg:grey"),
    ("log.date", "fg:#00875f"),
]


DIAGNOSTIC_STYLE = [
    ("diagnostic-0", "fg:ansigray"),
    ("diagnostic-1", "fg:ansigreen"),
    ("diagnostic-2", "fg:ansiblue"),
    ("diagnostic-3", "fg:ansiyellow"),
    ("diagnostic-4", "fg:ansired"),
    ("diagnostic-5", "fg:ansiwhite bg:ansired bold"),
]


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


def base_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate base application styles."""
    return {
        "default": f"fg:{cp.bg.base} bg:{cp.bg.base}",
        "nbsp": "nounderline fg:default",
        "logo": "fg:#dd0000",
        "pattern": f"fg:{cp.bg.more(0.05)}",
        "loading": "fg:#888888",
        "placeholder": f"fg:{cp.fg.more(0.6)}",
    }


def chrome_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate chrome and UI element styles."""
    return {
        "chrome": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "tab-padding": f"fg:{cp.bg.more(0.2)} bg:{cp.bg.base}",
    }


def statusbar_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate statusbar styles."""
    return {
        "status": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "status-field": f"bg:{cp.fg.more(0.1)} fg:{cp.bg.more(0.1)} reverse",
        "status-sep": f"bg:{cp.bg.more(0.05)} fg:{cp.bg.more(0.1)} reverse",
    }


def menu_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate menu and menu bar styles."""
    return {
        "menu": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "menu bar": f"bg:{cp.bg.less(0.15)}",
        "menu disabled": f"fg:{cp.fg.more(0.05).towards(cp.bg, 0.75)}",
        "menu shortcut": f"fg:{cp.fg.more(0.4)}",
        "menu shortcut disabled": f"fg:{cp.fg.more(0.4).towards(cp.bg, 0.5)}",
        "menu prefix": f"fg:{cp.fg.more(0.2)}",
        "menu prefix disabled": f"fg:{cp.fg.more(0.2).towards(cp.bg, 0.5)}",
        "menu selection": f"bg:{cp.hl.more(1)} fg:{cp.hl} reverse",
        "menu selection shortcut": f"bg:{cp.hl.more(1).more(0.05)} fg:{cp.hl} reverse",
        "menu selection prefix": f"bg:{cp.hl.more(1).more(0.05)} fg:{cp.hl} reverse",
        "menu border": f"fg:{cp.bg.more(0.15)} bg:{cp.bg.more(0.05)}",
        "menu border selection": f"fg:{cp.bg.more(0.15)} bg:{cp.hl} noreverse",
    }


def tab_bar_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate tab bar styles."""
    return {
        "app-tab-bar": f"bg:{cp.bg.less(0.15)}",
        "app-tab-bar border": f"fg:{cp.bg.more(0.1)}",
        "app-tab-bar tab inactive": f"fg:{cp.fg.more(0.5)}",
        "app-tab-bar tab inactive border": f"fg:{cp.bg.more(0.15)}",
        "app-tab-bar tab active": "bold fg:default bg:default",
        "app-tab-bar tab active close": "fg:darkred",
        "app-tab-bar tab active border top": f"fg:{cp.hl} bg:{cp.bg.less(0.15)}",
    }


def buffer_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate buffer and editor styles."""
    return {
        "line-number": f"bg:{cp.fg.more(0.5)} fg:{cp.bg.more(0.05)} reverse",
        "line-number.current": f"bg:orange fg:{cp.bg.more(0.1)} bold",
        "line-number edge": f"bg:{cp.bg.darker(0.1)}",
        "line-number.current edge": f"bg:{cp.bg.darker(0.1)}",
        "cursor-line": f"bg:{cp.bg.more(0.05)}",
        "cursor-line search": f"bg:{cp.bg.more(0.02)}",
        "cursor-line search.current": f"bg:{cp.bg.more(0.02)}",
        "cursor-line incsearch": "bg:ansibrightyellow",
        "cursor-line incsearch.current": "bg:ansibrightgreen",
        "matching-bracket.cursor": "fg:yellow bold",
        "matching-bracket.other": "fg:yellow bold",
        "trailing-whitespace": f"fg:{cp.fg.more(0.66)}",
        "tab": f"fg:{cp.fg.more(0.66)}",
        "search": f"bg:{cp.bg.more(0.05)}",
        "search.current": f"bg:{cp.bg.more(0.05)}",
        "incsearch": "bg:ansibrightyellow",
        "incsearch.current": "bg:ansibrightgreen",
    }


def cell_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate notebook cell styles."""
    return {
        "kernel-input": f"fg:default bg:{cp.bg.more(0.02)}",
        "cell border": f"fg:{cp.bg.more(0.25)}",
        "cell border cell.selection": f"fg:{cp.hl.more(0.2)}",
        "cell border edit": f"fg:{cp.hl.adjust(hue=-0.3333, rel=False)}",
        "cell input prompt": "fg:blue",
        "cell output prompt": "fg:red",
        "cell show outputs": f"bg:{cp.fg.more(0.5)} fg:{cp.bg.more(0.05)} reverse",
        "cell show inputs": f"bg:{cp.fg.more(0.5)} fg:{cp.bg.more(0.05)} reverse",
        "cell show inputs border": f"bg:{cp.bg.darker(0.1)} fg:{cp.bg.more(0.05)} reverse",
        "cell show outputs border": f"bg:{cp.bg.darker(0.1)} fg:{cp.bg.more(0.05)} reverse",
    }


def scrollbar_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate scrollbar styles."""
    return {
        "scrollbar": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.15)}",
        "scrollbar.background": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.15)}",
        "scrollbar.arrow": f"bg:{cp.bg.more(0.75)} fg:{cp.bg.more(0.20)} reverse",
        "scrollbar.start": "",
        "scrollbar.button": f"bg:{cp.bg.more(0.75)} fg:{cp.bg.more(0.75)} reverse",
        "scrollbar.end": f"bg:{cp.bg.more(0.15)} fg:{cp.bg.more(0.75)} reverse",
        "overflow": f"fg:{cp.fg.more(0.5)}",
    }


def dialog_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate dialog styles."""
    return {
        "dialog dialog-title": f"bg:white fg:{cp.hl.darker(0.25)} bold reverse",
        "dialog": f"fg:{cp.fg.base} bg:{cp.bg.darker(0.1)}",
        "dialog text-area": f"bg:{cp.bg.lighter(0.05)}",
        "dialog input text text-area": f"fg:default bg:{cp.bg.less(0.1)}",
        "dialog text-area last-line": "nounderline",
        "dialog border": f"fg:{cp.bg.darker(0.1).more(0.1)}",
        "dialog tabbed-split border bottom right": f"bg:{cp.bg.darker(0.1)}",
        "dialog tabbed-split border bottom left": f"bg:{cp.bg.darker(0.1)}",
        "hr": "fg:red",
    }


def toolbar_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate toolbar styles."""
    return {
        "toolbar": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "toolbar.title": f"fg:{cp.fg.more(0.1)} bg:{cp.bg.more(0.1)}",
        "search-toolbar": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "toolbar menu": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "toolbar menu completion": f"fg:{cp.fg.more(0.1)} bg:{cp.bg.more(0.1)}",
        "toolbar menu completion current": f"fg:{cp.hl} bg:{cp.fg} reverse",
        "toolbar menu overflow": f"fg:{cp.fg.more(0.5)}",
        "toolbar menu meta": f"bg:{cp.bg.more(0.25)} bold",
    }


def completion_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate completion menu styles."""
    completion_colors = {
        "keyword": "#d700af",
        "function": "#005faf",
        "class": "#008700",
        "statement": "#5f0000",
        "instance": "#d75f00",
        "module": "#d70000",
        "magic": "#9841bb",
        "path": "#aa8800",
        "dict-key": "#ddbb00",
    }

    styles = {}
    for name, color_hex in completion_colors.items():
        styles[f"menu completion-{name}"] = f"fg:{color_hex}"
        color = ColorPaletteColor(color_hex)
        styles[f"menu completion-{name} selection"] = (
            f"bg:{color.lighter(0.75)} fg:{cp.hl} reverse"
        )
    return styles


def shortcuts_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate shortcuts display styles."""
    return {
        "shortcuts.group": f"bg:{cp.bg.more(0.4)} bold underline",
        "shortcuts.row alt": f"bg:{cp.bg.more(0.1)}",
        "shortcuts.row key": "bold",
    }


def palette_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate command palette styles."""
    return {
        "palette.item": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "palette.item.alt": f"bg:{cp.bg.more(0.15)}",
        "palette.item.selected": f"bg:{cp.hl.more(1)} fg:{cp.hl} reverse",
    }


def pager_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate pager styles."""
    return {
        "pager": f"bg:{cp.bg.more(0.05)}",
        "pager.border": f"fg:{cp.bg.towards(cp.ansiblack, 0.15)} reverse",
    }


def markdown_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate markdown rendering styles."""
    return {
        "markdown code": f"bg:{cp.bg.more(0.15)}",
        "markdown code block": f"bg:{cp.bg.less(0.2)}",
        "markdown code block border": f"fg:{cp.bg.more(0.25)}",
        "markdown table border": f"fg:{cp.bg.more(0.75)}",
    }


def shadow_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate drop shadow styles."""
    return {
        "drop-shadow inner": f"fg:{cp.bg.towards(cp.ansiblack, 0.3)}",
        "drop-shadow outer": f"fg:{cp.bg.towards(cp.ansiblack, 0.2)} bg:{cp.bg.towards(cp.ansiblack, 0.05)}",
    }


def sidebar_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate sidebar styles."""
    return {
        "side_bar": f"bg:{cp.bg.less(0.15)}",
        "side_bar title": f"fg:{cp.hl}",
        "side_bar title text": f"fg:default bg:{cp.bg.less(0.15).more(0.01)}",
        "side_bar border outer": f"bg:{cp.bg}",
        "side_bar border": f"fg:{cp.bg.darker(0.15).less(0.3)}",
        "side_bar border handle": f"fg:{cp.bg.more(0.25)}",
        "side_bar buttons": f"bg:{cp.bg.less(0.15)}",
        "side_bar buttons focused": f"fg:{cp.hl}",
        "side_bar buttons separator": f"bg:{cp.bg.less(0.15)} fg:{cp.bg.less(0.15)}",
        "side_bar buttons selection": f"bg:{cp.fg} fg:{cp.hl} reverse",
        "side_bar buttons separator selection before": (
            f"bg:{cp.bg.less(0.15)} fg:{cp.hl} reverse"
        ),
        "side_bar buttons separator selection after": (
            f"fg:{cp.hl} bg:{cp.bg.less(0.15)} noreverse"
        ),
    }


def tabbed_split_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate tabbed split container styles."""
    return {
        "tabbed-split border": f"fg:{cp.bg.more(0.2)}",
        "tabbed-split border left": f"bg:{cp.bg.more(0.025)}",
        "tabbed-split border right": f"bg:{cp.bg.more(0.025)}",
        "tabbed-split border bottom left": f"bg:{cp.bg}",
        "tabbed-split border bottom right": f"bg:{cp.bg}",
        "tabbed-split page": f"bg:{cp.bg.more(0.025)}",
        "tabbed-split tab-bar tab inactive": f"fg:{cp.bg.more(0.3)}",
        "tabbed-split tab-bar tab inactive title": f"bg:{cp.bg.darker(0.05)}",
        "tabbed-split tab-bar tab inactive border left": f"bg:{cp.bg.darker(0.05)}",
        "tabbed-split tab-bar tab inactive border right": f"bg:{cp.bg.darker(0.05)}",
        "tabbed-split tab-bar tab active": f"bold fg:{cp.fg}",
        "tabbed-split tab-bar tab active title": f"bg:{cp.bg.more(0.025)}",
        "tabbed-split tab-bar tab active close": "fg:darkred",
    }


def ipywidget_styles(
    cp: ColorPalette, style_variants: dict[str, ColorPaletteColor]
) -> dict[str, str]:
    """Generate ipywidget styles."""

    def borders(
        template: str,
        color: ColorPaletteColor | Callable[[ColorPaletteColor], ColorPaletteColor],
        inset: bool = False,
    ) -> dict[str, str]:
        """Generate border style definitions for all four directions."""
        styles = {}

        if callable(color):
            # Variant mode
            for variant, variant_color in style_variants.items():
                c = color(variant_color)
                if inset:
                    styles[template.format("top", variant)] = f"fg:{c.darker(0.5)}"
                    styles[template.format("left", variant)] = f"fg:{c.darker(0.5)}"
                    styles[template.format("bottom", variant)] = f"fg:{c.lighter(0.1)}"
                    styles[template.format("right", variant)] = f"fg:{c.lighter(0.1)}"
                else:  # outset
                    styles[template.format("top", variant)] = f"fg:{c.lighter(0.1)}"
                    styles[template.format("left", variant)] = f"fg:{c.lighter(0.1)}"
                    styles[template.format("bottom", variant)] = f"fg:{c.darker(0.5)}"
                    styles[template.format("right", variant)] = f"fg:{c.darker(0.5)}"
        else:
            # Static mode
            if inset:
                styles[template.format("top")] = f"fg:{color.darker(0.25)}"
                styles[template.format("left")] = f"fg:{color.darker(0.25)}"
                styles[template.format("bottom")] = f"fg:{color.lighter(0.25)}"
                styles[template.format("right")] = f"fg:{color.lighter(0.25)}"
            else:  # outset
                styles[template.format("top")] = f"fg:{color.lighter(0.25)}"
                styles[template.format("left")] = f"fg:{color.lighter(0.25)}"
                styles[template.format("bottom")] = f"fg:{color.darker(0.25)}"
                styles[template.format("right")] = f"fg:{color.darker(0.25)}"

        return styles

    return {
        "ipywidget focused": f"bg:{cp.bg.more(0.05)}",
        "ipywidget slider track": f"fg:{cp.fg.darker(0.5)}",
        "ipywidget slider arrow": f"fg:{cp.fg.darker(0.25)}",
        "ipywidget slider handle": f"fg:{cp.fg.darker(0.25)}",
        "ipywidget accordion border default": f"fg:{cp.bg.more(0.2)}",
        **borders("ipywidget border {} {}", lambda c: c),
        **borders("ipywidget selection border {} {}", lambda c: c, inset=True),
    }


def input_widget_styles(
    cp: ColorPalette, style_variants: dict[str, ColorPaletteColor]
) -> dict[str, str]:
    """Generate input widget styles."""

    def variants(
        template: str, definition: Callable[[ColorPaletteColor], str]
    ) -> dict[str, str]:
        """Generate style definitions for all variants."""
        styles = {}
        for variant, color in style_variants.items():
            styles[template.format(variant)] = definition(color)
        return styles

    def borders(
        template: str,
        color: ColorPaletteColor | Callable[[ColorPaletteColor], ColorPaletteColor],
        inset: bool = False,
    ) -> dict[str, str]:
        """Generate border style definitions for all four directions."""
        styles = {}

        if callable(color):
            # Variant mode
            for variant, variant_color in style_variants.items():
                c = color(variant_color)
                if inset:
                    styles[template.format("top", variant)] = f"fg:{c.darker(0.5)}"
                    styles[template.format("left", variant)] = f"fg:{c.darker(0.5)}"
                    styles[template.format("bottom", variant)] = f"fg:{c.lighter(0.1)}"
                    styles[template.format("right", variant)] = f"fg:{c.lighter(0.1)}"
                else:  # outset
                    styles[template.format("top", variant)] = f"fg:{c.lighter(0.1)}"
                    styles[template.format("left", variant)] = f"fg:{c.lighter(0.1)}"
                    styles[template.format("bottom", variant)] = f"fg:{c.darker(0.5)}"
                    styles[template.format("right", variant)] = f"fg:{c.darker(0.5)}"
        else:
            # Static mode
            if inset:
                styles[template.format("top")] = f"fg:{color.darker(0.25)}"
                styles[template.format("left")] = f"fg:{color.darker(0.25)}"
                styles[template.format("bottom")] = f"fg:{color.lighter(0.25)}"
                styles[template.format("right")] = f"fg:{color.lighter(0.25)}"
            else:  # outset
                styles[template.format("top")] = f"fg:{color.lighter(0.25)}"
                styles[template.format("left")] = f"fg:{color.lighter(0.25)}"
                styles[template.format("bottom")] = f"fg:{color.darker(0.25)}"
                styles[template.format("right")] = f"fg:{color.darker(0.25)}"

        return styles

    return {
        # Colored icons on faces
        **variants("face icon {}", lambda c: f"fg:{c}"),
        # Focused faces
        **variants("focused face {}", lambda c: f"bg:{c}"),
        # Selected faces
        **variants("selection face {}", lambda c: f"bg:{c.darker(0.05)}"),
        # Hovered faces
        **variants("focused hovered face {}", lambda c: f"bg:{c.lighter(0.05)}"),
        # Text areas
        "text-area focused": "noreverse",
        "text-area selected": "noreverse",
        "text-area focused selected": "reverse",
        # Buttons
        "input button face": f"fg:default bg:{cp.bg.more(0.05)}",
        "input button face hovered": f"fg:{cp.fg} bg:{cp.bg.more(0.2)}",
        "input button face selection": f"bg:{cp.fg} fg:{cp.bg.more(0.05)} reverse",
        "input button face focused": f"bg:{cp.fg} fg:{cp.bg.towards(cp.hl, 0.1)} reverse",
        **variants("input button face hovered {}", lambda c: f"bg:{cp.bg.more(0.2)}"),
        **variants(
            "input button face selection {}", lambda c: f"fg:{cp.bg.more(0.05)} reverse"
        ),
        **variants(
            "input button face focused {}",
            lambda c: f"fg:{cp.bg.towards(cp.hl, 0.1)} reverse",
        ),
        # Input widgets
        **borders("input border {}", cp.bg),
        **borders("input border {} focused", cp.hl),
        **borders("input border {} selection", cp.bg, inset=True),
        **borders("input border {} selection focused", cp.hl, inset=True),
        **borders("input inset border {}", cp.bg, inset=True),
        **borders("input inset border {} focused", cp.hl, inset=True),
        **borders("input inset border {} selection", cp.bg),
        **borders("input inset border {} selection focused", cp.hl),
        "input text text-area": f"fg:default bg:{cp.bg.lighter(0.1)}",
        **borders("input text border {}", cp.bg, inset=True),
        **borders("input text border {} focused", cp.hl, inset=True),
        "input border top invalid": "fg:ansidarkred",
        "input border right invalid": "fg:ansired",
        "input border bottom invalid": "fg:ansired",
        "input border left invalid": "fg:ansidarkred",
        "input radio-buttons prefix selection focused": f"fg:{cp.hl}",
        "input slider arrow": f"fg:{cp.fg.darker(0.25)}",
        "input slider track": f"fg:{cp.fg.darker(0.5)}",
        "input slider track selection": f"fg:{cp.hl}",
        "input slider handle": f"fg:{cp.fg.darker(0.25)}",
        "input slider handle focused": f"fg:{cp.fg}",
        "input slider handle selection focused": f"fg:{cp.hl}",
        "input dropdown dropdown.menu": f"bg:{cp.bg.more(0.05)}",
        "input dropdown dropdown.menu hovered": f"bg:{cp.hl}",
        "input select face": f"bg:{cp.bg.lighter(0.1)}",
        "input select face selection": f"fg:white bg:{cp.hl}",
        "input select face hovered": f"bg:{cp.bg.more(0.2)}",
        "input select face hovered selection": f"fg:white bg:{cp.hl}",
        "input list border": f"fg:{cp.bg.more(0.5)}",
        "input list face": f"bg:{cp.bg.lighter(0.1)}",
        "input list face placeholder": f"fg:{cp.fg.more(0.5)}",
        "input list face row alt": f"bg:{cp.bg.lighter(0.1).more(0.01)}",
        "input list face row hovered": f"bg:{cp.bg.more(0.2)}",
        "input list face row selection": f"bg:{cp.bg.more(0.3)}",
        "input list face row selection focused": f"bg:{cp.fg} fg:{cp.hl} reverse",
    }


def dataframe_styles(cp: ColorPalette) -> dict[str, str]:
    """Generate dataframe display styles."""
    return {
        "dataframe th": f"bg:{cp.bg.more(0.1)}",
        "dataframe row-odd td": f"bg:{cp.bg.more(0.05)}",
    }


def build_style(
    cp: ColorPalette,
    have_term_colors: bool = True,
) -> Style:
    """Create an application style based on the given color palette."""
    style_variants = {
        "primary": cp.ansiblue,
        "success": cp.ansigreen,
        "info": cp.ansicyan,
        "warning": cp.ansiyellow,
        "danger": cp.ansired,
        "orange": ColorPaletteColor("#ffa500"),
        "teal": ColorPaletteColor("#008080"),
        "purple": ColorPaletteColor("#800080"),
    }

    style_dict = {
        # The default style is merged at this point so full styles can be
        # overridden. For example, this allows us to switch off the underline
        # status of cursor-line.
        **dict(default_ui_style().style_rules),
        **base_styles(cp),
        **chrome_styles(cp),
        **statusbar_styles(cp),
        **menu_styles(cp),
        **tab_bar_styles(cp),
        **buffer_styles(cp),
        **cell_styles(cp),
        **scrollbar_styles(cp),
        **dialog_styles(cp),
        **toolbar_styles(cp),
        **completion_styles(cp),
        **shortcuts_styles(cp),
        **palette_styles(cp),
        **pager_styles(cp),
        **markdown_styles(cp),
        **shadow_styles(cp),
        **sidebar_styles(cp),
        **tabbed_split_styles(cp),
        **ipywidget_styles(cp, style_variants),
        **input_widget_styles(cp, style_variants),
        **dataframe_styles(cp),
    }

    return Style.from_dict(style_dict)


@cache
def get_style_by_name(name: str) -> type[PygmentsStyle]:
    """Get Pygments style, caching the result."""
    return pyg_get_style_by_name(name)
