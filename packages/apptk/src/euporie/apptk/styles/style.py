"""Dynamic style based on color palette."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.styles.style import parse_color

from euporie.apptk.styles.base import DEFAULT_ATTRS, Attrs, BaseStyle

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable

    from prompt_toolkit.styles.style import _T

    from euporie.apptk.color import ColorPalette

log = logging.getLogger(__name__)

_EMPTY_ATTRS = Attrs(
    color=None,
    bgcolor=None,
    bold=None,
    dim=None,
    underline=None,
    strike=None,
    italic=None,
    blink=None,
    reverse=None,
    hidden=None,
    ulcolor=None,
    doubleunderline=None,
    curvyunderline=None,
    dottedunderline=None,
    dashedunderline=None,
    blinkfast=None,
    overline=None,
)


def _parse_style_str(style_str: str) -> Attrs:
    """Take a style string, e.g.  'bg:red #88ff00 class:title' and return a `Attrs` instance."""
    # Start from default Attrs.
    if "noinherit" in style_str:
        attrs = DEFAULT_ATTRS
    else:
        attrs = _EMPTY_ATTRS

    # Now update with the given attributes.
    for part in style_str.split():
        if part == "noinherit":
            pass
        elif part == "bold":
            attrs = attrs._replace(bold=True)
        elif part == "nobold":
            attrs = attrs._replace(bold=False)
        elif part == "italic":
            attrs = attrs._replace(italic=True)
        elif part == "noitalic":
            attrs = attrs._replace(italic=False)
        elif part == "underline":
            attrs = attrs._replace(underline=True)
        elif part == "nounderline":
            attrs = attrs._replace(underline=False)
        elif part == "strike":
            attrs = attrs._replace(strike=True)
        elif part == "nostrike":
            attrs = attrs._replace(strike=False)

        # prompt_toolkit extensions. Not in Pygments.
        elif part == "blink":
            attrs = attrs._replace(blink=True)
        elif part == "noblink":
            attrs = attrs._replace(blink=False)
        elif part == "blinkfast":
            attrs = attrs._replace(blinkfast=True)
        elif part == "noblinkfast":
            attrs = attrs._replace(blinkfast=False)
        elif part == "reverse":
            attrs = attrs._replace(reverse=True)
        elif part == "noreverse":
            attrs = attrs._replace(reverse=False)
        elif part == "hidden":
            attrs = attrs._replace(hidden=True)
        elif part == "nohidden":
            attrs = attrs._replace(hidden=False)
        elif part == "dim":
            attrs = attrs._replace(dim=True)
        elif part == "nodim":
            attrs = attrs._replace(dim=False)

        # apptk extensions. Not in prompt toolkit
        elif part == "doubleunderline":
            attrs = attrs._replace(doubleunderline=True)
        elif part == "nodoubleunderline":
            attrs = attrs._replace(doubleunderline=False)
        elif part == "curvyunderline":
            attrs = attrs._replace(curvyunderline=True)
        elif part == "nocurvyunderline":
            attrs = attrs._replace(curvyunderline=False)
        elif part == "dottedunderline":
            attrs = attrs._replace(dottedunderline=True)
        elif part == "nodottedunderline":
            attrs = attrs._replace(dottedunderline=False)
        elif part == "dashedunderline":
            attrs = attrs._replace(dashedunderline=True)
        elif part == "nodashedunderline":
            attrs = attrs._replace(dashedunderline=False)
        elif part == "overline":
            attrs = attrs._replace(overline=True)
        elif part == "nooverline":
            attrs = attrs._replace(overline=False)

        elif (
            # Pygments properties that we ignore.
            part in ("roman", "sans", "mono")
            or part.startswith("border:")
            # Ignore pieces in between square brackets. This is internal stuff.
            # Like '[transparent]' or '[set-cursor-position]'.
            or (part.startswith("[") and part.endswith("]"))
        ):
            pass

        # Colors.
        elif part.startswith("bg:"):
            attrs = attrs._replace(bgcolor=parse_color(part[3:]))
        elif part.startswith("fg:"):
            attrs = attrs._replace(color=parse_color(part[3:]))
        elif part.startswith("ul:"):
            attrs = attrs._replace(ulcolor=parse_color(part[3:]))
        else:
            # The 'fg:' prefix is optional.
            try:
                attrs = attrs._replace(color=parse_color(part))
            except ValueError:
                log.exception("Unrecognised color format")

    return attrs


def _merge_attrs(list_of_attrs: list[Attrs]) -> Attrs:
    """Take a list of :class:`.Attrs` instances and merge them into one.

    Every `Attr` in the list can override the styling of the previous one. So,
    the last one has highest priority.
    """

    def _or(*values: _T) -> _T:
        """Take first not-None value, starting at the end."""
        for v in values[::-1]:
            if v is not None:
                return v
        raise ValueError  # Should not happen, there's always one non-null value.

    return Attrs(
        color=_or("", *[a.color for a in list_of_attrs]),
        bgcolor=_or("", *[a.bgcolor for a in list_of_attrs]),
        bold=_or(False, *[a.bold for a in list_of_attrs]),
        dim=_or(False, *[a.dim for a in list_of_attrs]),
        underline=_or(False, *[a.underline for a in list_of_attrs]),
        strike=_or(False, *[a.strike for a in list_of_attrs]),
        italic=_or(False, *[a.italic for a in list_of_attrs]),
        blink=_or(False, *[a.blink for a in list_of_attrs]),
        reverse=_or(False, *[a.reverse for a in list_of_attrs]),
        hidden=_or(False, *[a.hidden for a in list_of_attrs]),
        blinkfast=_or(False, *[a.blinkfast for a in list_of_attrs]),
        ulcolor=_or("", *[a.ulcolor for a in list_of_attrs]),
        doubleunderline=_or(False, *[a.doubleunderline for a in list_of_attrs]),
        curvyunderline=_or(False, *[a.curvyunderline for a in list_of_attrs]),
        dottedunderline=_or(False, *[a.dottedunderline for a in list_of_attrs]),
        dashedunderline=_or(False, *[a.dashedunderline for a in list_of_attrs]),
        overline=_or(False, *[a.overline for a in list_of_attrs]),
    )


class PaletteStyle(BaseStyle):
    """A style that dynamically generates rules from a color palette.

    This style accepts color dictionaries and style definition generators,
    recalculating styles when the underlying colors change.
    """

    def __init__(
        self,
        color_palette: ColorPalette,
        get_style: Callable[[ColorPalette], dict[str, str]],
    ) -> None:
        """Initialize the palette style.

        Args:
            color_palette: Color palette with named colors
            get_style: Callables that take a ColorPalette and return a dict mapping
                style class names to style strings.
        """
        self.color_palette = color_palette
        self._get_style = get_style
        self._cached_style: BaseStyle | None = None
        self._cached_hash: Hashable | None = None

    def _build_style(self) -> BaseStyle:
        """Build the underlying Style from generators and palette."""
        from euporie.apptk.styles.style import Style

        return Style.from_dict(self._get_style(self.color_palette))

    def _style(self) -> BaseStyle:
        """Get the cached style, rebuilding if invalidated."""
        current_hash = self.invalidation_hash()
        if self._cached_style is None or self._cached_hash != current_hash:
            self._cached_style = self._build_style()
            self._cached_hash = current_hash
        return self._cached_style

    def get_attrs_for_style_str(
        self, style_str: str, default: Attrs = DEFAULT_ATTRS
    ) -> Attrs:
        """Return Attrs for the given style string.

        Args:
            style_str: The style string to look up.
            default: Default Attrs if no styling defined.

        Returns:
            The computed Attrs for the style string.
        """
        return self._style().get_attrs_for_style_str(style_str, default)

    @property
    def style_rules(self) -> list[tuple[str, str]]:
        """The list of style rules from the underlying style."""
        return self._style().style_rules

    def invalidation_hash(self) -> Hashable:
        """Compute hash based on current color values."""
        return hash(self.color_palette)
