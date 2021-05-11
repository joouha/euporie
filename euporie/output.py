# -*- coding: utf-8 -*-
from pathlib import PurePath

from prompt_toolkit.layout import Container, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Label, TextArea
from rich.markdown import Markdown

from euporie import mdtable  # noqa F401
from euporie.config import config
from euporie.control import HTMLControl, ImageControl, RichControl, SVGControl
from euporie.text import ANSI

BLING_SCORES = {
    "image/*": 0,
    "text/html": 1,
    "text/x-markdown": 2,
    "text/x-python-traceback": 3,
    "text/stderr": 4,
    "text/*": 5,
    "*": 6,
}


def bling(item):
    mime, _ = item
    for bling_path, score in BLING_SCORES.items():
        if PurePath(mime).match(bling_path):
            return score


class Output:
    def __init__(self, index, json, parent=None):
        self.index = index
        self.json = json
        self.parent = parent
        self.style = ""
        self.content = None

        # Sort data first so there is more bling first
        for mime, datum in sorted(self.data.items(), key=bling):

            mime_path = PurePath(mime)

            if mime_path.match("image/svg+xml"):
                control = SVGControl(
                    datum,
                    render_args=dict(cell=self.parent, output_index=index),
                )
                if control.renderer:
                    self.content = Window(control, height=control.rendered_lines)
                    break

            if mime_path.match("image/*"):
                control = ImageControl(
                    datum,
                    render_args=dict(cell=self.parent, output_index=index),
                )
                if control.renderer:
                    self.content = Window(control, height=control.rendered_lines)
                    break

            if mime_path.match("text/html"):
                control = HTMLControl(datum)
                if control.renderer:
                    self.content = Window(control, height=control.rendered_lines)
                    break
                else:
                    continue  # Use plain text rendering instead

            if mime_path.match("text/x-markdown"):
                control = RichControl(
                    Markdown(
                        datum,
                        code_theme=config.pygments_style,
                        inline_code_theme=config.pygments_style,
                    )
                )
                self.content = Window(control, height=control.rendered_lines)
                break

            if mime_path.match("text/x-python-traceback"):
                control = FormattedTextControl(ANSI(datum))
                self.content = Window(control)
                break

            if mime_path.match("text/stderr"):
                self.content = TextArea(
                    datum.rstrip(), wrap_lines=True, style="bg:darkred"
                )
                break

            if mime_path.match("text/*"):
                # Use formatted text so ansi colour codes are displayed as colours
                control = FormattedTextControl(ANSI(datum.rstrip()))
                self.content = Window(control, wrap_lines=True)
                break

        else:
            datum = sorted(self.data.items(), key=bling)[-1][1]
            self.content = Label(ANSI(str(datum).rstrip()))

    @property
    def data(self):
        output_type = self.json.get("output_type", "unknown")
        if output_type == "stream":
            return {f'text/{self.json.get("name")}': self.json.get("text")}
        elif output_type == "error":
            return {"text/x-python-traceback": "\n".join(self.json.get("traceback"))}
        else:
            return self.json.get("data", {})

    @property
    def metadata(self):
        return self.json.get("metadata", {})

    def get_key_bindings(self, *args, **kwargs):
        return self.content.get_key_bindings(*args, **kwargs)

    def get_children(self, *args, **kwargs):
        return self.content.get_children(*args, **kwargs)

    def preferred_width(self, *args, **kwargs):
        return self.content.preferred_width(*args, **kwargs)

    def preferred_height(self, *args, **kwargs):
        return self.content.preferred_height(*args, **kwargs)

    def write_to_screen(self, *args, **kwargs):
        return self.content.write_to_screen(*args, **kwargs)

    def reset(self, *args, **kwargs):
        return self.content.reset(*args, **kwargs)

    def __pt_container__(self) -> Container:
        return self.content
