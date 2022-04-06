"""Style related functions."""

from colorsys import hls_to_rgb, rgb_to_hls
from functools import lru_cache
from typing import TYPE_CHECKING

from prompt_toolkit.styles.defaults import default_ui_style
from prompt_toolkit.styles.style import Style

from euporie.config import config

if TYPE_CHECKING:
    from typing import Any, Dict, Optional, Union


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
    ("log.level.critical", "fg:red bold"),
    ("log.ref", "fg:grey italic"),
    ("log.date", "fg:ansiblue"),
]


@lru_cache
def color_series(
    n: "int" = 10, interval: "float" = 0.05, **kwargs: "Any"
) -> "Dict[str, Dict[Union[str, int], str]]":
    """Create a series of dimmed colours."""
    series: "Dict[str, Dict[Union[int, str], str]]" = {
        key: {"base": value} for key, value in kwargs.items()
    }

    for name, color in kwargs.items():
        color = color.lstrip("#")
        r, g, b = (
            int(color[0:2], 16) / 255,
            int(color[2:4], 16) / 255,
            int(color[4:6], 16) / 255,
        )
        hue, brightness, saturation = rgb_to_hls(r, g, b)

        for i in range(-n, n + 1):

            # Linear interpolation
            if i > 0:
                adj_brightness = brightness + (1 - brightness) / n * i
            else:
                adj_brightness = brightness + (brightness) / n * i

            r, g, b = hls_to_rgb(hue, adj_brightness, saturation)
            new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

            if brightness > 0.5:
                i *= -1
            series[name][i] = new_color

    return series


def build_style(cp: "Optional[Dict[str, Dict[Union[str, int], str]]]") -> "Style":
    """Create an application style based on the given color palette."""
    if cp is None:
        cp = color_series(fg="#ffffff", bg="#000000", n=20)
    return Style.from_dict(
        {
            # The default style is merged at this point so full styles can be
            # overridden. For example, this allows us to switch off the underline
            # status of cursor-line.
            **dict(default_ui_style().style_rules),
            "default": f"fg:{cp['bg'][0]} bg:{cp['bg'][0]}",
            # Logo
            "logo": "fg:#ff0000",
            # Pattern
            "pattern": f"fg:{config.background_color or cp['fg'][14]}",
            # Chrome
            "chrome": f"fg:{cp['bg'][1]} bg:{cp['bg'][1]}",
            # Statusbar
            "status": f"fg:{cp['fg'][1]} bg:{cp['bg'][1]}",
            "status.field": f"fg:{cp['fg'][2]} bg:{cp['bg'][2]}",
            # Menus & Menu bar
            "menu-bar": f"fg:{cp['fg'][1]} bg:{cp['bg'][1]}",
            "menu-bar.disabled-item": f"fg:{cp['bg'][3]}",
            "menu-bar.selected-item": "reverse",
            "menu-bar.shortcut": f"fg:{cp['fg'][5]}",
            "menu-bar.selected-item menu-bar.shortcut": (
                f"fg:{cp['fg'][1]} bg:{cp['bg'][4]}"
            ),
            "menu-bar.disabled-item menu-bar.shortcut": f"fg:{cp['bg'][3]}",
            "menu": f"bg:{cp['bg'][1]} fg:{cp['fg'][1]}",
            "menu-border": f"fg:{cp['bg'][6]} bg:{cp['bg'][1]}",
            # Buffer
            "line-number": f"fg:{cp['fg'][1]} bg:{cp['bg'][1]}",
            "line-number.current": "bold orange",
            "cursor-line": f"bg:{cp['bg'][1]}",
            "matching-bracket.cursor": "fg:yellow bold",
            "matching-bracket.other": "fg:yellow bold",
            # Cells
            "cell.border": f"fg:{cp['bg'][5]}",
            "cell.border.selected": "fg:#00afff",
            "cell.border.edit": "fg:#00ff00",
            "cell.input.box": f"fg:default bg:{cp['bg'][-2]}",
            "cell.output": "fg:default bg:default",
            "cell.input.prompt": "fg:blue",
            "cell.output.prompt": "fg:red",
            # Scrollbars
            "scrollbar": f"fg:{cp['bg'][15]} bg:{cp['bg'][3]}",
            "scrollbar.background": f"fg:{cp['bg'][15]} bg:{cp['bg'][3]}",
            "scrollbar.arrow": f"fg:{cp['bg'][15]} bg:{cp['bg'][3]}",
            "scrollbar.start": "",
            "scrollbar.button": f"fg:{cp['bg'][15]} bg:{cp['bg'][15]}",
            "scrollbar.end": f"fg:{cp['bg'][3]} bg:{cp['bg'][15]}",
            # Shadows
            "shadow": f"bg:{cp['bg'][9]}",
            "pager shadow": f"bg:{cp['bg'][9]}",
            "cell.input shadow": f"bg:{cp['bg'][9]}",
            "cell.output shadow": f"bg:{cp['bg'][9]}",
            # Dialogs
            "dialog.body": f"fg:{cp['fg']['base']} bg:{cp['bg'][4]}",
            "dialog.body text-area": f"fg:{cp['fg']['base']}",
            "dialog.body scrollbar.button": f"fg:{cp['bg'][5]} bg:{cp['bg'][15]}",
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
            "shortcuts.group": f"bg:{cp['bg'][8]} bold underline",
            "shortcuts.row": f"bg:{cp['bg'][0]} nobold",
            "shortcuts.row alt": f"bg:{cp['bg'][2]}",
            "shortcuts.row key": "bold",
            # Palette
            "palette.item": f"fg:{cp['fg'][1]} bg:{cp['bg'][1]}",
            "palette.item.alt": f"bg:{cp['bg'][3]}",
            "palette.item.selected": "fg:#ffffff bg:#0055ff",
            # Pager
            "pager": f"bg:{cp['bg'][1]}",
            "pager.border": f"fg:{cp['bg'][9]}",
            # Markdown
            "md.code.inline": f"bg:{cp['bg'][3]}",
            "md.code.block": f"bg:{cp['bg'][-4]}",
            "md.code.block.border": f"fg:{cp['bg'][5]}",
            "md.table.border": f"fg:{cp['bg'][8]}",
        }
    )
