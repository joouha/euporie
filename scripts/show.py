#!/usr/bin/env python
"""A application to show files on the command line."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.apptk.application.current import set_app

from euporie.apptk.convert.datum import Datum
from euporie.apptk.convert.mime import get_format
from euporie.apptk.layout.containers import DummyContainer
from euporie.core.app.app import BaseApp
from euporie.apptk.path import parse_path

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from euporie.apptk.eventloop import InputHook


class ShowApp(BaseApp):
    """An app to show files."""

    name = "show"

    def __init__(self, **kwargs: Any) -> None:
        """Create an app to preview files."""
        super().__init__(**kwargs)

    def load_container(self) -> DummyContainer:
        """No container."""
        return DummyContainer()

    def run(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        in_thread: bool = False,
        inputhook: InputHook | None = None,
    ) -> None:
        """Display a file."""
        with set_app(self):
            size = self.output.get_size()
            for file in self.config.files:
                path = parse_path(file)
                data_bytes = path.read_bytes()

                self.print_text(
                    Datum(data_bytes, format=get_format(path), path=path).convert(
                        "ft", rows=size.rows, cols=size.columns
                    ),
                    style=self.create_merged_style(),
                )


if __name__ == "__main__":
    ShowApp.launch()
