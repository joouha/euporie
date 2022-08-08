"""Modify the KeyProcessor to remove any timeout after an escape key press."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding.key_processor import KeyProcessor as PtKeyProcessor
from prompt_toolkit.key_binding.key_processor import _Flush
from prompt_toolkit.keys import Keys

if TYPE_CHECKING:
    from typing import Any, Optional

    from prompt_toolkit.key_binding.key_processor import KeyPress

log = logging.getLogger(__name__)


class KeyProcessor(PtKeyProcessor):
    """A subclass of prompt_toolkit's keyprocessor.

    This adds an exception to the auto-flush timeout so that the input is flushed
    immediately if the key pressed is the escape key.

    """

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Create a new KeyProcessor instance."""
        super().__init__(*args, **kwargs)
        self._last_key_press: "Optional[KeyPress]" = None

    def _start_timeout(self) -> "None":
        """Start auto flush timeout. Similar to Vim's `timeoutlen` option.

        Do not apply a timeout if the key is :kbd:`Escape`.
        """
        app = get_app()
        timeout = app.timeoutlen

        if timeout is None:
            return

        async def wait() -> "None":
            """Wait for timeout."""
            # This sleep can be cancelled. In that case we don't flush.
            # Don't sleep for the escape key
            if self._last_key_press is None or self._last_key_press.key != Keys.Escape:
                await asyncio.sleep(timeout)

            if len(self.key_buffer) > 0:
                # (No keys pressed in the meantime.)
                flush_keys()

        def flush_keys() -> "None":
            """Flush keys."""
            self.feed(_Flush)
            self.process_keys()

        # Automatically flush keys.
        if self._flush_wait_task:
            self._flush_wait_task.cancel()
        self._flush_wait_task = app.create_background_task(wait())

    def process_keys(self) -> None:
        """Process all the keys in the input queue."""
        app = get_app()

        def not_empty() -> "bool":
            # When the application result is set, stop processing keys.  (E.g.
            # if ENTER was received, followed by a few additional key strokes,
            # leave the other keys in the queue.)
            if app.is_done:
                # But if there are still CPRResponse keys in the queue, these
                # need to be processed.
                return any(k for k in self.input_queue if k.key == Keys.CPRResponse)
            else:
                return bool(self.input_queue)

        def get_next() -> "KeyPress":
            if app.is_done:
                # Only process CPR responses. Everything else is typeahead.
                cpr = [k for k in self.input_queue if k.key == Keys.CPRResponse][0]
                self.input_queue.remove(cpr)
                return cpr
            else:
                return self.input_queue.popleft()

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
