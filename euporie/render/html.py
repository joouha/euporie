"""Contains renderer classes which convert rich content to displayable output."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from euporie.render.base import DataRenderer
from euporie.render.markdown import MarkdownRenderer
from euporie.render.mixin import PythonRenderMixin, SubprocessRenderMixin

if TYPE_CHECKING:
    from typing import Any, Optional, Union


__all__ = [
    "HTMLRenderer",
    "html_w3m",
    "html_elinks",
    "html_lynx",
    "html_links",
    "html_mtable_py",
    "html_fallback_py",
]

log = logging.getLogger(__name__)


class HTMLRenderer(DataRenderer):
    """A grouping renderer for HTML."""


class html_w3m(SubprocessRenderMixin, HTMLRenderer):
    """Renderers HTML using `w3m`."""

    cmd = "w3m"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        self.args = ["-T", "text/html", "-cols", f"{self.width}"]


class html_elinks(SubprocessRenderMixin, HTMLRenderer):
    """Renderers HTML using `elinks`."""

    cmd = "elinks"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        self.args = [
            "-dump",
            "-dump-width",
            f"{self.width}",
            "-no-numbering",
            "-force-html",
            "-no-references",
        ]


class html_lynx(SubprocessRenderMixin, HTMLRenderer):
    """Renderers HTML using `lynx`."""

    cmd = "lynx"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        self.args = ["-dump", "-stdin", f"-width={self.width}"]


class html_links(SubprocessRenderMixin, HTMLRenderer):
    """Renderers HTML using `lynx`."""

    cmd = "links"

    use_tempfile = True

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        self.args = ["-width", self.width, "-dump"]


class html_mtable_py(PythonRenderMixin, HTMLRenderer):
    """Renders HTML tables using `mtable` by converting to markdown."""

    modules = ["mtable", "html5lib"]

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Initiates the renderer and selects a markdown renderer to use."""
        super().__init__(*args, **kwargs)
        self.markdown_renderer = MarkdownRenderer.select()

    def process(self, data: "str") -> "Union[bytes, str]":
        """Converts HTML tables to markdown with `mtable`.

        The resulting markdown is rendered using rich.

        Args:
            data: An HTML string.

        Returns:
            An ANSI string representing the rendered input.

        """
        from mtable import MarkupTable  # type: ignore

        return self.markdown_renderer.render(
            data="\n\n".join([table.to_md() for table in MarkupTable.from_html(data)]),
            width=self.width,
            height=self.height,
        )


class html_fallback_py(HTMLRenderer):
    """This uses `HTMLParser` from the standard library to strip html tags.

    This produces poor output, but does not require any python dependencies or
    external commands, thus it is the last resort for rendering HTML.
    """

    stripper = None

    @classmethod
    def validate(cls) -> "bool":
        """Always return True as `html.parser` is in the standard library."""
        return True

    def load(self, data: "str") -> "None":
        """Instantiate a class to strip HTML tags.

        This is assigned to the class on first load rather than a specific
        instance, so it can be reused.

        Args:
            data: An HTML string.

        """
        from html.parser import HTMLParser

        if self.stripper is None:

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

            self.stripper = HTMLStripper()

    def process(self, data: "str") -> "Union[bytes, str]":
        """Strip tags from HTML data.

        Args:
            data: A string of HTML data.

        Returns:
            An ANSI string representing the rendered input.

        """
        import re
        from html.parser import HTMLParser

        assert isinstance(self.stripper, HTMLParser)
        self.stripper.feed(data)
        data = self.stripper.get_data()
        data = "\n".join([x.strip() for x in data.strip().split("\n")])
        data = re.sub("\n\n\n+", "\n\n", data)
        return data
