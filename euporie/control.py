# -*- coding: utf-8 -*-
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.layout.controls import UIContent, UIControl

from euporie.render import HTMLRenderer, ImageRenderer, RichRenderer, SVGRenderer

from .text import ANSI


class Control(UIControl):
    """Displays the output of a renderer re-draws it's contents on resize."""

    def __init__(self, data, render_args={}):
        self.data = data
        self.render_args = render_args

        self.renderer_instance = self.renderer.select()
        self.rendered_lines = None

        self._format_cache = SimpleCache(maxsize=20)
        self._content_cache = SimpleCache(maxsize=20)

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix,
    ):
        if not self.rendered_lines:
            self.rendered_lines = self._format_cache.get(
                (width, max_available_height),
                lambda: self.render(width, max_available_height),
            )
        return len(self.rendered_lines)

    def create_content(self, width, height):

        self.rendered_lines = self._format_cache.get(
            (width,),
            lambda: self.render(width, height),
        )

        def get_content():
            return UIContent(
                get_line=lambda i: ANSI(self.rendered_lines[i]).__pt_formatted_text__(),
                line_count=len(self.rendered_lines),
            )

        return self._content_cache.get((width,), get_content)

    def render(self, width, height):
        result = self.renderer_instance.render(
            self.data, width=width, height=height, render_args=self.render_args
        )
        if isinstance(result, str):
            result = result.rstrip().split("\n")
        return result


class RichControl(Control):
    renderer = RichRenderer


class HTMLControl(Control):
    renderer = HTMLRenderer


class ImageControl(Control):
    renderer = ImageRenderer

    def create_content(self, width, height):
        cell_obscured = self.render_args["cell"].obscured()
        self.rendered_lines = self._format_cache.get(
            (cell_obscured, width),
            lambda: self.render(width, height),
        )

        def get_content():
            return UIContent(
                get_line=lambda i: ANSI(self.rendered_lines[i]).__pt_formatted_text__(),
                line_count=len(self.rendered_lines),
            )

        return self._content_cache.get((cell_obscured, width), get_content)


class SVGControl(ImageControl):
    renderer = SVGRenderer
