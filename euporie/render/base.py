"""Contains the data renderer base class."""

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from euporie.app import get_app

if TYPE_CHECKING:
    from typing import Any, Optional, Type, Union

    from euporie.graphics.base import TerminalGraphic

__all__ = ["DataRendererMeta", "DataRenderer", "FallbackRenderer"]

log = logging.getLogger(__name__)


class DataRendererMeta(ABCMeta):
    """Metaclass for data renderers to allow sorting of class types."""

    priority: "int"

    def __lt__(self, other: "DataRenderer") -> "bool":
        """Sort renderer classes based on priority."""
        return self.priority < other.priority


class DataRenderer(metaclass=DataRendererMeta):
    """Base class for rendering output data."""

    priority = 0

    def __init__(
        self,
        width: "Optional[int]" = None,
        height: "Optional[int]" = None,
        bg_color: "Optional[str]" = None,
        graphic: "Optional[TerminalGraphic]" = None,
    ):
        """Initiate the data renderer object."""
        self.app = get_app()
        self.width: "int" = width or 1
        self.height: "int" = height or 1
        self.graphic = graphic
        self.bg_color = bg_color

    def load(self, data: "Any") -> "None":
        """Function which performs setup tasks for the renderer.

        This is run after initiation and prior to each rendering.

        Args:
            data: Cell output data.

        """
        pass

    @classmethod
    def validate(cls) -> "bool":
        """Determine whether a DataRenderer should be used to render outputs."""
        return False

    @abstractmethod
    def process(self, data: "Any") -> "Union[str, bytes]":
        """Abstract function which processes cell output data.

        Args:
            data: Cell output data.

        Returns:
            NotImplemented

        """

    # async def _render(self, mime, data, **kwargs):
    # TODO - make this asynchronous again
    def render(
        self,
        data: "Any",
        width: "int",
        height: "int",
    ) -> "str":
        """Render the input data to ANSI.

        Args:
            data: The original data to be rendered.
            width: The desired output width in columns.
            height: The desired output height in rows.

        Returns:
            An ANSI string.

        """
        self.width = width
        self.height = height
        self.load(data)
        output = self.process(data)
        if isinstance(output, bytes):
            ansi_data = output.decode()
        else:
            ansi_data = output
        return ansi_data

    @classmethod
    def select(cls, *args: "Any", **kwargs: "Any") -> "DataRenderer":
        """Selects a renderer of this type to use.

        If not valid renderer is found, return a fallback renderer.

        Args:
            *args: Arguments to pass to the renderer when initiated.
            **kwargs: Key-word arguments to pass to the renderer when initiated.

        Returns:
            A valid DataRenderer instance.

        """
        if Renderer := cls._select(*args, **kwargs):
            selected = Renderer(*args, **kwargs)
        else:
            selected = FallbackRenderer(*args, **kwargs)
        assert isinstance(selected, DataRenderer)
        log.debug("Selecting '%s' for '%s'", type(selected).__name__, cls.__name__)
        return selected

    @classmethod
    def _select(cls, *args: "Any", **kwargs: "Any") -> "Optional[Type[DataRenderer]]":
        """Returns an instance of the first valid sub-class of renderer.

        1. If the renderer has no sub-renderers, validate it and return it
        2. If the renderer has sub-renderers, select one of those

        Args:
            *args: Arguments to pass to the renderer when initiated.
            **kwargs: Key-word arguments to pass to the renderer when initiated.

        Returns:
            An instance of the selected renderer.

        """
        # log.debug(f"Checking renderer {cls}")

        sub_renderers = cls.__subclasses__()

        # If there are no sub-renderers, try using the current renderer
        if not sub_renderers:
            # log.debug(f"No sub-renderers found, validating {cls}")
            if cls.validate():
                # log.debug(f"{cls} is valid")
                return cls
            else:
                # log.debug(f"{cls} found to be invalid")
                return None

        # If there are sub-renderers, try selecting one
        # log.debug(f"Sub-renderers of {cls} are: {sub_renderers}")
        for Renderer in sorted(sub_renderers):
            selection = Renderer._select()
            if selection is not None:
                return selection
        else:
            return None


class FallbackRenderer(DataRenderer):
    """Fallback renderer, used if nothing else works.

    This should never be needed.
    """

    @classmethod
    def validate(cls) -> "bool":
        """Always returns `True`.

        Returns:
            True.

        """
        return True

    def process(self, data: "str") -> "Union[bytes, str]":
        """Retruns text stating the data could not be renderered.

        Args:
            data: The data to be rendered.

        Returns:
            A string stating the output could not be rendered.

        """
        return "(Could not render output)"
