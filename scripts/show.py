"""A application to show files on the command line."""

from typing import TYPE_CHECKING

from prompt_toolkit.application.current import set_app

from euporie.core.app import BaseApp
from euporie.core.convert.base import convert, get_format

if TYPE_CHECKING:
    from typing import Any, Callable, Optional

    from prompt_toolkit.application.base import _AppResult


class ShowApp(BaseApp):
    """An app to show files."""

    def __init__(self, **kwargs: "Any") -> "None":
        """Create an app to preview files."""
        super().__init__(**kwargs)
        # print(self.vt100_parser)

    def run(
        self,
        pre_run: "Optional[Callable[[], None]]" = None,
        set_exception_handler: "bool" = True,
        handle_sigint: "bool" = True,
        in_thread: "bool" = False,
    ) -> "_AppResult":
        """Display a file."""
        with set_app(self):
            size = self.output.get_size()
            for file in self.config.files:
                data_bytes = file.read_bytes()

                try:
                    data = data_bytes.decode()
                except UnicodeDecodeError:
                    data = data_bytes

                self.print_text(
                    convert(
                        data=data,
                        from_=get_format(file),
                        to="formatted_text",
                        rows=size.rows,
                        cols=size.columns,
                        path=file,
                    ),
                    style=self.create_merged_style(),
                )


if __name__ == "__main__":
    ShowApp.launch()
