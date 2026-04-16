import logging
import re
from collections.abc import Mapping
from html.parser import HTMLParser
from pathlib import Path
from string import Formatter
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict, overload

from apptk.border import (
    DiLineStyle,
    DoubleLine,
    FullDottedLine,
    FullLine,
    GridStyle,
    InvisibleLine,
    LowerLeftEighthLine,
    LowerLeftHalfDottedLine,
    LowerLeftHalfLine,
    NoLine,
    ThickDoubleDashedLine,
    ThickLine,
    ThickQuadrupleDashedLine,
    ThinDoubleDashedLine,
    ThinLine,
    ThinQuadrupleDashedLine,
    UpperRightEighthLine,
    UpperRightHalfDottedLine,
    UpperRightHalfLine,
)
from apptk.convert.datum import Datum
from apptk.data_structures import DiBool, DiInt, DiStr
from apptk.enums import HorizontalAlign
from apptk.filters.utils import to_filter
from apptk.utils import Event
from upath import UPath

from .base import FormattedText, StyleAndTextTuples

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator

    from apptk.filters.base import Filter, FilterOrBool
    from apptk.formatted_text.base import StyleAndTextTuples
    from apptk.key_binding.key_bindings import NotImplementedOrNone
    from apptk.mouse_events import MouseEvent
    from fsspec.spec import AbstractFileSystem

FORMATTER = HTMLFormatter()
log = logging.getLogger(__name__)
always = to_filter(True)
never = to_filter(False)
sub_trans = str.maketrans(
    "0123456789+-=()aeijoruvxβγρφχ",
    "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑᵢⱼₒᵣᵤᵥₓᵦᵧᵨᵩᵪ",
)
sup_trans = str.maketrans(
    "0123456789+-=()abcdefghijklmnoprstuvwxyzABDEGHIJKLMNOPRTUVWαβγδ∊θιΦφχ",
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂᵅᵝᵞᵟᵋᶿᶥᶲᵠᵡ",
)
CssRuleEntry = tuple[tuple[CssSelector, ...], dict[str, str]]
CssSelectors = dict[Filter, CssRuleSet]
_COLOR_RE = re.compile(r"#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})")
_SELECTOR_RE = re.compile(
    r"""
        (?:^|\s*(?P<comb>[\s>+~]|(?=::))\s*)
        (?P<item>(?:::)?[^\s>+~:[\]]+)?
        (?P<attr>\[[^\s>+~]+\])?
        (?P<pseudo>\:[^:][^\s>+~]*)?
    """,
    re.VERBOSE,
)
_AT_RULE_RE = re.compile(
    r"""
    (
        @(?:color-profile|container|counter-style|document|font-face|font-feature-values|font-palette-values|keyframes|layer|media|page|supports)
        [^@{]+
        (?:
            {[^{}]*}
            |
            {(?:[^{]+?{(?:[^{}]|{[^}]+?})+?}\s*)*?}
        )
        |
        @(?:charset|import|namespace)[^;]*;
    )
    """,
    re.VERBOSE,
)
_NESTED_AT_RULE_RE = re.compile(
    r"@(?P<identifier>[\w-]+)\s*(?P<rule>[^{]*?)\s*{\s*(?P<part>.*)\s*}"
)
_MEDIA_QUERY_TARGET_RE = re.compile(
    r"""
        (?:
            (?P<invert>not\s+)?
            (?:only\s+)?  # Ignore this
            (?P<type>all|print|screen) |
            (?:\((?P<feature>[^)]+)\))
        )
    """,
    re.VERBOSE,
)
_GRID_TEMPLATE_RE = re.compile(
    r"""
        (
            none|auto|(?:min|max)-content
          | (?<!-)\d+(?:\.\d+)?(?:\w{1,4}|%)
          | minmax\(\s*[^,]+?\s*,\s*[^)]+?\s*\)
          | repeat\(\s*(?:\d+|auto-fill|auto-fit)\s*,\s*[^)]+?\s*\)
          | [^\s]+
        )
        (?=\s+|$)
    """,
    re.MULTILINE | re.VERBOSE,
)
_GRID_TEMPLATE_REPEAT_RE = re.compile(
    r"repeat\(\s*(?P<count>\d+)\s*,\s*(?P<value>[^)]+?)\s*\)"
)
_CSS_COMMENT_RE = re.compile(r"/\*[^*]*\*+(?:[^/*][^*]*\*+)*/")
_MATHJAX_TAG_RE = re.compile(
    r"""
        ^(?P<beginning>.*?)
        (?P<middle>
            \\\[(?P<display_bracket>.*?)\\\]
            |
            \\\((?P<inline_bracket>.*?)\\\)
            |
            \$\$(?P<display_dollar>.*?)\$\$
            |
            \$(?P<inline_dollar>.*?)(?: \$(?=\$\$) | (?<!\$)\$(?!\$) )
        )
        (?P<end>.*)$
    """,
    re.MULTILINE | re.VERBOSE,
)
_VOID_ELEMENTS = (
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
    # SVG
    "circle",
    "ellipse",
    "use",
    "path",
)
_LIST_STYLE_TYPES = {
    "none": "",
    "disc": "•",
    "circle": "○",
    "square": "■",
    "triangle": "▲",
    "disclosure-open": "▼",
    "disclosure-closed": "▶",
}
_BORDER_WIDTHS = {
    "thin": 0.1,
    "medium": 0.15,
    "thick": 0.3,
}
_BORDER_WIDTH_STYLES = {
    0: (
        _ := {
            "none": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "hidden": DiLineStyle(
                InvisibleLine, InvisibleLine, InvisibleLine, InvisibleLine
            ),
            "dotted": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "dashed": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "solid": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "double": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "groove": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "inset": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "outset": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "ridge": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
        }
    ),
    0.00001: (
        _ := {
            **_,
            "dotted": DiLineStyle(
                ThinQuadrupleDashedLine,
                ThinQuadrupleDashedLine,
                ThinQuadrupleDashedLine,
                ThinQuadrupleDashedLine,
            ),
            "dashed": DiLineStyle(
                ThinDoubleDashedLine,
                ThinDoubleDashedLine,
                ThinDoubleDashedLine,
                ThinDoubleDashedLine,
            ),
            "solid": DiLineStyle(ThinLine, ThinLine, ThinLine, ThinLine),
            "double": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "inset": DiLineStyle(
                LowerLeftEighthLine,
                LowerLeftEighthLine,
                UpperRightEighthLine,
                UpperRightEighthLine,
            ),
            "outset": DiLineStyle(
                UpperRightEighthLine,
                UpperRightEighthLine,
                LowerLeftEighthLine,
                LowerLeftEighthLine,
            ),
            "ridge": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "groove": DiLineStyle(ThinLine, ThinLine, ThinLine, ThinLine),
        }
    ),
    0.2: (
        _ := {
            **_,
            "dotted": DiLineStyle(
                ThickQuadrupleDashedLine,
                ThickQuadrupleDashedLine,
                ThickQuadrupleDashedLine,
                ThickQuadrupleDashedLine,
            ),
            "dashed": DiLineStyle(
                ThickDoubleDashedLine,
                ThickDoubleDashedLine,
                ThickDoubleDashedLine,
                ThickDoubleDashedLine,
            ),
            "solid": DiLineStyle(ThickLine, ThickLine, ThickLine, ThickLine),
            "double": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "ridge": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "groove": DiLineStyle(ThickLine, ThickLine, ThickLine, ThickLine),
        }
    ),
    0.5: (
        _ := {
            **_,
            "solid": DiLineStyle(
                UpperRightHalfLine,
                UpperRightHalfLine,
                LowerLeftHalfLine,
                LowerLeftHalfLine,
            ),
        }
    ),
    1: (
        _ := {
            **_,
            "solid": DiLineStyle(
                UpperRightHalfLine, FullLine, LowerLeftHalfLine, FullLine
            ),
            "double": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "dotted": DiLineStyle(
                UpperRightHalfDottedLine,
                FullDottedLine,
                LowerLeftHalfDottedLine,
                FullDottedLine,
            ),
        }
    ),
    2: (
        _ := {
            **_,
            "solid": DiLineStyle(FullLine, FullLine, FullLine, FullLine),
        }
    ),
}
_TEXT_ALIGNS = {
    "left": HorizontalAlign.LEFT,
    "center": HorizontalAlign.CENTER,
    "right": HorizontalAlign.RIGHT,
}
_VERTICAL_ALIGNS = {
    "top": 0,
    "middle": 0.5,
    "baseline": 1,
}
_HERITABLE_PROPS = {
    "color",
    "font_style",
    "font_size",
    "font_weight",
    "text_transform",
    "text_decoration",
    "text_align",
    "vertical_align",
    "visibility",
    "white_space",
    "list_style_type",
    "list_style_position",
    "_pt_class",
}
_DEFAULT_ELEMENT_CSS = {
    # Display
    "display": "block",
    "float": "none",
    "visibility": "visible",
    "opacity": "1.0",
    "overflow_x": "visible",
    "overflow_y": "visible",
    "vertical_align": "baseline",
    # Text
    "color": "default",
    "background_color": "default",
    "font_style": "normal",
    "font_size": "1em",
    "font_weight": "normal",
    "text_decoration": "none",
    "text_transform": "none",
    "text_align": "left",
    "white_space": "normal",
    # Box
    "padding_top": "0",
    "padding_left": "0",
    "padding_bottom": "0",
    "padding_right": "0",
    "margin_top": "0",
    "margin_left": "0",
    "margin_bottom": "0",
    "margin_right": "0",
    "border_top_width": "0",
    "border_left_width": "0",
    "border_bottom_width": "0",
    "border_right_width": "0",
    "border_top_style": "none",
    "border_left_style": "none",
    "border_bottom_style": "none",
    "border_right_style": "none",
    "border_top_color": "",
    "border_left_color": "",
    "border_bottom_color": "",
    "border_right_color": "",
    # Flex
    "flex_direction": "row",
    "align_content": "normal",
    # Position
    "position": "static",
    "top": "unset",
    "right": "unset",
    "bottom": "unset",
    "left": "unset",
    "z_index": "0",
    # Lists
    "list_style_type": "none",
    "list_style_position": "inside",
}
_BROWSER_CSS: dict[Filter, CssRuleSet] = {
    always: CssRuleSet(
        {
            # Set body background to white
            ((CssSelector(item="body"),),): {"background_color": "#FFFFFF"},
            # Non-rendered elements
            (
                (CssSelector(item="head"),),
                (CssSelector(item="base"),),
                (CssSelector(item="command"),),
                (CssSelector(item="link"),),
                (CssSelector(item="meta"),),
                (CssSelector(item="noscript"),),
                (CssSelector(item="script"),),
                (CssSelector(item="style"),),
                (CssSelector(item="title"),),
                (CssSelector(item="option"),),
                (CssSelector(item="input", attr="[type=hidden]"),),
            ): {"display": "none"},
            # Inline elements
            (
                (CssSelector(item="::before"),),
                (CssSelector(item="::after"),),
                (CssSelector(item="::text"),),
                (CssSelector(item="abbr"),),
                (CssSelector(item="acronym"),),
                (CssSelector(item="audio"),),
                (CssSelector(item="bdi"),),
                (CssSelector(item="bdo"),),
                (CssSelector(item="big"),),
                (CssSelector(item="br"),),
                (CssSelector(item="canvas"),),
                (CssSelector(item="data"),),
                (CssSelector(item="datalist"),),
                (CssSelector(item="embed"),),
                (CssSelector(item="iframe"),),
                (CssSelector(item="label"),),
                (CssSelector(item="map"),),
                (CssSelector(item="meter"),),
                (CssSelector(item="object"),),
                (CssSelector(item="output"),),
                (CssSelector(item="picture"),),
                (CssSelector(item="progress"),),
                (CssSelector(item="q"),),
                (CssSelector(item="ruby"),),
                (CssSelector(item="select"),),
                (CssSelector(item="slot"),),
                (CssSelector(item="small"),),
                (CssSelector(item="span"),),
                (CssSelector(item="template"),),
                (CssSelector(item="textarea"),),
                (CssSelector(item="time"),),
                (CssSelector(item="tt"),),
                (CssSelector(item="video"),),
                (CssSelector(item="wbr"),),
            ): {"display": "inline"},
            # Formatted inlines
            ((CssSelector(item="a"),),): {
                "display": "inline",
                "text_decoration": "underline",
                "color": "#0000FF",
            },
            ((CssSelector(item="b"),), (CssSelector(item="strong"),)): {
                "display": "inline",
                "font_weight": "bold",
            },
            ((CssSelector(item="blink"),),): {
                "display": "inline",
                "text_decoration": "blink",
            },
            (
                (CssSelector(item="cite"),),
                (CssSelector(item="dfn"),),
                (CssSelector(item="em"),),
                (CssSelector(item="i"),),
                (CssSelector(item="var"),),
            ): {"display": "inline", "font_style": "italic"},
            ((CssSelector(item="code"),),): {
                "display": "inline",
            },
            ((CssSelector(item="del"),), (CssSelector(item="s"),)): {
                "display": "inline",
                "text_decoration": "line-through",
            },
            (
                (CssSelector(item="img", attr="[width=0]"),),
                (CssSelector(item="img", attr="[height=0]"),),
                (CssSelector(item="svg", attr="[width=0]"),),
                (CssSelector(item="svg", attr="[height=0]"),),
            ): {"display": "none"},
            ((CssSelector(item="img"),), (CssSelector(item="svg"),)): {
                "display": "inline-block",
                "overflow_x": "hidden",
                "overflow_y": "hidden",
            },
            ((CssSelector(item="ins"),), (CssSelector(item="u"),)): {
                "display": "inline",
                "text_decoration": "underline",
            },
            ((CssSelector(item="kbd"),),): {
                "display": "inline",
                "background_color": "#333344",
                "color": "#FFFFFF",
            },
            ((CssSelector(item="mark"),),): {
                "display": "inline",
                "color": "black",
                "background_color": "#FFFF00",
            },
            ((CssSelector(item="samp"),),): {
                "display": "inline",
                "background_color": "#334433",
                "color": "#FFFFFF",
            },
            ((CssSelector(item="sub"),),): {
                "display": "inline",
                "vertical_align": "sub",
            },
            ((CssSelector(item="sup"),),): {
                "display": "inline",
                "vertical_align": "super",
            },
            (
                (
                    CssSelector(item="q"),
                    CssSelector(item="::before"),
                ),
            ): {"content": "'“'"},
            (
                (
                    CssSelector(item="q"),
                    CssSelector(item="::after"),
                ),
            ): {"content": "'”'"},
            # Images
            (
                (CssSelector(item="img", attr="[_missing]"),),
                (CssSelector(item="svg", attr="[_missing]"),),
            ): {
                "border_top_style": "solid",
                "border_right_style": "solid",
                "border_bottom_style": "solid",
                "border_left_style": "solid",
                "border_top_width": "1px",
                "border_right_width": "1px",
                "border_bottom_width": "1px",
                "border_left_width": "1px",
                "border_top_color": "#888888",
                "border_right_color": "#888888",
                "border_bottom_color": "#888888",
                "border_left_color": "#888888",
            },
            # Alignment
            ((CssSelector(item="center"),), (CssSelector(item="caption"),)): {
                "text_align": "center",
                "display": "block",
            },
            # Tables
            ((CssSelector(item="table"),),): {
                "display": "table",
                "border_collapse": "collapse",
            },
            (
                (CssSelector(item="td"),),
                (CssSelector(item="th"),),
            ): {
                "border_top_width": "0px",
                "border_right_width": "0px",
                "border_bottom_width": "0px",
                "border_left_width": "0px",
            },
            ((CssSelector(item="td"),),): {
                "display": "table-cell",
                "text_align": "unset",
            },
            ((CssSelector(item="th"),),): {
                "display": "table-cell",
                "font_weight": "bold",
                "text_align": "center",
            },
            # Forms
            ((CssSelector(item="input"),),): {
                "display": "inline-block",
                "white_space": "pre",
                "color": "#000000",
                "border_top_style": "inset",
                "border_right_style": "inset",
                "border_bottom_style": "inset",
                "border_left_style": "inset",
                "border_top_width": "2px",
                "border_right_width": "2px",
                "border_bottom_width": "2px",
                "border_left_width": "2px",
                "vertical_align": "middle",
            },
            ((CssSelector(item="input", attr="[type=text]"),),): {
                "background_color": "#FAFAFA",
                "border_top_color": "#606060",
                "border_right_color": "#E9E7E3",
                "border_bottom_color": "#E9E7E3",
                "border_left_color": "#606060",
                "overflow_x": "hidden",
            },
            (
                (CssSelector(item="input", attr="[type=button]"),),
                (CssSelector(item="input", attr="[type=submit]"),),
                (CssSelector(item="input", attr="[type=reset]"),),
            ): {
                "background_color": "#d4d0c8",
                "border_right": "#606060",
                "border_bottom": "#606060",
                "border_left": "#ffffff",
                "border_top": "#ffffff",
            },
            ((CssSelector(item="button"),),): {
                "display": "inline-block",
                "color": "#000000",
                "border_top_style": "outset",
                "border_right_style": "outset",
                "border_bottom_style": "outset",
                "border_left_style": "outset",
                "border_top_width": "2px",
                "border_right_width": "2px",
                "border_bottom_width": "2px",
                "border_left_width": "2px",
                "background_color": "#d4d0c8",
                "border_right": "#606060",
                "border_bottom": "#606060",
                "border_left": "#ffffff",
                "border_top": "#ffffff",
            },
            # Headings
            ((CssSelector(item="h1"),),): {
                "font_weight": "bold",
                "text_decoration": "underline",
                "border_bottom_style": "solid",
                "border_bottom_width": "thick",
                "padding_bottom": "2rem",
                "margin_top": "2rem",
                "margin_bottom": "2em",
            },
            ((CssSelector(item="h2"),),): {
                "font_weight": "bold",
                "border_bottom_style": "double",
                "border_bottom_width": "thick",
                "padding_bottom": "1.5rem",
                "margin_top": "1.5rem",
                "margin_bottom": "1.5rem",
            },
            ((CssSelector(item="h3"),),): {
                "font_weight": "bold",
                "font_style": "italic",
                "border_bottom_style": ":lower-left",
                "border_bottom_width": "thin",
                "padding_top": "1rem",
                "padding_bottom": "1rem",
                "margin_bottom": "1.5rem",
            },
            ((CssSelector(item="h4"),),): {
                "text_decoration": "underline",
                "border_bottom_style": "solid",
                "border_bottom_width": "thin",
                "padding_top": "1rem",
                "padding_bottom": "1rem",
                "margin_bottom": "1.5rem",
            },
            ((CssSelector(item="h5"),),): {
                "border_bottom_style": "dashed",
                "border_bottom_width": "thin",
                "margin_bottom": "1.5rem",
            },
            ((CssSelector(item="h6"),),): {
                "font_style": "italic",
                "border_bottom_style": "dotted",
                "border_bottom_width": "thin",
                "margin_bottom": "1.5rem",
            },
            # Misc blocks
            ((CssSelector(item="blockquote"),),): {
                "margin_top": "1em",
                "margin_bottom": "1em",
                "margin_right": "2em",
                "margin_left": "2em",
            },
            ((CssSelector(item="hr"),),): {
                "margin_top": "1rem",
                "margin_bottom": "1rem",
                "border_top_width": "thin",
                "border_top_style": "solid",
                "border_top_color": "ansired",
                "width": "100%",
            },
            ((CssSelector(item="p"),),): {"margin_top": "1em", "margin_bottom": "1em"},
            ((CssSelector(item="pre"),),): {
                "margin_top": "1em",
                "margin_bottom": "1em",
                "white_space": "pre",
            },
            # Lists
            ((CssSelector(item="::marker"),),): {
                "display": "inline-block",
                "padding_right": "1em",
                "text_align": "right",
            },
            ((CssSelector(item="ol"),),): {
                "list_style_type": "decimal",
                "list_style_position": "outside",
                "padding_left": "4em",
                "margin_top": "1em",
                "margin_bottom": "1em",
            },
            (
                (CssSelector(item="ul"),),
                (CssSelector(item="menu"),),
                (CssSelector(item="dir"),),
            ): {
                "list_style_type": "disc",
                "list_style_position": "outside",
                "padding_left": "3em",
                "margin_top": "1em",
                "margin_bottom": "1em",
            },
            (
                (CssSelector(item="dir"), CssSelector(item="dir")),
                (CssSelector(item="dir"), CssSelector(item="menu")),
                (CssSelector(item="dir"), CssSelector(item="ul")),
                (CssSelector(item="ol"), CssSelector(item="dir")),
                (CssSelector(item="ol"), CssSelector(item="menu")),
                (CssSelector(item="ol"), CssSelector(item="ul")),
                (CssSelector(item="menu"), CssSelector(item="dir")),
                (CssSelector(item="menu"), CssSelector(item="menu")),
                (CssSelector(item="ul"), CssSelector(item="dir")),
                (CssSelector(item="ul"), CssSelector(item="menu")),
                (CssSelector(item="ul"), CssSelector(item="ul")),
            ): {
                "margin_top": "0em",
                "margin_bottom": "0em",
                "list_style_type": "circle",
            },
            (
                (CssSelector(item="dir"), CssSelector(item="dl")),
                (CssSelector(item="dir"), CssSelector(item="ol")),
                (CssSelector(item="dl"), CssSelector(item="dir")),
                (CssSelector(item="dl"), CssSelector(item="dl")),
                (CssSelector(item="dl"), CssSelector(item="ol")),
                (CssSelector(item="dl"), CssSelector(item="menu")),
                (CssSelector(item="dl"), CssSelector(item="ul")),
                (CssSelector(item="ol"), CssSelector(item="dl")),
                (CssSelector(item="ol"), CssSelector(item="ol")),
                (CssSelector(item="menu"), CssSelector(item="dl")),
                (CssSelector(item="menu"), CssSelector(item="ol")),
                (CssSelector(item="ul"), CssSelector(item="dl")),
                (CssSelector(item="ul"), CssSelector(item="ol")),
            ): {"margin_top": "0em", "margin_bottom": "0em"},
            ((CssSelector(item="menu"), CssSelector(item="ul")),): {
                "list_style_type": "circle",
                "margin_top": "0em",
                "margin_bottom": "0em",
            },
            (
                (
                    CssSelector(item="dir"),
                    CssSelector(item="dir"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="dir"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="dir"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="menu"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="menu"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="menu"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="ol"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="ol"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="ol"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="ul"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="ul"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="dir"),
                    CssSelector(item="ul"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="dir"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="dir"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="dir"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="menu"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="menu"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="menu"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="ol"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="ol"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="ol"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="ul"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="ul"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="menu"),
                    CssSelector(item="ul"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="dir"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="dir"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="dir"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="menu"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="menu"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="menu"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="ol"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="ol"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="ol"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="ul"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="ul"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="ol"),
                    CssSelector(item="ul"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="dir"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="dir"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="dir"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="menu"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="menu"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="menu"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="ol"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="ol"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="ol"),
                    CssSelector(item="ul"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="ul"),
                    CssSelector(item="dir"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="ul"),
                    CssSelector(item="menu"),
                ),
                (
                    CssSelector(item="ul"),
                    CssSelector(item="ul"),
                    CssSelector(item="ul"),
                ),
            ): {"list_style_type": "square"},
            ((CssSelector(item="li"),),): {"display": "list-item"},
            # Details & summary
            ((CssSelector(item="details"), CssSelector(item="summary")),): {
                "display": "list-item",
                "list_style_type": "disclosure-closed",
                "list_style_position": "inside",
            },
            (
                (
                    CssSelector(item="details", attr="[open]"),
                    CssSelector(item="summary"),
                ),
            ): {
                "list_style_type": "disclosure-open",
                "display": "list-item",
            },
        },
    )
}
NodeAttrs = TypedDict(
    "NodeAttrs",
    {
        "class": str,
        "data": str | bytes,
        "href": str,
        "rel": str,
        "as": str,
        "src": str,
        "colspan": int,
        "size": str,
        "id": str,
        "type": str,
        "color": str,
        "bgcolor": str,
        "height": str,
        "width": str,
        "border": str,
        "alt": str,
        "title": str,
        "linkpath": Path,
        "style": str,
        "halign": str,
        "valign": str,
    },
    total=False,
)

__all__ = [
    "HTML",
]

def html_escape(text: object) -> str: ...
def match_css_selector(
    selector: str,
    attrs: str,
    pseudo: str,
    element_name: str,
    is_first_child_element: bool,
    is_last_child_element: bool,
    sibling_element_index: int | None,
    **element_attrs: Any,
) -> bool: ...
def try_eval(value: str, default: Any = None) -> Any: ...
def get_integer(value: str) -> int | None: ...
def get_color(value: str) -> str: ...
def css_dimension(
    value: str,
    vertical: bool = False,
    available: float | int | None = None,
) -> float | None: ...
def parse_css_content(content: str) -> dict[str, str]: ...
def selector_specificity(
    selector_parts: tuple[CssSelector, ...],
) -> tuple[int, int, int]: ...

class HTML:
    value: str
    formatted_text: FormattedText
    def __init__(self, value: str) -> None: ...
    def __repr__(self) -> str: ...
    def __pt_formatted_text__(self) -> StyleAndTextTuples: ...
    def format(self, *args: object, **kwargs: object) -> HTML: ...
    def __mod__(self, value: object) -> HTML: ...

class HTMLFormatter(Formatter):
    def format_field(self, value: object, format_spec: str) -> str: ...

class CssSelector(NamedTuple):
    comb: str | None = None
    item: str | None = None
    attr: str | None = None
    pseudo: str | None = None
    def __repr__(self) -> str: ...

class CssRuleSet(dict[tuple[tuple[CssSelector, ...], ...], dict[str, str]]):
    by_tag: dict[str, list[CssRuleEntry]]
    by_id: dict[str, list[CssRuleEntry]]
    by_class: dict[str, list[CssRuleEntry]]
    by_attr: dict[str, list[CssRuleEntry]]
    by_attr_value: dict[tuple[str, str], list[CssRuleEntry]]
    universal: list[CssRuleEntry]
    def __init__(
        self,
        data: dict[tuple[tuple[CssSelector, ...], ...], dict[str, str]] | None = None,
    ) -> None: ...
    def __setitem__(
        self,
        selectors: tuple[tuple[CssSelector, ...], ...],
        style: dict[str, str],
    ) -> None: ...
    def _index_selector(
        self,
        selector_parts: tuple[CssSelector, ...],
        rule: dict[str, str],
    ) -> None: ...
    def get_potential_rules(
        self,
        tag_name: str,
        element_id: str | None,
        class_names: list[str],
        element_attrs: dict[str, str] | None = None,
    ) -> list[CssRuleEntry]: ...

class Direction(NamedTuple):
    x: bool = False
    y: bool = False

class Theme(Mapping):
    element: Node
    parent_theme: Theme | None
    available_width: int
    available_height: int
    rendered_width = 0
    rendered_height = 0
    def __init__(
        self,
        element: Node,
        parent_theme: Theme | None,
        available_width: int = 0,
        available_height: int = 0,
    ) -> None: ...
    def reset(self) -> None: ...
    def theme(self) -> dict[str, str]: ...
    def update_space(self, available_width: int, available_height: int) -> None: ...
    def update_size(self, rendered_width: int, rendered_height: int) -> None: ...
    def inherited_browser_css_theme(self) -> dict[str, str]: ...
    def inherited_theme(self) -> dict[str, str]: ...
    def style_attribute_theme(self) -> dict[str, str]: ...
    def attributes_theme(self) -> dict[str, str]: ...
    def _css_theme(self, rulesets: dict[Filter, CssRuleSet]) -> dict[str, str]: ...
    def browser_css_theme(self) -> dict[str, str]: ...
    def dom_css_theme(self) -> dict[str, str]: ...
    def d_block(self) -> bool: ...
    def d_inline(self) -> bool: ...
    def d_inline_block(self) -> bool: ...
    def d_flex(self) -> bool: ...
    def d_grid(self) -> bool: ...
    def d_image(self) -> bool: ...
    def d_table(self) -> bool: ...
    def d_table_cell(self) -> bool: ...
    def d_list_item(self) -> bool: ...
    def d_blocky(self) -> bool: ...
    def include(self) -> bool: ...
    def floated(self) -> str | None: ...
    @property
    def min_width(self) -> int | None: ...
    @property
    def width(self) -> int | None: ...
    @property
    def max_width(self) -> int | None: ...
    def min_content_width(self) -> int: ...
    def max_content_width(self) -> int: ...
    @property
    def content_width(self) -> int: ...
    @property
    def min_height(self) -> int | None: ...
    @property
    def height(self) -> int | None: ...
    @property
    def max_height(self) -> int | None: ...
    @property
    def content_height(self) -> int: ...
    def padding(self) -> DiInt: ...
    def base_margin(self) -> DiInt: ...
    def margin(self) -> DiInt: ...
    def block_align(self) -> HorizontalAlign: ...
    def border_style(self) -> DiStr: ...
    def border_visibility(self) -> DiBool: ...
    def border_line(self) -> DiLineStyle: ...
    def border_grid(self) -> GridStyle: ...
    def border_collapse(self) -> bool: ...
    def color(self) -> str: ...
    def background_color(self) -> str: ...
    def style(self) -> str: ...
    async def text_transform(self, value: str) -> str: ...
    def preformatted(self) -> bool: ...
    def text_align(self) -> HorizontalAlign: ...
    def vertical_align(self) -> float: ...
    def list_style_type(self) -> str: ...
    def list_style_position(self) -> str: ...
    def font_size(self) -> float | int: ...
    def z_index(self) -> int: ...
    def position(self) -> DiInt: ...
    def anchors(self) -> DiBool: ...
    def skip(self) -> bool: ...
    def hidden(self) -> bool: ...
    def in_flow(self) -> bool: ...
    def container_theme(self) -> Theme: ...
    def gap(self) -> tuple[int, int]: ...
    def grid_template(self) -> list[list[str]]: ...
    def grid_column_start(self) -> int | None: ...
    def grid_column_span(self) -> int: ...
    def grid_area(self) -> str | None: ...
    def grid_areas(self) -> dict[int, dict[int, str]]: ...
    def order(self) -> tuple[tuple[bool, int], int, tuple[bool, int]]: ...
    def latex(self) -> bool: ...
    def __getitem__(self, key: str) -> Any: ...
    def __iter__(self) -> Iterator: ...
    def __len__(self) -> int: ...

class Node:
    dom: RichHTML
    name: str
    parent: Node | None
    _text: str
    attrs: NodeAttrs
    contents: list[Node]
    closed = False
    marker: Node | None
    def __init__(
        self,
        dom: RichHTML,
        name: str,
        parent: Node | None,
        text: str = "",
        attrs: NodeAttrs | None = None,
        contents: list[Node] | None = None,
    ) -> None: ...
    def theme(self) -> Theme: ...
    def reset(self) -> None: ...
    def _outer_html(self, d: int = 0, attrs: bool = True) -> str: ...
    def __lt__(self, other: Node) -> bool: ...
    def preceding_text(self) -> str: ...
    def text(self) -> str: ...
    def find_all(self, tag: str, recursive: bool = False) -> Iterator[Node]: ...
    @property
    def descendents(self) -> Generator[Node]: ...
    @property
    def renderable_descendents(self) -> Generator[Node]: ...
    def parents(self) -> list[Node]: ...
    def is_first_child_node(self) -> bool: ...
    def is_last_child_node(self) -> bool: ...
    @property
    def child_elements(self) -> Generator[Node]: ...
    def first_child_element(self) -> Node | None: ...
    def last_child_element(self) -> Node | None: ...
    def is_first_child_element(self) -> bool: ...
    def is_last_child_element(self) -> bool: ...
    def sibling_element_index(self) -> int | None: ...
    def sibling_flow_index(self) -> int | None: ...
    def prev_node(self) -> Node | None: ...
    def next_node(self) -> Node | None: ...
    def prev_node_in_flow(self) -> Node | None: ...
    def next_node_in_flow(self) -> Node | None: ...
    def prev_element(self) -> Node | None: ...
    def next_element(self) -> Node | None: ...
    def __repr__(self, d: int = 0) -> str: ...

class CustomHTMLParser(HTMLParser):
    soup: Node
    curr: Node
    dom: RichHTML
    def __init__(self, dom: RichHTML) -> None: ...
    def parse(self, markup: str) -> Node: ...
    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None: ...
    def autoclose(self) -> None: ...
    def handle_data(self, data: str) -> None: ...
    def handle_endtag(self, tag: str) -> None: ...

class RichHTML:
    render_ul_content = render_ol_content
    value = value.strip()
    base: UPath
    title = ""
    browser_css = (
        {filter: CssRuleSet(rules) for filter, rules in browser_css.items()}
        if browser_css
        else _BROWSER_CSS
    )
    css: dict[Filter, CssRuleSet]
    mathjax: FilterOrBool
    defer_assets: bool
    render_count = 0
    width: int | None
    height: int | None
    fill: bool
    collapse_root_margin: bool
    paste_fixed: bool
    graphic_data: set[Datum]
    mouse_handler: Callable[[Node, MouseEvent], NotImplementedOrNone] | None
    formatted_text: StyleAndTextTuples
    floats: dict[tuple[int, DiBool, DiInt], StyleAndTextTuples]
    fixed: dict[tuple[int, DiBool, DiInt], StyleAndTextTuples]
    fixed_mask: StyleAndTextTuples
    on_update: Event
    on_change: Event
    _dom_processed = False
    _assets_loaded = False
    _url_cbs: dict[Path, Callable[[Any], None]]
    _url_fs_map: dict[Path, AbstractFileSystem]
    def __init__(
        self,
        value: str,
        base: Path | str | None = None,
        width: int | None = None,
        height: int | None = None,
        collapse_root_margin: bool = False,
        fill: bool = True,
        css: dict[Filter, CssRuleSet] | None = None,
        browser_css: dict[Filter, CssRuleSet] | None = None,
        mathjax: FilterOrBool = True,
        mouse_handler: Callable[[Node, MouseEvent], NotImplementedOrNone] | None = None,
        paste_fixed: bool = True,
        defer_assets: bool = False,
        on_update: Callable[[RichHTML], None] | None = None,
        on_change: Callable[[RichHTML], None] | None = None,
    ) -> None: ...
    def parser(self) -> CustomHTMLParser: ...
    def soup(self) -> Node: ...
    def parse_media_condition(self, condition: str) -> Filter: ...
    def parse_style_sheet(self, css_str: str, condition: Filter = always) -> None: ...
    def process_dom(self) -> None: ...
    async def load_assets(self) -> None: ...
    def render(self, width: int | None, height: int | None) -> StyleAndTextTuples: ...
    async def _render(
        self, width: int | None, height: int | None
    ) -> StyleAndTextTuples: ...
    async def render_element(
        self,
        element: Node,
        available_width: int,
        available_height: int,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_text_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_details_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_ol_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_list_item_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_table_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_grid_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_latex_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    @overload
    async def _render_datum(
        self,
        data: bytes,
        format_: str,
        theme: Theme,
        path: Path | None = None,
        raise_on_error: bool = False,
    ) -> StyleAndTextTuples: ...
    @overload
    async def _render_datum(
        self,
        data: str,
        format_: str,
        theme: Theme,
        path: Path | None = None,
        raise_on_error: bool = False,
    ) -> StyleAndTextTuples: ...
    async def _render_datum(
        self,
        data,
        format_,
        theme,
        path=None,
        raise_on_error=False,
    ): ...
    async def render_img_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_svg_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_include_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_input_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def render_node_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    async def format_element(
        self,
        ft: StyleAndTextTuples,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples: ...
    def __pt_formatted_text__(self) -> StyleAndTextTuples: ...
    def __repr__(self) -> str: ...
