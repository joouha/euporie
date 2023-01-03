"""Contains functions which convert data to PIL format."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.core.convert.base import register
from euporie.core.convert.utils import have_modules

if TYPE_CHECKING:
    from typing import Optional

    from PIL.Image import Image as PilImage
    from upath import UPath

log = logging.getLogger(__name__)


def set_background(image: "PilImage", bg_color: "Optional[str]" = None) -> "PilImage":
    """Removes the alpha channel from an image and set the background colour."""
    from PIL import Image

    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        alpha = image.convert("RGBA").getchannel("A")
        bg = Image.new("RGBA", image.size, bg_color or "#000")
        bg.paste(image, mask=alpha)
        image = bg
    image = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=16).convert(
        "RGB", palette=Image.Palette.ADAPTIVE, colors=16
    )
    return image


@register(
    from_=("png", "jpeg", "gif"),
    to="pil",
    filter_=have_modules("PIL"),
)
def png_to_pil_py(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "PilImage":
    """Convert PNG to a pillow image using :py:mod:`PIL`."""
    import io

    from PIL import Image

    try:
        image = Image.open(io.BytesIO(data))
    except OSError:
        log.error("Could not load image.")
        return Image.new(mode="P", size=(1, 1))
    else:
        return image
