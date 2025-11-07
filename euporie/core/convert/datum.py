"""Convert display data between formats."""

from __future__ import annotations

import asyncio
import inspect
import io
import logging
from hashlib import md5
from itertools import pairwise
from typing import TYPE_CHECKING, Generic, TypeVar
from weakref import ReferenceType, WeakValueDictionary, finalize, ref

from prompt_toolkit.data_structures import Size
from prompt_toolkit.layout.containers import WindowAlign

from euporie.core.app.current import get_app
from euporie.core.async_utils import get_or_create_loop, run_coro_sync
from euporie.core.convert.registry import (
    _CONVERTOR_ROUTE_CACHE,
    _FILTER_CACHE,
    converters,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, ClassVar

    from PIL.Image import Image as PilImage
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from rich.console import ConsoleRenderable

    from euporie.core.data_structures import DiInt
    from euporie.core.style import ColorPaletteColor


T = TypeVar("T", bytes, str, "StyleAndTextTuples", "PilImage", "ConsoleRenderable")


log = logging.getLogger(__name__)


ERROR_OUTPUTS: dict[str, Any] = {
    "ansi": "(Format Conversion Error)",
    "ft": [("fg:white bg:darkred", "(Format Conversion Error)")],
}


class _MetaDatum(type):
    _instances: WeakValueDictionary[tuple[Any, ...], Datum] = WeakValueDictionary()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __call__(self, data: T, *args: Any, **kwargs: Any) -> Datum[T]:
        data_hash = Datum.get_hash(data)
        key: tuple[Any, ...] = (
            data_hash,
            *args,
            # Get defaults for non-passed kwargs
            *(
                kwargs.get(param.name, param.default)
                for param in inspect.signature(Datum.__init__).parameters.values()
                if param.default is not inspect._empty
                and param.name not in {"path", "source"}
            ),
        )
        if key in self._instances:
            return self._instances[key]
        instance = super().__call__(data, *args, **kwargs)
        self._instances[key] = instance
        return instance


class Datum(Generic[T], metaclass=_MetaDatum):
    """Class for storing and converting display data."""

    _pixel_size: tuple[int | None, int | None]
    _hash: str
    _root: ReferenceType[Datum]

    _sizes: ClassVar[dict[str, tuple[ReferenceType[Datum], Size]]] = {}

    def __init__(
        self,
        data: T,
        format: str,
        px: int | None = None,
        py: int | None = None,
        fg: str | ColorPaletteColor | None = None,
        bg: str | ColorPaletteColor | None = None,
        path: Path | None = None,
        source: Datum | None = None,
        align: WindowAlign = WindowAlign.LEFT,
    ) -> None:
        """Create a new instance of display data."""
        self.data: T = data
        self.format = format
        self.px, self.py = px, py
        self.fg = str(fg) if fg is not None else None
        self.bg = str(bg) if bg is not None else None
        self.path = path
        self.source: ReferenceType[Datum] = ref(source) if source else ref(self)
        self.align = align
        self._cell_size: tuple[int, float] | None = None
        self._conversions: dict[
            tuple[
                str,
                int | None,
                int | None,
                str | None,
                str | None,
                tuple[tuple[str, Any], ...],
            ],
            T | None,
        ] = {}
        self._queue: dict[
            tuple[
                str,
                int | None,
                int | None,
                str | None,
                str | None,
                tuple[tuple[str, Any], ...],
            ],
            asyncio.Event,
        ] = {}
        self._finalizer: finalize = finalize(self, self._cleanup_datum_sizes, self.hash)
        self._finalizer.atexit = False  # type: ignore [misc]
        self.loop = get_or_create_loop("convert")

    def __repr__(self) -> str:
        """Return a string representation of object."""
        return f"{self.__class__.__name__}(format={self.format!r})"

    @classmethod
    def _cleanup_datum_sizes(cls, data_hash: str) -> None:
        """Remove all sizes for a given datum hash."""
        size_instances = cls._sizes
        for key, (datum_ref, _size) in list(size_instances.items()):
            datum = datum_ref()
            if not datum or datum.hash == data_hash:
                try:
                    del size_instances[key]
                except KeyError:
                    pass
            del datum

    @staticmethod
    def get_hash(data: T) -> str:
        """Calculate a hash of data."""
        hash_data: bytes
        if isinstance(data, bytes):
            hash_data = data
        elif isinstance(data, str):
            hash_data = data.encode()
        elif isinstance(data, list):
            hash_data = hash(tuple(data)).to_bytes(8)
        elif isinstance(data, bytes):
            hash_data = data
        else:
            from PIL.Image import Image as PilImage

            if isinstance(data, PilImage):
                hash_data = data.tobytes()
            else:
                hash_data = b"Error"
        return md5(hash_data, usedforsecurity=False).hexdigest()

    @property
    def hash(self) -> str:
        """Return a hash of the `Datum`'s data."""
        try:
            return self._hash
        except AttributeError:
            value = self.get_hash(self.data)
            self._hash = value
            return value

    @property
    def root(self) -> Datum:
        """Retrieve the source datum of any conversion outputs."""
        try:
            return self._root() or self
        except AttributeError:
            root = self
            while True:
                if (source := root.source()) == root or source is None:
                    break
                else:
                    root = source
            self._root = ref(root or self)
            return root

    async def convert_async(
        self,
        to: str,
        cols: int | None = None,
        rows: int | None = None,
        fg: str | None = None,
        bg: str | None = None,
        bbox: DiInt | None = None,
        **kwargs: Any,
    ) -> Any:
        """Perform conversion asynchronously, caching the result."""
        if to == self.format:
            # TODO - crop
            return self.data

        if not fg and hasattr(app := get_app(), "color_palette"):
            fg = self.fg or app.color_palette.fg.base_hex
        if not bg and hasattr(app := get_app(), "color_palette"):
            bg = self.bg or app.color_palette.bg.base_hex

        if (key_conv := (to, cols, rows, fg, bg, tuple(kwargs.items()))) in self._queue:
            await self._queue[key_conv].wait()
        if key_conv in self._conversions:
            return self._conversions[key_conv]

        self._queue[key_conv] = event = asyncio.Event()

        routes = _CONVERTOR_ROUTE_CACHE[(self.format, to)]
        # log.debug(
        #     "Converting %s->'%s'@%s using routes: %s",
        #     self,
        #     to,
        #     (cols, rows),
        #     routes,
        # )
        output: T | None = None
        if routes:
            datum = self
            output = None
            for route in routes:
                for stage_a, stage_b in pairwise(route):
                    key_stage = (stage_b, cols, rows, fg, bg, tuple(kwargs.items()))
                    if key_stage in self._conversions:
                        output = self._conversions[key_stage]
                    else:
                        # Find converter with lowest weight
                        for converter in sorted(
                            [
                                conv
                                for conv in converters[stage_b][stage_a]
                                if _FILTER_CACHE.get((conv,), conv.filter_)
                            ],
                            key=lambda x: x.weight,
                        ):
                            try:
                                output = await converter.func(
                                    datum, cols, rows, fg, bg, **kwargs
                                )
                                self._conversions[key_stage] = output
                            except Exception:
                                log.debug(
                                    "Conversion step %s failed",
                                    converter,
                                    exc_info=True,
                                )
                                continue
                            else:
                                break
                        else:
                            log.warning("An error occurred during format conversion")
                            output = None
                    if output is None:
                        log.error(
                            "Failed to convert `%s`"
                            " to `%s` using route `%s` at stage `%s`",
                            self,
                            to,
                            route,
                            stage_b,
                        )
                        # Try the next route on error
                        break
                    if stage_b != route[-1]:
                        datum = Datum(
                            data=output,
                            format=stage_b,
                            px=self.px,
                            py=self.py,
                            fg=fg,
                            bg=bg,
                            path=self.path,
                            source=datum,
                        )
                else:
                    # If this route succeeded, stop trying routes
                    break

        # Crop or pad output
        # if bbox and any(bbox):

        if output is None:
            output = ERROR_OUTPUTS.get(to, "(Conversion Error)")

        event.set()
        del self._queue[key_conv]

        return output

    def convert(
        self,
        to: str,
        cols: int | None = None,
        rows: int | None = None,
        fg: str | None = None,
        bg: str | None = None,
        bbox: DiInt | None = None,
        **kwargs: Any,
    ) -> Any:
        """Convert between formats."""
        return run_coro_sync(
            self.convert_async(to, cols, rows, fg, bg, bbox, **kwargs), self.loop
        )

    async def pixel_size_async(self) -> tuple[int | None, int | None]:
        """Get the dimensions of displayable data in pixels.

        Foreground and background color are set at this point if they are available, as
        data conversion outputs are cached and reused.

        Returns:
            A tuple of the data's width in terminal columns and its aspect ratio, when
                converted to a image.

        """
        try:
            return self._pixel_size
        except AttributeError:
            pass

        px, py = self.px, self.py
        self_data = self.data
        format = self.format
        data: bytes

        while px is None or py is None:
            # Do not bother trying if the format is ANSI
            if format == "ansi":
                break

            from PIL.Image import Image as PilImage

            if isinstance(self_data, PilImage):
                px, py = self_data.size
                break

            # Decode base64 data
            if format.startswith("base64-"):
                data = await self.convert_async(to=format[7:])

            # Encode string data
            if isinstance(self_data, str):
                data = self_data.encode()

            if isinstance(self_data, bytes):
                data = self_data

            # Try using imagesize to get the size of the output
            try:
                import imagesize

                px_calc, py_calc = imagesize.get(io.BytesIO(data))
            except ValueError:
                px_calc = py_calc = -1

            if (
                format != "png"
                and px_calc <= 0
                and py_calc <= 0
                and _CONVERTOR_ROUTE_CACHE[(format, "png")]
            ):
                # Try converting to PNG on failure
                self_data = await self.convert_async(to="png")
                format = "png"
                continue

            if px is None and px_calc > 0:
                if py is not None and py_calc > 0:
                    px = int(px_calc * py / py_calc)
                else:
                    px = px_calc
            if py is None and py_calc > 0:
                if px is not None and px_calc > 0:
                    py = int(py_calc * px / px_calc)
                else:
                    py = py_calc
            break

        self._pixel_size = (px, py)
        return self._pixel_size

    def pixel_size(self) -> Any:
        """Get data dimensions synchronously."""
        return run_coro_sync(self.pixel_size_async(), self.loop)

    async def cell_size_async(self) -> tuple[int, float]:
        """Get the cell width and aspect ratio of the displayable data.

        Returns:
            A tuple of the data's width in terminal columns and its aspect ratio, when
                converted to a image.
        """
        if self._cell_size is None:
            cols, aspect = 0, 0.0
            px, py = await self.pixel_size_async()
            if px is not None and py is not None:
                app = get_app()
                if hasattr(app, "cell_size_px"):
                    cell_px, cell_py = app.cell_size_px
                else:
                    cell_px, cell_py = 10, 20
                cols = max(1, int(px // cell_px))
                aspect = (py / cell_py) / (px / cell_px)
            self._cell_size = cols, aspect
        return self._cell_size

    def cell_size(self) -> Any:
        """Get cell width and aspect synchronously."""
        if self._cell_size is None:
            return run_coro_sync(self.cell_size_async(), self.loop)
        return self._cell_size

    # def crop(self, bbox: DiInt) -> T:
    #     """Crop displayable data."""

    def add_size(self, size: tuple[int, int] | Size) -> str:
        """Store a size for a :py:class`Datum`."""
        sized_datum = (ref(self), Size(*size))
        key = str(hash(sized_datum))
        self._sizes[key] = sized_datum
        return key

    @classmethod
    def get_size(cls, key: str) -> tuple[Datum, Size] | None:
        """Retrieve a :py:class:`Datum` and it's size by its key."""
        if sized_datum := cls._sizes.get(key):
            datum_ref, size = sized_datum
            if datum := datum_ref():
                return datum, size
        return None
