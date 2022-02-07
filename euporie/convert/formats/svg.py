"""Contains function which convert SVGs to other formats."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.app.current import get_base_app as get_app
from euporie.convert.base import register
from euporie.convert.util import call_subproc, commands_exist, have_modules

if TYPE_CHECKING:
    from typing import Any, Optional


@register(
    from_="svg",
    to="ansi",
    filter_=commands_exist("chafa"),
)
def svg_to_ansi_chafa(
    data: "str",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts SVG data to ANSI text using :command:`chafa`."""
    cmd: "list[Any]" = ["chafa", "--format=symbols"]
    if cols is not None and rows is not None:
        cmd += [f"--size={cols}x{rows}"]
    cmd += ["--stretch", "-"]
    return call_subproc(data.encode(), cmd).decode()


@register(
    from_="svg",
    to="png",
    filter_=commands_exist("convert", "magick"),
)
def svg_to_png_imagemagick(
    data: "str",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "bytes":
    """Converts SVG data to PNG bytes using ``imagemagick``."""
    cmd: "list[Any]" = ["convert"]
    if cols is not None:
        px, _ = get_app().term_info.cell_size_px
        cmd += ["-geometry", f"{int(cols * px)}"]
    bg = bg or get_app().term_info.background_color.value
    if bg is not None:
        cmd += ["-background", bg]
    cmd += ["-", "PNG:-"]
    return call_subproc(data.encode(), cmd)


@register(
    from_="svg",
    to="sixel",
    filter_=commands_exist("convert", "magick"),
)
def svg_to_sixel_imagemagick(
    data: "str",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts SVG to sixels using ``imagemagick``."""
    cmd: "list[Any]" = ["convert"]
    bg = bg or get_app().term_info.background_color.value
    if bg is not None:
        cmd += ["-background", bg]
    if cols is not None:
        px, _ = get_app().term_info.cell_size_px
        cmd += ["-geometry", f"{int(cols * px)}"]
    cmd += ["-", "sixel:-"]
    return call_subproc(data.encode(), cmd).decode()


@register(
    from_="svg",
    to="png",
    filter_=have_modules("cairosvg"),
)
def svg_to_png_py_cairosvg(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert SVG to PNG using :py:mod:`cairosvg`."""
    import cairosvg  # type: ignore

    return cairosvg.surface.PNGSurface.convert(data, write_to=None)
