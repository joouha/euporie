"""Tests for key binding functionality."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest
from apptk.application import Application
from apptk.application.current import set_app
from apptk.input.defaults import create_pipe_input
from apptk.key_binding.key_bindings import KeyBindings
from apptk.key_binding.key_processor import KeyPress, KeyProcessor
from apptk.keys import Keys
from apptk.layout import Layout, Window
from apptk.output import DummyOutput


class Handlers:
    """Handler class for tracking key binding calls."""

    def __init__(self) -> None:
        """Initialize the handlers."""
        self.called: list[str] = []

    def controlx_controlc(self, event: Any) -> None:
        """Handle control-x control-c."""
        self.called.append("controlx_controlc")

    def control_x(self, event: Any) -> None:
        """Handle control-x."""
        self.called.append("control_x")

    def control_d(self, event: Any) -> None:
        """Handle control-d."""
        self.called.append("control_d")

    def controld(self, event: Any) -> None:
        """Handle control-d (alternate name)."""
        self.called.append("controld")

    def control_square_close_any(self, event: Any) -> None:
        """Handle control-square-close any."""
        self.called.append("control_square_close_any")


@contextmanager
def set_dummy_app() -> Generator[None, None, None]:
    """Set up a dummy application for testing.

    This is important, because we need an `Application` with
    `is_done=False` flag, otherwise no keys will be processed.
    """
    with create_pipe_input() as pipe_input:
        app = Application(
            layout=Layout(Window()),
            output=DummyOutput(),
            input=pipe_input,
        )

        # Don't start background tasks for these tests. The `KeyProcessor`
        # wants to create a background task for flushing keys. We can ignore it
        # here for these tests.
        # This patch is not clean. In the future, when we can use Taskgroups,
        # the `Application` should pass its task group to the constructor of
        # `KeyProcessor`. That way, it doesn't have to do a lookup using
        # `get_app()`.
        def _cancel_background_task(coro: Any, **kw: Any) -> None:
            """Close the coroutine to prevent 'was never awaited' warnings."""
            coro.close()

        app.create_background_task = _cancel_background_task

        with set_app(app):
            yield


@pytest.fixture
def handlers() -> Handlers:
    """Create a handlers fixture."""
    return Handlers()


@pytest.fixture
def bindings(handlers: Handlers) -> KeyBindings:
    """Create key bindings fixture."""
    bindings = KeyBindings()
    bindings.add(Keys.ControlX, Keys.ControlC)(handlers.controlx_controlc)
    bindings.add(Keys.ControlX)(handlers.control_x)
    bindings.add(Keys.ControlD)(handlers.control_d)
    bindings.add(Keys.ControlSquareClose, Keys.Any)(handlers.control_square_close_any)

    return bindings


@pytest.fixture
def processor(bindings: KeyBindings) -> KeyProcessor:
    """Create a key processor fixture."""
    return KeyProcessor(bindings)


def test_remove_bindings(handlers: Handlers) -> None:
    """Test removing key bindings."""
    with set_dummy_app():
        h = handlers.controlx_controlc
        h2 = handlers.controld

        # Test passing a handler to the remove() function.
        bindings = KeyBindings()
        bindings.add(Keys.ControlX, Keys.ControlC)(h)
        bindings.add(Keys.ControlD)(h2)
        assert len(bindings.bindings) == 2
        bindings.remove(h)
        assert len(bindings.bindings) == 1

        # Test passing a key sequence to the remove() function.
        bindings = KeyBindings()
        bindings.add(Keys.ControlX, Keys.ControlC)(h)
        bindings.add(Keys.ControlD)(h2)
        assert len(bindings.bindings) == 2
        bindings.remove(Keys.ControlX, Keys.ControlC)
        assert len(bindings.bindings) == 1


def test_feed_simple(processor: KeyProcessor, handlers: Handlers) -> None:
    """Test simple key feeding."""
    with set_dummy_app():
        processor.feed(KeyPress(Keys.ControlX, "\x18"))
        processor.feed(KeyPress(Keys.ControlC, "\x03"))
        processor.process_keys()

        assert handlers.called == ["controlx_controlc"]


def test_feed_several(processor: KeyProcessor, handlers: Handlers) -> None:
    """Test feeding several keys."""
    with set_dummy_app():
        # First an unknown key first.
        processor.feed(KeyPress(Keys.ControlQ, ""))
        processor.process_keys()

        assert handlers.called == []

        # Followed by a know key sequence.
        processor.feed(KeyPress(Keys.ControlX, ""))
        processor.feed(KeyPress(Keys.ControlC, ""))
        processor.process_keys()

        assert handlers.called == ["controlx_controlc"]

        # Followed by another unknown sequence.
        processor.feed(KeyPress(Keys.ControlR, ""))
        processor.feed(KeyPress(Keys.ControlS, ""))

        # Followed again by a know key sequence.
        processor.feed(KeyPress(Keys.ControlD, ""))
        processor.process_keys()

        assert handlers.called == ["controlx_controlc", "control_d"]


def test_control_square_closed_any(processor: KeyProcessor, handlers: Handlers) -> None:
    """Test control square close with any key."""
    with set_dummy_app():
        processor.feed(KeyPress(Keys.ControlSquareClose, ""))
        processor.feed(KeyPress("C", "C"))
        processor.process_keys()

        assert handlers.called == ["control_square_close_any"]


def test_common_prefix(processor: KeyProcessor, handlers: Handlers) -> None:
    """Test key bindings with common prefix."""
    with set_dummy_app():
        # Sending Control_X should not yet do anything, because there is
        # another sequence starting with that as well.
        processor.feed(KeyPress(Keys.ControlX, ""))
        processor.process_keys()

        assert handlers.called == []

        # When another key is pressed, we know that we did not meant the longer
        # "ControlX ControlC" sequence and the callbacks are called.
        processor.feed(KeyPress(Keys.ControlD, ""))
        processor.process_keys()

        assert handlers.called == ["control_x", "control_d"]


def test_previous_key_sequence(processor: KeyProcessor) -> None:
    """Test whether we receive the correct previous_key_sequence."""
    with set_dummy_app():
        events: list[Any] = []

        def handler(event: Any) -> None:
            events.append(event)

        # Build registry.
        registry = KeyBindings()
        registry.add("a", "a")(handler)
        registry.add("b", "b")(handler)
        processor = KeyProcessor(registry)

        # Create processor and feed keys.
        processor.feed(KeyPress("a", "a"))
        processor.feed(KeyPress("a", "a"))
        processor.feed(KeyPress("b", "b"))
        processor.feed(KeyPress("b", "b"))
        processor.process_keys()

        # Test.
        assert len(events) == 2
        assert len(events[0].key_sequence) == 2
        assert events[0].key_sequence[0].key == "a"
        assert events[0].key_sequence[0].data == "a"
        assert events[0].key_sequence[1].key == "a"
        assert events[0].key_sequence[1].data == "a"
        assert events[0].previous_key_sequence == []

        assert len(events[1].key_sequence) == 2
        assert events[1].key_sequence[0].key == "b"
        assert events[1].key_sequence[0].data == "b"
        assert events[1].key_sequence[1].key == "b"
        assert events[1].key_sequence[1].data == "b"
        assert len(events[1].previous_key_sequence) == 2
        assert events[1].previous_key_sequence[0].key == "a"
        assert events[1].previous_key_sequence[0].data == "a"
        assert events[1].previous_key_sequence[1].key == "a"
        assert events[1].previous_key_sequence[1].data == "a"
