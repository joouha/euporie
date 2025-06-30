"""Modify the KeyProcessor to remove any timeout after an escape key press."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding.key_processor import KeyPress, _Flush
from prompt_toolkit.key_binding.key_processor import KeyProcessor as PtKeyProcessor
from prompt_toolkit.keys import Keys

from euporie.core.keys import MoreKeys

if TYPE_CHECKING:
    from typing import Any


log = logging.getLogger(__name__)


def _kp_init(
    self: KeyPress, key: Keys | MoreKeys | str, data: str | None = None
) -> None:
    """Include more keys when creating a KeyPress."""
    assert isinstance(key, (Keys | MoreKeys)) or len(key) == 1, (
        f"key {key!r} ({type(key)}) not recognised {MoreKeys(key)}"
    )
    if data is None:
        data = key.value if isinstance(key, (Keys, MoreKeys)) else key
    self.key = key
    self.data = data


setattr(KeyPress, "__init__", _kp_init)  # noqa: B010


class KeyProcessor(PtKeyProcessor):
    """A subclass of prompt_toolkit's keyprocessor.

    This adds an exception to the auto-flush timeout so that the input is flushed
    immediately if the key pressed is the escape key.

    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Create a new KeyProcessor instance."""
        super().__init__(*args, **kwargs)
        self._last_key_press: KeyPress | None = None

    def _start_timeout(self) -> None:
        """Start auto flush timeout. Similar to Vim's `timeoutlen` option.

        Do not apply a timeout if the key is :kbd:`Escape`.
        """
        app = get_app()
        timeout = app.timeoutlen

        if timeout is None:
            return

        async def wait() -> None:
            """Wait for timeout."""
            # This sleep can be cancelled. In that case we don't flush.
            # Don't sleep for the escape key
            if self._last_key_press is None or self._last_key_press.key != Keys.Escape:
                await asyncio.sleep(timeout)

            if len(self.key_buffer) > 0:
                # (No keys pressed in the meantime.)
                flush_keys()

        def flush_keys() -> None:
            """Fluh keys."""
            self.feed(_Flush)
            self.process_keys()

        # Automatically flush keys.
        if self._flush_wait_task:
            self._flush_wait_task.cancel()
        self._flush_wait_task = app.create_background_task(wait())

    def process_keys(self) -> None:
        """Process all the keys in the input queue."""
        app = get_app()
        input_queue = self.input_queue

        def not_empty() -> bool:
            # When the application result is set, stop processing keys.  (E.g.
            # if ENTER was received, followed by a few additional key strokes,
            # leave the other keys in the queue.)
            if app.is_done:
                # But if there are still CPRResponse keys in the queue, these
                # need to be processed.
                return any(k for k in self.input_queue if k.key == Keys.CPRResponse)
            else:
                return bool(self.input_queue)

        def get_next() -> KeyPress:
            if app.is_done:
                # Only process CPR responses. Everything else is typeahead.
                cpr = next(k for k in self.input_queue if k.key == Keys.CPRResponse)
                self.input_queue.remove(cpr)
                return cpr
            else:
                return input_queue.popleft()

        # Throttle repeated mouse events - limit to 10 per flush
        if len(input_queue) >= 10 and not any(
            input_queue[i].key != Keys.Vt100MouseEvent for i in range(10)
        ):
            for _ in range(len(input_queue) - 10):
                input_queue.popleft()

        is_flush = False

        self._last_key_press = None
        while not_empty():
            # Process next key.
            key_press = get_next()
            self._last_key_press = key_press

            is_flush = key_press is _Flush
            is_cpr = key_press.key == Keys.CPRResponse

            if not is_flush and not is_cpr:
                self.before_key_press.fire()

            try:
                self._process_coroutine.send(key_press)
            except Exception:
                # If for some reason something goes wrong in the parser, (maybe
                # an exception was raised) restart the processor for next time.
                self.reset()
                self.empty_queue()
                raise

            if not is_flush and not is_cpr:
                self.after_key_press.fire()

        # Skip timeout if the last key was flush.
        if not is_flush:
            self._start_timeout()

    def await_key(self, key: Keys | MoreKeys, timeout: float = 1.0) -> None:
        """Wait for a particular key, processing it before all other keys.

        Args:
            key: The key to wait for
            timeout: How long to wait for the key, in seconds
        """
        # Wait up to 1 second for response from terminal
        start = time.monotonic()
        input = get_app().input
        tkp = self.__class__(key_bindings=self._bindings)
        while (time.monotonic() - start) < timeout:
            time.sleep(0.05)
            for press in input.read_keys():
                if press.key == key:
                    # If we find the key we're after, process it immediately
                    tkp.feed_multiple([press, _Flush])
                    tkp.process_keys()
                    return
                else:
                    # If we get other keys, add them to the input queue
                    self.feed(press)
