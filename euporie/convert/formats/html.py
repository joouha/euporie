"""Contains function which convert HTML strings to other formats."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.convert.base import register
from euporie.convert.util import call_subproc, commands_exist, have_modules

if TYPE_CHECKING:
    from typing import Any, Optional


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("w3m"),
)
def html_to_ansi_w3m(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts HTML text to formatted ANSI using :command:`w3m`."""
    cmd: "list[Any]" = ["w3m", "-T", "text/html"]
    if width is not None:
        cmd += ["-cols", str(width)]
    return call_subproc(data.encode(), cmd).decode()


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("elinks"),
)
def html_to_ansi_elinks(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts HTML text to formatted ANSI using :command:`elinks`."""
    cmd: "list[Any]" = [
        "elinks",
        "-dump",
        "-no-numbering",
        "-force-html",
        "-no-references",
    ]
    if width is not None:
        cmd += ["-dump-width", width]
    return call_subproc(data.encode(), cmd).decode()


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("lynx"),
)
def html_to_ansi_lynx(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts HTML text to formatted ANSI using :command:`lynx`."""
    cmd: "list[Any]" = ["lynx", "-dump", "-stdin"]
    if width is not None:
        cmd += [f"-width={width}"]
    return call_subproc(data.encode(), cmd).decode()


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("links"),
)
def html_to_ansi_links(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts HTML text to formatted ANSI using :command:`links`."""
    cmd: "list[Any]" = ["links", "-dump"]
    if width is not None:
        cmd += ["-width", width]
    return call_subproc(data.encode(), cmd, use_tempfile=True).decode()


@register(
    from_="html",
    to="markdown",
    filter_=have_modules("mtable", "html5lib"),
)
def html_to_markdown_py_mtable(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert HTML tables to markdown tables using :py:mod:`mtable`."""
    from mtable import MarkupTable  # type: ignore

    return "\n\n".join([table.to_md() for table in MarkupTable.from_html(data)])


@register(
    from_="html",
    to="ansi",
    filter_=True,
)
def html_to_ansi_py_htmlparser(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert HTML tables to ANSI text using :py:mod:`HTMLParser`."""
    import io
    import re
    from html.parser import HTMLParser

    class HTMLStripper(HTMLParser):
        """Very basic HTML parser which strips style and script tags."""

        def __init__(self):
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.text = io.StringIO()
            self.skip = False
            self.skip_tags = ("script", "style")

        def handle_starttag(
            self, tag: "str", attrs: "list[tuple[str, Optional[str]]]"
        ) -> "None":
            if tag in self.skip_tags:
                self.skip = True

        def handle_endtag(self, tag: "str") -> "None":
            if tag in self.skip_tags:
                self.skip = False

        def handle_data(self, d: "str") -> "None":
            if not self.skip:
                self.text.write(d)

        def get_data(self) -> "str":
            return self.text.getvalue()

    stripper = HTMLStripper()
    stripper.feed(data)
    output = stripper.get_data()
    # Strip lines
    output = "\n".join([x.strip() for x in output.strip().split("\n")])
    # Remove empty paragraphs
    output = re.sub("\n\n\n+", "\n\n", output)
    return output
