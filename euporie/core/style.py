"""Style related functions."""

from __future__ import annotations

import logging
from colorsys import hls_to_rgb, rgb_to_hls
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.styles.defaults import default_ui_style
from prompt_toolkit.styles.style import Style

if TYPE_CHECKING:
    from typing import Any


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
    "ansipurple": "#cb1ed1",
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
    ("mime.stream.stderr", "fg:ansired"),
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


LOG_STYLE = [
    ("log.level.nonset", "fg:ansigray"),
    ("log.level.debug", "fg:ansigreen"),
    ("log.level.info", "fg:ansiblue"),
    ("log.level.warning", "fg:ansiyellow"),
    ("log.level.error", "fg:ansired"),
    ("log.level.critical", "fg:ansiwhite bg:ansired bold"),
]

IPYWIDGET_STYLE = [
    ("ipywidget", "bg:default"),
    ("ipywidget focused", ""),
    ("ipywidget button face", "fg:black bg:#d4d0c8"),
    ("ipywidget button face selection", "bg:#e9e7e3"),
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
    # ("ipywidget success border right selection", "fg:ansibrightgreen"),
    # ("ipywidget success border bottom selection", "fg:ansibrightgreen"),
    # ("ipywidget success border right selection", "fg:ansibrightgreen"),
    # ("ipywidget success border bottom selection", "fg:ansibrightgreen"),
    # ("ipywidget info border right selection", "fg:ansibrightcyan"),
    # ("ipywidget info border bottom selection", "fg:ansibrightcyan"),
    # ("ipywidget danger border right selection", "fg:ansibrightred"),
    # ("ipywidget danger border bottom selection", "fg:ansibrightred"),
    ("ipywidget text text-area", "fg:black bg:white"),
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
    ("ipywidget progress success", "fg:ansigreen"),
    ("ipywidget progress info", "fg:ansicyan"),
    ("ipywidget progress warning", "fg:ansiyellow"),
    ("ipywidget progress danger", "fg:ansired"),
    ("ipywidget progress border", "bg:default"),
    ("ipywidget progress border top", "fg:#606060"),
    ("ipywidget progress border right", "fg:#E9E7E3"),
    ("ipywidget progress border bottom", "fg:#E9E7E3"),
    ("ipywidget progress border left", "fg:#606060"),
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
    ("ipywidget tabbed-split tab-bar tab active border top success", "fg:ansigreen"),
    ("ipywidget tabbed-split tab-bar tab active border top info", "fg:ansicyan"),
    ("ipywidget tabbed-split tab-bar tab active border top warning", "fg:ansiyellow"),
    ("ipywidget tabbed-split tab-bar tab active border top danger", "fg:ansired"),
    ("ipywidget accordion border success", "fg:ansigreen"),
    ("ipywidget accordion border info", "fg:ansicyan"),
    ("ipywidget accordion border warning", "fg:ansiyellow"),
    ("ipywidget accordion border danger", "fg:ansired"),
    ("ipywidget accordion selection", "fg:ansiblue"),
]


class ColorPaletteColor:
    """A representation of a color with adjustment methods."""

    _cache: "SimpleCache[tuple[str, float, float, float, bool], ColorPaletteColor]" = (
        SimpleCache()
    )

    def __init__(self, base: "str", _base_override: str = "") -> "None":
        """Creates a new color."""
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
        self, hue: "float" = 0.0, brightness: "float" = 0.0, saturation: "float" = 0.0
    ) -> "ColorPaletteColor":
        hue = max(min(1, self.hue + hue), 0)
        brightness = max(min(1, self.brightness + brightness), 0)
        saturation = max(min(1, self.saturation + saturation), 0)

        r, g, b = hls_to_rgb(hue, brightness, saturation)
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return ColorPaletteColor(new_color)

    def _adjust_rel(
        self, hue: "float" = 0.0, brightness: "float" = 0.0, saturation: "float" = 0.0
    ) -> "ColorPaletteColor":
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
        hue: "float" = 0.0,
        brightness: "float" = 0.0,
        saturation: "float" = 0.0,
        rel: "bool" = True,
    ) -> "ColorPaletteColor":
        """Performs a relative of absolute color adjustment."""
        if rel:
            return self._adjust_rel(hue, brightness, saturation)
        else:
            return self._adjust_abs(hue, brightness, saturation)

    def adjust(
        self,
        hue: "float" = 0.0,
        brightness: "float" = 0.0,
        saturation: "float" = 0.0,
        rel: "bool" = True,
    ) -> "ColorPaletteColor":
        """Adjust the hue, saturation, or brightness of the color."""
        key = (self.base_hex, hue, brightness, saturation, rel)
        return self._cache.get(
            key, partial(self._adjust, hue, brightness, saturation, rel)
        )

    def lighter(self, amount: "float", rel: "bool" = True) -> "ColorPaletteColor":
        """Makes the color lighter."""
        return self.adjust(brightness=amount, rel=rel)

    def darker(self, amount: "float", rel: "bool" = True) -> "ColorPaletteColor":
        """Makes the color darker."""
        return self.adjust(brightness=-amount, rel=rel)

    def more(self, amount: "float", rel: "bool" = True) -> "ColorPaletteColor":
        """Makes bright colors darker and dark colors brighter."""
        if self.is_light:
            amount *= -1
        return self.adjust(brightness=amount, rel=rel)

    def less(self, amount: "float", rel: "bool" = True) -> "ColorPaletteColor":
        """Makes bright colors brighter and dark colors darker."""
        if self.is_light:
            amount *= -1
        return self.adjust(brightness=-amount, rel=rel)

    def towards(
        self, other: "ColorPaletteColor", amount: "float"
    ) -> "ColorPaletteColor":
        """Interpolate between two colors."""
        amount = min(max(0, amount), 1)
        r = (other.red - self.red) * amount + self.red
        g = (other.green - self.green) * amount + self.green
        b = (other.blue - self.blue) * amount + self.blue
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return ColorPaletteColor(new_color)

    def __repr__(self) -> "str":
        """Returns a string representation of the color."""
        return self.base


class ColorPalette:
    """Defines a collection of colors."""

    def __init__(self) -> "None":
        """Creates a new color-palette."""
        self.colors: "dict[str, ColorPaletteColor]" = {}

    def add_color(
        self, name: "str", base: "str", _base_override: str = ""
    ) -> "ColorPalette":
        """Adds a color to the palette."""
        self.colors[name] = ColorPaletteColor(base, _base_override)
        return self

    def __getattr__(self, name: "str") -> "Any":
        """Enables access of palette colors via dotted attributes.

        Args:
            name: The name of the attribute to access.

        Returns:
            The color-palette color.

        """
        return self.colors.get(name)


def build_style(
    cp: "ColorPalette",
    have_term_colors: "bool" = True,
) -> "Style":
    """Create an application style based on the given color palette."""
    style_dict = {
        # The default style is merged at this point so full styles can be
        # overridden. For example, this allows us to switch off the underline
        # status of cursor-line.
        **dict(default_ui_style().style_rules),
        "default": f"fg:{cp.bg.base} bg:{cp.bg.base}",
        # Logo
        "logo": "fg:#dd0000",
        # Pattern
        "pattern": f"fg:{cp.bg.more(0.075)}",
        # Chrome
        "chrome": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "tab-padding": f"fg:{cp.bg.more(0.2)} bg:{cp.bg.base}",
        # Statusbar
        "status": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "status.field": f"fg:{cp.fg.more(0.1)} bg:{cp.bg.more(0.1)}",
        # Menus & Menu bar
        "menu": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "menu bar": f"bg:{cp.bg.less(0.15)}",
        "menu disabled": f"fg:{cp.fg.more(0.05).towards(cp.bg, 0.75)}",
        "menu shortcut": f"fg:{cp.fg.more(0.4)}",
        "menu shortcut disabled": f"fg:{cp.fg.more(0.4).towards(cp.bg, 0.5)}",
        "menu prefix": f"fg:{cp.fg.more(0.2)}",
        "menu prefix disabled": f"fg:{cp.fg.more(0.2).towards(cp.bg, 0.5)}",
        "menu selection": f"fg:{cp.hl.more(1)} bg:{cp.hl}",
        "menu selection shortcut": f"fg:{cp.hl.more(1).more(0.05)} bg:{cp.hl}",
        "menu selection prefix": f"fg:{cp.hl.more(1).more(0.05)} bg:{cp.hl}",
        "menu border": f"fg:{cp.bg.more(0.15)} bg:{cp.bg.more(0.05)}",
        "menu border selection": f"bg:{cp.hl}",
        # Tab bar
        "app-tab-bar": f"bg:{cp.bg.less(0.15)}",
        "app-tab-bar border": f"fg:{cp.bg.more(0.1)}",
        "app-tab-bar tab inactive": f"fg:{cp.fg.more(0.5)}",
        "app-tab-bar tab inactive border": f"fg:{cp.bg.more(0.15)}",
        "app-tab-bar tab active": "bold fg:default bg:default",
        "app-tab-bar tab active close": "fg:darkred",
        "app-tab-bar tab active border top": f"fg:{cp.hl} bg:{cp.bg.less(0.15)}",
        # Buffer
        "line-number": f"fg:{cp.fg.more(0.5)} bg:{cp.bg.more(0.05)}",
        "line-number.current": f"bold orange bg:{cp.bg.more(0.1)}",
        "line-number edge": f"fg:{cp.bg.darker(0.1)}",
        "line-number.current edge": f"fg:{cp.bg.darker(0.1)}",
        "cursor-line": f"bg:{cp.bg.more(0.05)}",
        "cursor-line search": f"bg:{cp.bg.more(0.02)}",
        "cursor-line search.current": f"bg:{cp.bg.more(0.02)}",
        "cursor-line incsearch": "bg:ansibrightyellow",
        "cursor-line incsearch.current": "bg:ansibrightgreen",
        "matching-bracket.cursor": "fg:yellow bold",
        "matching-bracket.other": "fg:yellow bold",
        "trailing-whitespace": f"fg:{cp.fg.more(0.66)}",
        "tab": f"fg:{cp.fg.more(0.66)}",
        # Search
        "search": f"bg:{cp.bg.more(0.05)}",
        "search.current": f"bg:{cp.bg.more(0.05)}",
        "incsearch": "bg:ansibrightyellow",
        "incsearch.current": "bg:ansibrightgreen",
        "search-toolbar": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "search-toolbar.title": f"fg:{cp.fg.more(0.1)} bg:{cp.bg.more(0.1)}",
        # Inputs
        "kernel-input": f"fg:default bg:{cp.bg.more(0.02)}",
        # Cells
        "cell.border": f"fg:{cp.bg.more(0.25)}",
        "cell.border.selected": f"fg:{cp.hl.more(0.2)}",
        "cell.border.edit": "fg:ansibrightgreen",
        "cell.output": "fg:default bg:default",
        "cell.input.prompt": "fg:blue",
        "cell.output.prompt": "fg:red",
        "cell show outputs": "bg:#888",
        "cell show inputs": "bg:#888",
        # Scrollbars
        "scrollbar": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.15)}",
        "scrollbar.background": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.15)}",
        "scrollbar.arrow": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.15)}",
        "scrollbar.start": "",
        # "scrollbar.start": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.25)}",
        "scrollbar.button": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.75)}",
        "scrollbar.end": f"fg:{cp.bg.more(0.15)} bg:{cp.bg.more(0.75)}",
        # Overflow margin
        "overflow": f"fg:{cp.fg.more(0.5)}",
        # Dialogs
        "dialog title": f"fg:white bg:{cp.hl.darker(0.25)} bold",
        "dialog title border": "fg:ansired",
        "dialog": f"fg:{cp.fg.base} bg:{cp.bg.darker(0.1)}",
        "dialog text-area": f"bg:{cp.bg.lighter(0.05)}",
        "dialog input text text-area": f"fg:default bg:{cp.bg.less(0.1)}",
        "dialog text-area last-line": "nounderline",
        "dialog border": f"fg:{cp.bg.darker(0.1).more(0.1)}",
        # Horizontals rule
        "hr": "fg:ansired",
        # Completions menu
        "completion-menu.completion.keyword": "fg:#d700af",
        "completion-menu.completion.current.keyword": "fg:#fff bg:#d700ff",
        "completion-menu.completion.function": "fg:#005faf",
        "completion-menu.completion.current.function": "fg:#fff bg:#005fff",
        "completion-menu.completion.class": "fg:#008700",
        "completion-menu.completion.current.class": "fg:#fff bg:#00af00",
        "completion-menu.completion.statement": "fg:#5f0000",
        "completion-menu.completion.current.statement": "fg:#fff bg:#5f0000",
        "completion-menu.completion.instance": "fg:#d75f00",
        "completion-menu.completion.current.instance": "fg:#fff bg:#d78700",
        "completion-menu.completion.module": "fg:#d70000",
        "completion-menu.completion.current.module": "fg:#fff bg:#d70000",
        # Log
        "log.level.nonset": "fg:grey",
        "log.level.debug": "fg:green",
        "log.level.info": "fg:blue",
        "log.level.warning": "fg:yellow",
        "log.level.error": "fg:red",
        "log.level.critical": "fg:red bold",
        "log.ref": "fg:grey",
        "log.date": "fg:#00875f",
        # File browser
        "file-browser border": f"fg:{cp.bg.more(0.5)}",
        "file-browser face": f"bg:{cp.bg.lighter(0.1)}",
        "file-browser face row alt-row": f"bg:{cp.bg.lighter(0.1).more(0.01)}",
        "file-browser face row hovered": f"bg:{cp.bg.more(0.2)}",
        "file-browser face row selection": f"bg:{cp.hl}",
        # Shortcuts
        "shortcuts.group": f"bg:{cp.bg.more(0.4)} bold underline",
        # "shortcuts.row": f"bg:{cp.bg.base} nobold",
        "shortcuts.row alt": f"bg:{cp.bg.more(0.1)}",
        "shortcuts.row key": "bold",
        # Palette
        "palette.item": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "palette.item.alt": f"bg:{cp.bg.more(0.15)}",
        "palette.item.selected": f"fg:{cp.hl.more(1)} bg:{cp.hl}",
        # Pager
        "pager": f"bg:{cp.bg.more(0.05)}",
        "pager.border": f"fg:{cp.bg.more(0.45)}",
        # Markdown
        "markdown code": f"bg:{cp.bg.more(0.15)}",
        "markdown code block": f"bg:{cp.bg.less(0.2)}",
        "markdown code block border": f"fg:{cp.bg.more(0.25)}",
        "markdown table border": f"fg:{cp.bg.more(0.75)}",
        # Drop-shadow
        "drop-shadow inner": f"fg:{cp.bg.towards(cp.ansiblack, 0.3)}",
        "drop-shadow outer": f"fg:{cp.bg.towards(cp.ansiblack, 0.2)} bg:{cp.bg.towards(cp.ansiblack, 0.05)}",
        # Side-bar
        "side_bar": f"bg:{cp.bg.less(0.15)}",
        "side_bar title": f"fg:{cp.hl}",
        "side_bar title text": f"fg:default bg:{cp.bg.less(0.15).more(0.01)}",
        "side_bar border": f"fg:{cp.bg.towards(cp.ansiblack, 0.3)}",
        "side_bar border outer": f"bg:{cp.bg}",
        "side_bar buttons": f"bg:{cp.bg.less(0.15)}",
        "side_bar buttons hovered": f"fg:{cp.hl}",
        "side_bar buttons selection": f"fg:{cp.fg} bg:{cp.hl}",
        "side_bar buttons separator": f"fg:{cp.bg.less(0.15)} bg:{cp.bg.less(0.15)}",
        "side_bar buttons separator selection before": f"fg:{cp.bg.less(0.15)} bg:{cp.hl}",
        "side_bar buttons separator selection after": f"fg:{cp.hl} bg:{cp.bg.less(0.15)}",
        # Tabbed split
        "tabbed-split tab-bar tab inactive": f"fg:{cp.bg.more(0.1)}",
        "tabbed-split tab-bar tab inactive border": f"fg:{cp.bg.more(0.15)}",
        "tabbed-split tab-bar tab active": f"bold fg:{cp.fg}",
        "tabbed-split tab-bar tab active close": "fg:darkred",
        "tabbed-split border": f"fg:{cp.bg.more(0.2)}",
        # Ipywidgets
        "ipywidget focused": f"bg:{cp.bg.more(0.05)}",
        "ipywidget slider track": f"fg:{cp.fg.darker(0.5)}",
        "ipywidget slider arrow": f"fg:{cp.fg.darker(0.25)}",
        "ipywidget slider handle": f"fg:{cp.fg.darker(0.25)}",
        "ipywidget accordion border default": f"fg:{cp.bg.more(0.2)}",
        ## Styled borders
        "success border top": "fg:ansibrightgreen",
        "success border left": "fg:ansibrightgreen",
        "success border bottom": f"fg:{cp.ansigreen.darker(0.5)}",
        "success border right": f"fg:{cp.ansigreen.darker(0.5)}",
        "info border top": "fg:ansibrightcyan",
        "info border left": "fg:ansibrightcyan",
        "info border bottom": f"fg:{cp.ansicyan.darker(0.5)}",
        "info border right": f"fg:{cp.ansicyan.darker(0.5)}",
        "warning border top": "fg:ansibrightyellow",
        "warning border left": "fg:ansibrightyellow",
        "warning border bottom": f"fg:{cp.ansiyellow.darker(0.5)}",
        "warning border right": f"fg:{cp.ansiyellow.darker(0.5)}",
        "danger border top": "fg:ansibrightred",
        "danger border left": "fg:ansibrightred",
        "danger border bottom": f"fg:{cp.ansired.darker(0.5)}",
        "danger border right": f"fg:{cp.ansired.darker(0.5)}",
        ## Selected styled borders
        "selection success border top": f"fg:{cp.ansigreen.darker(0.5)}",
        "selection success border left": f"fg:{cp.ansigreen.darker(0.5)}",
        "selection success border bottom": "fg:ansibrightgreen",
        "selection success border right": "fg:ansibrightgreen",
        "selection info border left": f"fg:{cp.ansicyan.darker(0.5)}",
        "selection info border top": f"fg:{cp.ansicyan.darker(0.5)}",
        "selection info border right": "fg:ansibrightcyan",
        "selection info border bottom": "fg:ansibrightcyan",
        "selection warning border top": f"fg:{cp.ansiyellow.darker(0.5)}",
        "selection warning border left": f"fg:{cp.ansiyellow.darker(0.5)}",
        "selection warning border bottom": "fg:ansibrightyellow",
        "selection warning border right": "fg:ansibrightyellow",
        "selection danger border top": f"fg:{cp.ansired.darker(0.5)}",
        "selection danger border left": f"fg:{cp.ansired.darker(0.5)}",
        "selection danger border bottom": "fg:ansibrightred",
        "selection danger border right": "fg:ansibrightred",
        # Selected faces
        "selection success face": f"bg:{cp.ansigreen.darker(0.05)}",
        "selection info face": f"bg:{cp.ansicyan.darker(0.05)}",
        "selection warning face": f"bg:{cp.ansiyellow.darker(0.05)}",
        "selection danger face": f"bg:{cp.ansired.darker(0.05)}",
        # Hovered faces
        "focused hovered success face": f"bg:{cp.ansigreen.lighter(0.05)}",
        "focused hovered info face": f"bg:{cp.ansicyan.lighter(0.05)}",
        "focused hovered warning face": f"bg:{cp.ansiyellow.lighter(0.05)}",
        "focused hovered danger face": f"bg:{cp.ansired.lighter(0.05)}",
        # Input widgets
        "text-area focused": "noreverse",
        "text-area selected": "noreverse",
        "text-area focused selected": "reverse",
        # "input focused": f"bg:{cp.bg.more(0.025)}",
        # "input button face": f"fg:default bg:{cp.bg.more(0.05)}",
        "input button face selection": f"bg:{cp.bg.more(0.05)}",
        # "input button face focused": f"fg:default bg:{cp.hl.darker(0.75)}",
        "input border top": f"fg:{cp.bg.lighter(0.5)}",
        "input border left": f"fg:{cp.bg.lighter(0.5)}",
        "input border bottom": f"fg:{cp.bg.darker(0.25)}",
        "input border right": f"fg:{cp.bg.darker(0.25)}",
        "input border top focused": f"fg:{cp.hl.lighter(0.5)}",
        "input border left focused": f"fg:{cp.hl.lighter(0.5)}",
        "input border bottom focused": f"fg:{cp.hl.darker(0.5)}",
        "input border right focused": f"fg:{cp.hl.darker(0.5)}",
        "input border top selection": f"fg:{cp.bg.darker(0.5)}",
        "input border left selection": f"fg:{cp.bg.darker(0.5)}",
        "input border bottom selection": f"fg:{cp.bg.lighter(0.5)}",
        "input border right selection": f"fg:{cp.bg.lighter(0.5)}",
        "input border top selection focused": f"fg:{cp.hl.darker(0.5)}",
        "input border left selection focused": f"fg:{cp.hl.darker(0.5)}",
        "input border bottom selection focused": f"fg:{cp.hl.lighter(0.5)}",
        "input border right selection focused": f"fg:{cp.hl.lighter(0.5)}",
        "input inset border bottom": f"fg:{cp.bg.lighter(0.5)}",
        "input inset border right": f"fg:{cp.bg.lighter(0.5)}",
        "input inset border top": f"fg:{cp.bg.darker(0.25)}",
        "input inset border left": f"fg:{cp.bg.darker(0.25)}",
        "input inset border bottom focused": f"fg:{cp.hl.lighter(0.5)}",
        "input inset border right focused": f"fg:{cp.hl.lighter(0.5)}",
        "input inset border top focused": f"fg:{cp.hl.darker(0.5)}",
        "input inset border left focused": f"fg:{cp.hl.darker(0.5)}",
        "input inset border bottom selection": f"fg:{cp.bg.darker(0.5)}",
        "input inset border right selection": f"fg:{cp.bg.darker(0.5)}",
        "input inset border top selection": f"fg:{cp.bg.lighter(0.5)}",
        "input inset border left selection": f"fg:{cp.bg.lighter(0.5)}",
        "input inset border bottom selection focused": f"fg:{cp.hl.darker(0.5)}",
        "input inset border right selection focused": f"fg:{cp.hl.darker(0.5)}",
        "input inset border top selection focused": f"fg:{cp.hl.lighter(0.5)}",
        "input inset border left selection focused": f"fg:{cp.hl.lighter(0.5)}",
        "input text placeholder": f"fg:{cp.fg.more(0.6)}",
        "input text text-area": f"bg:{cp.bg.lighter(0.1)}",
        "input text border top": f"fg:{cp.bg.darker(0.5)}",
        "input text border right": f"fg:{cp.bg.lighter(0.25)}",
        "input text border bottom": f"fg:{cp.bg.lighter(0.25)}",
        "input text border left": f"fg:{cp.bg.darker(0.5)}",
        "input text border top focused": f"fg:{cp.hl.darker(0.5)}",
        "input text border right focused": f"fg:{cp.hl.lighter(0.5)}",
        "input text border bottom focused": f"fg:{cp.hl.lighter(0.5)}",
        "input text border left focused": f"fg:{cp.hl.darker(0.5)}",
        "input text border top invalid": "fg:ansidarkred",
        "input text border right invalid": "fg:ansired",
        "input text border bottom invalid": "fg:ansired",
        "input text border left invalid": "fg:ansidarkred",
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
        # Dataframes
        "dataframe th": f"bg:{cp.bg.more(0.1)}",
        "dataframe row-odd td": f"bg:{cp.bg.more(0.05)}",
    }

    return Style.from_dict(style_dict)
