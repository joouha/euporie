"""A application to show files on the command line."""

from typing import TYPE_CHECKING

from prompt_toolkit.application.current import set_app

from euporie.core.app import BaseApp
from euporie.core.convert.core import convert, get_format
from euporie.core.path import parse_path

if TYPE_CHECKING:
    from typing import Any, Callable, Optional


class ShowApp(BaseApp):
    """An app to show files."""

    name = "show"

    def __init__(self, **kwargs: "Any") -> "None":
        """Create an app to preview files."""
        super().__init__(**kwargs)

    def run(
        self,
        pre_run: "Optional[Callable[[], None]]" = None,
        set_exception_handler: "bool" = True,
        handle_sigint: "bool" = True,
        in_thread: "bool" = False,
    ) -> "None":
        """Display a file."""
        with set_app(self):
            size = self.output.get_size()
            for file in self.config.files:
                path = parse_path(file)
                data_bytes = path.read_bytes()

                data: str | bytes
                try:
                    data = data_bytes.decode()
                except UnicodeDecodeError:
                    data = data_bytes

                self.print_text(
                    convert(
                        data=data,
                        from_=get_format(path),
                        to="formatted_text",
                        rows=size.rows,
                        cols=size.columns,
                        path=path,
                    ),
                    style=self.create_merged_style(),
                )


if __name__ == "__main__":
    ShowApp.launch()
