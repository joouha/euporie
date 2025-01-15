"""Test core format conversion functions."""

from __future__ import annotations

import gc
from unittest.mock import PropertyMock, patch

from PIL import Image
from prompt_toolkit.application.current import set_app
from prompt_toolkit.data_structures import Size

from euporie.core.app.dummy import DummyApp
from euporie.core.convert.datum import Datum, get_loop


def test_get_loop() -> None:
    """Tests the instantiation and state of the asyncio event loop created by get_loop."""
    loop = get_loop()
    assert loop.is_running()
    assert not loop.is_closed()


def test_datum_new() -> None:
    """Creating the same datum twice returns the same instance."""
    image = Image.new("RGB", (60, 30), color="red")
    datum_1 = Datum(image, "pil")
    datum_2 = Datum(image, "pil")
    assert datum_1 is datum_2


async def test_convert() -> None:
    """Data is converted to another format."""
    # Async
    datum = Datum("Hello", format="ansi")
    result = await datum.convert_async("ft")
    assert result == [("", "Hello")]

    # Sync
    datum = Datum("Hello", format="ansi")
    result = datum.convert("ft")
    assert result == [("", "Hello")]

    # Self
    datum = Datum("Hello", format="ansi")
    result = datum.convert("ansi")
    assert result == datum.data

    # Invalid
    datum = Datum("Hello", format="ansi")
    result = datum.convert("unknown")
    assert result == "(Conversion Error)"


def test_convert_sync() -> None:
    """Data is converted to another format."""
    # datum = Datum(Image.new("RGB", (60, 30), color="red"), "pil")
    # output = await datum.convert_async("png")
    # assert b"<8-byte>" in str(output)

    datum = Datum("Hello", format="ansi")
    result = datum.convert("ft")
    assert result == [("", "Hello")]


async def test_convert_caching() -> None:
    """Convert results are cached."""
    datum = Datum("\x1b[31mHello", format="ansi")
    result = datum.convert(
        "ft", cols=100, rows=100, fg="#FFFFFF", bg="#000000", extend=False
    )
    assert datum._conversions["ft", 100, 100, "#FFFFFF", "#000000", False] == result


async def test_pixel_size_async() -> None:
    """Tests the asynchronous retrieval of a Datum object's pixel size."""
    datum_1 = Datum(Image.new("RGB", (256, 128), color="red"), format="pil")
    size = await datum_1.pixel_size_async()
    assert size == (256, 128)

    datum_2 = Datum('<svg width="10" height="20"></svg>', format="svg")
    size = await datum_2.pixel_size_async()
    assert size == (10, 20)


async def test_cell_size_async() -> None:
    """Tests the asynchronous retrieval of a Datum object's cell size."""
    datum = Datum(Image.new("RGB", (256, 128), color="red"), format="pil")
    app = DummyApp()
    with (
        set_app(app),
        patch(
            "euporie.core.app.dummy.DummyApp.cell_size_px", new_callable=PropertyMock
        ) as mock_cell_size_px,
    ):
        mock_cell_size_px.return_value = (8, 16)
        cols, aspect = await datum.cell_size_async()
    assert cols == 32
    assert aspect == 0.25


def test_sized_datum() -> None:
    """Tests the adding, retrieval, and deletion of SizedDatum objects."""
    image = Image.new("RGB", (60, 30), color="red")
    datum = Datum(image, "pil")
    size = Size(rows=2, columns=3)
    sized_datum = (datum, size)

    # Check key is created correctly
    key = Datum.add_size(datum, size)
    assert key in Datum._sizes

    # Check keyed datum is the same
    result = Datum.get_size(key)
    assert result is not None
    assert result == sized_datum
    del result
    del sized_datum

    # Check we get `None` for non-existent keys
    assert Datum.get_size("non-existent-key") is None

    # Check SizedDatum are cleaned up on datum deletion
    del datum
    gc.collect()
    assert key not in Datum._sizes
