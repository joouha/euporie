"""Convert display data between formats."""
from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import threading
from typing import TYPE_CHECKING, Generic, TypeVar
from weakref import ReferenceType, WeakValueDictionary, finalize, ref

import imagesize
from PIL.Image import Image as PilImage
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.data_structures import Size

from euporie.core.convert.registry import (
    _CONVERTOR_ROUTE_CACHE,
    _FILTER_CACHE,
    converters,
)
from euporie.core.current import get_app
from euporie.core.ft.utils import to_plain_text

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, ClassVar, Coroutine

    from rich.console import ConsoleRenderable

    from euporie.core.style import ColorPaletteColor


T = TypeVar("T", bytes, str, PilImage, "ConsoleRenderable")


log = logging.getLogger(__name__)


ERROR_OUTPUTS = {
    "ansi": "(Format Conversion Error)",
    "ft": [("fg:white bg:darkred", "(Format Conversion Error)")],
}


_IO_THREAD: list[threading.Thread | None] = [None]  # dedicated conversion IO thread
_LOOP: list[asyncio.AbstractEventLoop | None] = [
    None
]  # global event loop for conversion

_CONVERSION_CACHE: SimpleCache = SimpleCache(maxsize=2048)


def get_loop() -> asyncio.AbstractEventLoop:
    """Create or return the conversion IO loop.

    The loop will be running on a separate thread.
    """
    if _LOOP[0] is None:
        loop = asyncio.new_event_loop()
        _LOOP[0] = loop
        thread = threading.Thread(
            target=loop.run_forever, name="EuporieConvertIO", daemon=True
        )
        thread.start()
        _IO_THREAD[0] = thread
    assert _LOOP[0] is not None
    # Check we are not already in the conversion event loop
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None
    if _LOOP[0] is running_loop:
        raise NotImplementedError(
            "Cannot call `convert` from the conversion event loop"
        )
    return _LOOP[0]


class Datum(Generic[T]):
    """Class for storing and converting display data."""

    _pixel_size: tuple[int | None, int | None]
    _hash: str
    _root: ReferenceType[Datum]

    _instances: WeakValueDictionary[str, Datum] = WeakValueDictionary()
    _sizes: ClassVar[dict[str, tuple[ReferenceType[Datum], Size]]] = {}

    def __new__(cls, data: T, *args: Any, **kwargs: Any) -> Datum:
        """Create a single instance based on unique data."""
        data_hash = cls.get_hash(data)

        if instance := cls._instances.get(data_hash):
            return instance

        instance = super().__new__(cls)
        cls._instances[data_hash] = instance
        return instance

    def __init__(
        self,
        data: T,
        format: str,
        px: int | None = None,
        py: int | None = None,
        fg: ColorPaletteColor | str | None = None,
        bg: ColorPaletteColor | str | None = None,
        path: Path | None = None,
        source: Datum | None = None,
    ) -> None:
        """Create a new instance of display data."""
        # self.self = self
        self.data: T = data
        self.format = format
        self.px, self.py = px, py
        self.fg = str(fg) if fg else None
        self.bg = str(bg) if bg else None
        self.path = path
        self.source: ReferenceType[Datum] = ref(source) if source else ref(self)

        self._cell_size: tuple[int, float] | None = None

        self._conversions: dict[tuple[str, int | None, int | None], T] = {}

        self._finalizer = finalize(self, self._cleanup_datum_sizes, self.hash)
        self._finalizer.atexit = False

    @classmethod
    def _cleanup_datum_sizes(cls, data_hash: str) -> None:
        """Remove all sizes for a given datum hash."""
        size_instances = cls._sizes
        for key, (datum_ref, _size) in list(size_instances.items()):
            datum = datum_ref()
            if not datum or datum.hash == data_hash:
                del size_instances[key]
            del datum

    def to_bytes(self) -> bytes:
        """Cast the data to bytes."""
        data = self.data
        if isinstance(data, str):
            return data.encode()
        elif isinstance(data, list):
            return to_plain_text(data).encode()
        elif isinstance(data, PilImage):
            return data.tobytes()
        elif isinstance(data, bytes):
            return data
        else:
            return b"Error"

    @staticmethod
    def get_hash(data: Any) -> str:
        """Calculate a hash of data."""
        if isinstance(data, str):
            hash_data = data.encode()
        elif isinstance(data, PilImage):
            hash_data = data.tobytes()
        else:
            hash_data = data
        return hashlib.sha1(hash_data).hexdigest()  # noqa S324

    @property
    def hash(self) -> str:
        """Return a hash of the `Datum`'s data."""
        try:
            return self._hash
        except AttributeError:
            value = self.get_hash(self.to_bytes())
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
    ) -> Any:
        """Perform conversion asynchronously, caching the result."""
        if to == self.format:
            # TODO - crop
            return self.data

        if to in self._conversions:
            return self._conversions[to, cols, rows]

        routes = _CONVERTOR_ROUTE_CACHE[(self.format, to)]
        # log.debug(
        #     "Converting from '%s' to '%s' using route: %s", self, to, routes
        # )
        if not routes:
            # raise NotImplementedError(
            # f"Cannot convert from `self.format` to `to`"
            # )
            log.warning("Cannot convert from `%s` to `%s`", self.format, to)
            output = None
        else:
            datum = self
            output = None
            for route in routes:
                for stage_a, stage_b in zip(route, route[1:]):
                    # Find converter with lowest weight
                    func = sorted(
                        [
                            conv
                            for conv in converters[stage_b][stage_a]
                            if _FILTER_CACHE.get((conv,), conv.filter_)
                        ],
                        key=lambda x: x.weight,
                    )[0].func
                    try:
                        output = await func(datum, cols, rows)
                        self._conversions[stage_b, cols, rows] = output
                    except Exception:
                        log.exception("An error occurred during format conversion")
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
                            fg=self.fg,
                            bg=self.bg,
                            path=self.path,
                            source=datum,
                        )
                else:
                    # If this route succeeded, stop trying routes
                    break

        if output is None:
            output = ERROR_OUTPUTS.get(to, "(Conversion Error)")

        return output

    def _to_sync(self, coro: Coroutine) -> Any:
        """Call an async method synchronously."""
        future = asyncio.run_coroutine_threadsafe(coro, get_loop())
        return future.result()

    def convert(
        self,
        to: str,
        cols: int | None = None,
        rows: int | None = None,
    ) -> Any:
        """Convert between formats."""
        return self._to_sync(self.convert_async(to, cols, rows))

    async def pixel_size_async(self) -> tuple[int | None, int | None]:
        """Get the dimensions of displayable data in pixels.

        Foreground and background color are set at this point if they are available, as
        data conversion outputs are cached and re-used.

        Returns:
            A tuple of the data's width in terminal columns and its aspect ratio, when
                converted to a image.

        """
        try:
            return self._pixel_size
        except AttributeError:
            px, py = self.px, self.py
            # Do not bother trying if the format is ANSI
            if self.format != "ansi" and (px is None or py is None):
                # Try using imagesize to get the size of the output
                if self.format not in {"png", "svg", "jpeg", "gif", "tiff"}:
                    data = await self.convert_async(to="png")
                else:
                    data = self.data
                if isinstance(data, str):
                    data = data.encode()
                try:
                    px_calc, py_calc = imagesize.get(io.BytesIO(data))
                except ValueError:
                    pass
                else:
                    if px is None and px_calc > 0:
                        if py is not None and py_calc > 0:
                            px = px_calc * py / py_calc
                        else:
                            px = px_calc
                    if py is None and py_calc > 0:
                        if px is not None and px_calc > 0:
                            py = py_calc * px / px_calc
                        else:
                            py = py_calc
            self._pixel_size = (px, py)
            return self._pixel_size

    def pixel_size(self) -> Any:
        """Get data dimensions synchronously."""
        return self._to_sync(self.pixel_size_async())

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
                if hasattr(app, "term_info"):
                    cell_px, cell_py = app.term_info.cell_size_px
                else:
                    cell_px, cell_py = 10, 20
                cols = max(1, int(px // cell_px))
                aspect = (py / cell_py) / (px / cell_px)
            self._cell_size = cols, aspect
        return self._cell_size

    def cell_size(self) -> Any:
        """Get cell width and aspect synchronously."""
        return self._to_sync(self.cell_size_async())

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
