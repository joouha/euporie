"""Style related functions."""

from functools import lru_cache
from typing import TYPE_CHECKING

from prompt_toolkit.styles import DEFAULT_ATTRS, AdjustBrightnessStyleTransformation

if TYPE_CHECKING:
    from typing import Any, Dict


@lru_cache
def color_series(
    n: "int" = 6, interval: "float" = 0.05, **kwargs: "Any"
) -> "Dict[str, Dict[int, str]]":
    """Create a series of dimmed colours."""
    series: "Dict[str, Dict[int, str]]" = {key: {} for key in kwargs.keys()}
    for i in range(n):
        tr = AdjustBrightnessStyleTransformation(
            min_brightness=interval * i, max_brightness=1 - (interval * i)
        )
        for name, color in kwargs.items():
            series[name][i] = "#{}".format(
                tr.transform_attrs(
                    DEFAULT_ATTRS._replace(color=color.lstrip("#"))
                ).color
            )
    return series
