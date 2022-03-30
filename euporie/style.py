"""Style related functions."""

from colorsys import hls_to_rgb, rgb_to_hls
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Dict, Union


@lru_cache
def color_series(
    n: "int" = 10, interval: "float" = 0.05, **kwargs: "Any"
) -> "Dict[str, Dict[Union[str, int], str]]":
    """Create a series of dimmed colours."""
    series: "Dict[str, Dict[Union[int, str], str]]" = {
        key: {"base": value} for key, value in kwargs.items()
    }

    for name, color in kwargs.items():
        color = color.lstrip("#")
        r, g, b = (
            int(color[0:2], 16) / 255,
            int(color[2:4], 16) / 255,
            int(color[4:6], 16) / 255,
        )
        hue, brightness, saturation = rgb_to_hls(r, g, b)

        for i in range(-n, n + 1):

            # Linear interpolation
            if i > 0:
                adj_brightness = brightness + (1 - brightness) / n * i
            else:
                adj_brightness = brightness + (brightness) / n * i

            r, g, b = hls_to_rgb(hue, adj_brightness, saturation)
            new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

            if brightness > 0.5:
                i *= -1
            series[name][i] = new_color

    return series
