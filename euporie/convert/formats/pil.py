"""Contains functions which convert data to PIL format."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PIL import Image  # type: ignore

from euporie.convert.base import register
from euporie.convert.util import have_modules

if TYPE_CHECKING:
    from typing import Optional


log = logging.getLogger(__name__)


def set_background(image: "Image", bg_color: "Optional[str]" = None) -> "bytes":
    """Removes the alpha channel from an image and set the background colour."""
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        alpha = image.convert("RGBA").getchannel("A")
        bg = Image.new("RGBA", image.size, bg_color)
        bg.paste(image, mask=alpha)
        image = bg
    image = image.convert("P", palette=Image.ADAPTIVE, colors=16).convert(
        "RGB", palette=Image.ADAPTIVE, colors=16
    )
    return image


@register(
    from_=("png", "jpeg"),
    to="pil",
    filter_=have_modules("PIL"),
)
def png_to_pil_py(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "Image":
    """Convert PNG to a pillow image using :py:mod:`PIL`."""
    import io

    from PIL import Image  # type: ignore

    try:
        image = Image.open(io.BytesIO(data))
    except IOError:
        log.error("Could not load image.")
    else:
        return image
