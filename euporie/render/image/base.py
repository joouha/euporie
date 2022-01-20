"""Contains base class for renderers which convert images to displayable output."""

from __future__ import annotations

from euporie.render.base import DataRenderer
from euporie.render.mixin import ImageMixin

__all__ = ["ImageRenderer"]


class ImageRenderer(ImageMixin, DataRenderer):
    """A grouping renderer for images."""
