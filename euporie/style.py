"""Style related functions."""

from colorsys import hls_to_rgb, rgb_to_hls
from typing import TYPE_CHECKING

from prompt_toolkit.styles.defaults import default_ui_style
from prompt_toolkit.styles.style import Style

if TYPE_CHECKING:
    from typing import Any, Dict, Optional, Tuple


MARKDOWN_STYLE = [
    ("md.h1", "bold underline"),
    ("md.h1.border", "fg:ansiyellow nounderline"),
    ("md.h2", "bold"),
    ("md.h2.border", "fg:grey nobold"),
    ("md.h3", "bold"),
    ("md.h4", "bold italic"),
    ("md.h5", "underline"),
    ("md.h6", "italic"),
    ("md.code.inline", "bg:#333"),
    ("md.strong", "bold"),
    ("md.em", "italic"),
    ("md.hr", "fg:ansired"),
    ("md.ul.margin", "fg:ansiyellow"),
    ("md.ol.margin", "fg:ansicyan"),
    ("md.blockquote", "fg:ansipurple"),
    ("md.blockquote.margin", "fg:grey"),
    ("md.th", "bold"),
    ("md.a", "underline fg:ansibrightblue"),
    ("md.s", "strike"),
    ("md.img", "bg:cyan fg:black"),
    ("md.img.border", "fg:cyan bg:default"),
]


LOG_STYLE = [
    ("log.level.nonset", "fg:grey"),
    ("log.level.debug", "fg:green"),
    ("log.level.info", "fg:blue"),
    ("log.level.warning", "fg:yellow"),
    ("log.level.error", "fg:red"),
    ("log.level.critical", "fg:white bg:red bold"),
    ("log.ref", "fg:grey italic"),
    ("log.date", "fg:ansiblue"),
]


class ColorPaletteColor:
    """A representation of a color with adjustment methods."""

    def __init__(self, name: "str", base: "str", _base_override: str = "") -> "None":
        """Creates a new color."""
        self.name = name
        self.base_hex = base
        self.base = _base_override or base

        color = base.lstrip("#")
        self.red, self.green, self.blue = (
            int(color[0:2], 16) / 255,
            int(color[2:4], 16) / 255,
            int(color[4:6], 16) / 255,
        )

        self.hue, self.brightness, self.saturation = rgb_to_hls(
            self.red, self.green, self.blue
        )

        self.is_light = self.brightness > 0.5

        self._cache: "Dict[Tuple[float, float, float, bool], str]" = {}

    def _adjust_abs(
        self, hue: "float" = 0.0, brightness: "float" = 0.0, saturation: "float" = 0.0
    ) -> "str":
        hue = max(min(1, self.hue + hue), 0)
        brightness = max(min(1, self.brightness + brightness), 0)
        saturation = max(min(1, self.saturation + saturation), 0)

        r, g, b = hls_to_rgb(hue, brightness, saturation)
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return new_color

    def _adjust_rel(
        self, hue: "float" = 0.0, brightness: "float" = 0.0, saturation: "float" = 0.0
    ) -> "str":
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
        return new_color

    def _adjust(
        self,
        hue: "float" = 0.0,
        brightness: "float" = 0.0,
        saturation: "float" = 0.0,
        rel: "bool" = True,
    ) -> "str":
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
    ) -> "str":
        """Adjust the hue, saturation, or brightness of the color."""
        key = (hue, brightness, saturation, rel)
        if key in self._cache:
            return self._cache[key]
        else:
            return self._cache.setdefault(key, self._adjust(*key))

    def lighter(self, amount: "float", rel: "bool" = True) -> "str":
        """Makes the color lighter."""
        return self.adjust(brightness=amount, rel=rel)

    def darker(self, amount: "float", rel: "bool" = True) -> "str":
        """Makes the color darker."""
        return self.adjust(brightness=-amount, rel=rel)

    def more(self, amount: "float", rel: "bool" = True) -> "str":
        """Makes bright colors darker and dark colors brighter."""
        if self.is_light:
            amount *= -1
        return self.adjust(brightness=amount, rel=rel)

    def less(self, amount: "float", rel: "bool" = True) -> "str":
        """Makes bright colors brighter and dark colors darker."""
        if self.is_light:
            amount *= -1
        return self.adjust(brightness=-amount, rel=rel)

    def __repr__(self) -> "str":
        """Returns a string representation of the color."""
        return self.base


class ColorPalette:
    """Defines a collection of colors."""

    def __init__(self):
        """Creates a new color-palette."""
        self.colors = {}
        self.add_color("black", "#000000")
        self.add_color("white", "#FFFFFF")

    def add_color(
        self, name: "str", base: "str", _base_override: str = ""
    ) -> "ColorPalette":
        """Adds a color to the palette."""
        self.colors[name] = ColorPaletteColor(name, base, _base_override)
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
    cp: "Optional[ColorPalette]",
    have_term_colors: "bool" = True,
) -> "Style":
    """Create an application style based on the given color palette."""
    if cp is None:
        cp = (
            ColorPalette()
            .add_color("fg", "#FFFFFF", "default")
            .add_color("bg", "#000000", "default")
        )

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
        "chrome": f"fg:{cp.fg.more(1/20)} bg:{cp.bg.more(1/20)}",
        "tab-padding": f"fg:{cp.bg.more(4/20)} bg:{cp.bg.base}",
        # Statusbar
        "status": f"fg:{cp.fg.more(1/20)} bg:{cp.bg.more(1/20)}",
        "status.field": f"fg:{cp.fg.more(2/20)} bg:{cp.bg.more(2/20)}",
        # Menus & Menu bar
        "menu-bar": f"fg:{cp.fg.more(1/20)} bg:{cp.bg.more(1/20)}",
        "menu-bar.disabled-item": f"fg:{cp.bg.more(3/20)}",
        "menu-bar.selected-item": "reverse",
        "menu-bar.shortcut": f"fg:{cp.fg.more(5/20)}",
        "menu-bar.selected-item menu-bar.shortcut": (
            f"fg:{cp.fg.more(1/20)} bg:{cp.bg.more(4/20)}"
        ),
        "menu-bar.disabled-item menu-bar.shortcut": f"fg:{cp.bg.more(3/20)}",
        "menu": f"bg:{cp.bg.more(1/20)} fg:{cp.fg.more(1/20)}",
        "menu-border": f"fg:{cp.bg.more(6/20)} bg:{cp.bg.more(1/20)}",
        "menu-border menu-bar.selected-item": f"fg:{cp.fg.more(1/20)} bg:{cp.bg.more(6/20)} ",
        # Tab bar
        "tab-bar": f"fg:{cp.bg.more(4/20)} bg:{cp.bg.darker(3/20)}",
        "tab-bar.tab": f"fg:{cp.bg.more(2/20)} bg:{cp.bg.more(-3/20)}",
        "tab-bar.tab.head": f"fg:{cp.bg.more(3/20)} bg:{cp.bg.darker(3/20)}",
        "tab-bar.tab.edge": f"fg:{cp.bg.more(3/20)} bg:{cp.bg.more(-3/20)}",
        "tab-bar.tab.close": "",
        "tab-bar.tab active": f"bold fg:{cp.fg.more(0/20)} bg:{cp.bg.base}",
        "tab-bar.tab.head active": f"fg:ansiblue bg:{cp.bg.darker(3/20)}",
        "tab-bar.tab.edge active": f"fg:{cp.bg.more(4/20)} bg:{cp.bg.base}",
        "tab-bar.tab.close active": "fg:darkred",
        # Buffer
        "line-number": f"fg:{cp.fg.more(10/20)} bg:{cp.bg.more(1/20)}",
        "line-number.current": f"bold orange bg:{cp.bg.more(2/20)}",
        "line-number edge": f"fg:{cp.bg.darker(0.1)}",
        "line-number.current edge": f"fg:{cp.bg.darker(0.1)}",
        "cursor-line": f"bg:{cp.bg.more(1/20)}",
        "cursor-line incsearch": "bg:ansibrightyellow",
        "cursor-line incsearch.current": "bg:ansibrightgreen",
        "matching-bracket.cursor": "fg:yellow bold",
        "matching-bracket.other": "fg:yellow bold",
        # Search
        "incsearch": "bg:ansibrightyellow",
        "incsearch.current": "bg:ansibrightgreen",
        "search-toolbar": f"fg:{cp.fg.more(1/20)} bg:{cp.bg.more(1/20)}",
        "search-toolbar.title": f"fg:{cp.fg.more(2/20)} bg:{cp.bg.more(2/20)}",
        # Cells
        "cell.border": f"fg:{cp.bg.more(5/20)}",
        "cell.border.selected": "fg:ansibrightblue",
        "cell.border.edit": "fg:ansibrightgreen",
        "cell.input.box": f"fg:default bg:{cp.bg.more(0.02)}",
        "cell.output": "fg:default bg:default",
        "cell.input.prompt": "fg:blue",
        "cell.output.prompt": "fg:red",
        # Scrollbars
        "scrollbar": f"fg:{cp.bg.more(15/20)} bg:{cp.bg.more(3/20)}",
        "scrollbar.background": f"fg:{cp.bg.more(15/20)} bg:{cp.bg.more(3/20)}",
        "scrollbar.arrow": f"fg:{cp.bg.more(15/20)} bg:{cp.bg.more(3/20)}",
        "scrollbar.start": "",
        "scrollbar.button": f"fg:{cp.bg.more(15/20)} bg:{cp.bg.more(15/20)}",
        "scrollbar.end": f"fg:{cp.bg.more(3/20)} bg:{cp.bg.more(15/20)}",
        # Dialogs
        "dialog.body": f"fg:{cp.fg.base} bg:{cp.bg.darker(2/20)}",
        "dialog.body text-area": f"fg:{cp.fg.base}",
        "dialog.body scrollbar.button": f"fg:{cp.bg.more(5/20)} bg:{cp.bg.more(15/20)}",
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
        # Shortcuts
        "shortcuts.group": f"bg:{cp.bg.more(8/20)} bold underline",
        "shortcuts.row": f"bg:{cp.bg.base} nobold",
        "shortcuts.row alt": f"bg:{cp.bg.more(2/20)}",
        "shortcuts.row key": "bold",
        # Palette
        "palette.item": f"fg:{cp.fg.more(1/20)} bg:{cp.bg.more(1/20)}",
        "palette.item.alt": f"bg:{cp.bg.more(3/20)}",
        "palette.item.selected": "fg:#ffffff bg:ansiblue",
        # Pager
        "pager": f"bg:{cp.bg.more(1/20)}",
        "pager.border": f"fg:{cp.bg.more(9/20)}",
        # Markdown
        "md.code.inline": f"bg:{cp.bg.more(3/20)}",
        "md.code.block": f"bg:{cp.bg.less(0.2)}",
        "md.code.block.border": f"fg:{cp.bg.more(5/20)}",
        "md.table.border": f"fg:{cp.bg.more(15/20)}",
        # Drop-shadow
        "drop-shadow.inner": f"fg:{cp.bg.darker(3/20)}",
        "drop-shadow.outer": f"fg:{cp.bg.darker(2/20)} bg:{cp.bg.darker(0.5/20)}",
        # Shadows
        "shadow": f"bg:{cp.bg.darker(0.45)}",
        # Inputs
        "input": f"bg:{cp.bg.more(0.05)}",
        "button": f"bg:{cp.bg.more(0.05)}",
        "button.arrow": "",
        "button button.focused": "fg:#ffffff bg:ansidarkred",
    }

    # Add shadow combination for every element
    style_dict.update(
        {
            f"{key} shadow": f"bg:{cp.bg.darker(0.45)}"
            for key in style_dict
            if key not in ("menu", "menu-border")
        }
    )

    return Style.from_dict(style_dict)
