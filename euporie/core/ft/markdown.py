"""Contain the browser CSS for formatting markdown."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from prompt_toolkit.filters.utils import _always

from .html import CssSelector

if TYPE_CHECKING:
    from .html import CssSelectors


_MARKDOWN_CSS = {
    _always: {
        (
            (CssSelector(item="h1"),),
            (CssSelector(item="h2"),),
            (CssSelector(item="h3"),),
            (CssSelector(item="h4"),),
            (CssSelector(item="h5"),),
            (CssSelector(item="h6"),),
        ): {
            "text_align": "center",
        },
        ((CssSelector(item="h1"),),): {
            "font_weight": "bold",
            "text_decoration": "underline",
            "border_top_style": "double",
            "border_right_style": "double",
            "border_bottom_style": "double",
            "border_left_style": "double",
            "border_top_width": "0.34em",
            "border_right_width": "0.34em",
            "border_bottom_width": "0.34em",
            "border_left_width": "0.34em",
            "border_top_color": "ansiyellow",
            "border_right_color": "ansiyellow",
            "border_bottom_color": "ansiyellow",
            "border_left_color": "ansiyellow",
            "padding_bottom": "0",
        },
        ((CssSelector(item="h2"),),): {
            "font_weight": "bold",
            "border_top_style": "solid",
            "border_right_style": "solid",
            "border_bottom_style": "solid",
            "border_left_style": "solid",
            "border_top_width": "0.34em",
            "border_right_width": "0.34em",
            "border_bottom_width": "0.34em",
            "border_left_width": "0.34em",
            "border_top_color": "#888888",
            "border_right_color": "#888888",
            "border_bottom_color": "#888888",
            "border_left_color": "#888888",
            "padding_bottom": "0",
        },
        ((CssSelector(item="h3"),),): {
            "font_weight": "bold",
            "font_style": "italic",
            "border_top_style": "solid",
            "border_right_style": "solid",
            "border_bottom_style": "solid",
            "border_left_style": "solid",
            "border_top_width": "0.1em",
            "border_right_width": "0.1em",
            "border_bottom_width": "0.1em",
            "border_left_width": "0.1em",
            "border_top_color": "#888888",
            "border_right_color": "#888888",
            "border_bottom_color": "#888888",
            "border_left_color": "#888888",
            "margin_left": "auto",
            "margin_right": "auto",
            "padding_top": "0",
            "padding_right": "1em",
            "padding_bottom": "0",
            "padding_left": "1em",
        },
        ((CssSelector(item="h4"),),): {
            "text_weight": "bold",
            "text_decoration": "underline",
            "border_bottom_color": "#888888",
            "margin_top": "1rem",
            "margin_bottom": "1rem",
        },
        ((CssSelector(item="h5"),),): {
            "font_weight": "bold",
            "border_bottom_color": "#888888",
            "margin_top": "1rem",
            "margin_bottom": "1rem",
        },
        ((CssSelector(item="h6"),),): {
            "font_style": "italic",
            "border_bottom_color": "#888888",
            "margin_top": "1rem",
            "margin_bottom": "1rem",
        },
        (
            (
                CssSelector(item="ol"),
                CssSelector(item="li"),
                CssSelector(item="::marker"),
            ),
        ): {"color": "ansicyan"},
        (
            (
                CssSelector(item="ul"),
                CssSelector(item="li"),
                CssSelector(item="::marker"),
            ),
        ): {"color": "ansiyellow"},
        ((CssSelector(item="blockquote"),),): {
            "margin_top": "1em",
            "margin_bottom": "1em",
            "padding_left": "1em",
            "border_left_width": "thick",
            "border_left_style": "solid",
            "border_left_color": "darkmagenta",
        },
        ((CssSelector(item=".block"),),): {"display": "block"},
        ((CssSelector(item="td"),),): {
            "display": "table-cell",
            "border_top_style": "solid",
            "border_right_style": "solid",
            "border_bottom_style": "solid",
            "border_left_style": "solid",
            "border_top_width": "0.1em",
            "border_right_width": "0.1em",
            "border_bottom_width": "0.1em",
            "border_left_width": "0.1em",
            "padding_left": "1em",
            "padding_right": "1em",
            # "_pt_class": "markdown,table,border",
        },
        ((CssSelector(item="th"),),): {
            "display": "table-cell",
            "border_top_style": "solid",
            "border_right_style": "solid",
            "border_bottom_style": "solid",
            "border_left_style": "solid",
            "border_top_width": "0.34em",
            "border_right_width": "0.34em",
            "border_bottom_width": "0.34em",
            "border_left_width": "0.34em",
            "padding_left": "1em",
            "padding_right": "1em",
            "font_weight": "bold",
            # "_pt_class": "markdown,table,border",
        },
        ((CssSelector(item="code"),),): {
            "display": "inline",
            "_pt_class": "markdown,code",
        },
        ((CssSelector(item=".math"),),): {"text_transform": "latex"},
        ((CssSelector(item=".math.block"),),): {
            "text_align": "center",
        },
        (
            (
                CssSelector(item="pre"),
                CssSelector(comb=">", item="code"),
            ),
        ): {
            "display": "block",
            "border_top_style": "solid",
            "border_top_width": "1px",
            "border_right_style": "solid",
            "border_right_width": "1px",
            "border_bottom_style": "solid",
            "border_bottom_width": "1px",
            "border_left_style": "solid",
            "border_left_width": "1px",
            "_pt_class": "markdown,code,block",
        },
        (
            (
                CssSelector(item="pre"),
                CssSelector(comb=">", item="code"),
                CssSelector(item="*"),
            ),
        ): {
            "pt_class": "markdown,code,block",
        },
        ((CssSelector(item="img"),), (CssSelector(item="svg"),)): {
            "display": "inline-block",
            "overflow_x": "hidden",
            "overflow_y": "hidden",
            "vertical_align": "middle",
        },
    }
}


@cache
def get_markdown_file_css() -> CssSelectors:
    """Apply margins to the root - used if rendering a full markdown file."""
    return {
        _always: {
            **_MARKDOWN_CSS[_always],
            ((CssSelector(item="::root"),),): {
                "max_width": "100em",
                "margin_left": "auto",
                "margin_right": "auto",
            },
        }
    }
