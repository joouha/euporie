"""Contain functions which convert data to PIL format."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.core.convert.registry import register
from euporie.core.filters import have_modules

if TYPE_CHECKING:
    from typing import Any

    from PIL.Image import Image as PilImage

    from euporie.core.convert.datum import Datum


log = logging.getLogger(__name__)


def set_background(image: PilImage, bg: str | None = None) -> PilImage:
    """Remove the alpha channel from an image and set the background colour."""
    from PIL import Image

    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        alpha = image.convert("RGBA").getchannel("A")
        bg_img = Image.new("RGBA", image.size, bg or "#000")
        bg_img.paste(image, mask=alpha)
        image = bg_img
    return image.convert("P", palette=Image.Palette.ADAPTIVE, colors=16).convert(
        "RGB", palette=Image.Palette.ADAPTIVE, colors=16
    )


@register(
    from_=("png", "jpeg", "gif"),
    to="pil",
    filter_=have_modules("PIL"),
)
async def png_to_pil_py(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> PilImage:
    """Convert PNG to a pillow image using :py:mod:`PIL`."""
    import io

    from PIL import Image

    try:
        image = Image.open(io.BytesIO(datum.data))
        image.load()
    except OSError:
        log.error("Could not load image.")
        return Image.new(mode="P", size=(1, 1))
    else:
        return image


'''
def crop(data: PilImage, bbox: DiInt) -> PilImage:
    """Ctop a pillow image."""
    import io

    image = data.convert(
        to="pil",
        cols=full_width,
        rows=full_height,
    )
    if image is not None:
        cell_size_x, cell_size_y = self.app.cell_size_px
        # Downscale image to fit target region for precise cropping
        image.thumbnail((full_width * cell_size_x, full_height * cell_size_y))
        image = image.crop(
            (
                self.bbox.left * cell_size_x,  # left
                self.bbox.top * cell_size_y,  # top
                (self.bbox.left + cols) * cell_size_x,  # right
                (self.bbox.top + rows) * cell_size_y,  # bottom
            )
        )
        with io.BytesIO() as output:
            image.save(output, format="PNG")
            Datum(data=output.getvalue(), format="png")
'''
