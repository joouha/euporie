"""Dynamic style based on color palette."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.styles.base import DEFAULT_ATTRS, Attrs, BaseStyle

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable

    from euporie.apptk.color import ColorPalette


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
