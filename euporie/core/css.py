"""Contains markdown-specific CSS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.apptk.application.current import get_app
from euporie.apptk.filters.base import Condition
from euporie.apptk.filters.utils import to_filter

from euporie.apptk.formatted_text.html import CssSelector

if TYPE_CHECKING:
    from euporie.apptk.formatted_text.html import CssSelectors


# Special CSS for Jupyter notebook outputs
NOTEBOOK_CSS: CssSelectors = {
    to_filter(True): {
        # Dataframes for Jupyter
        ((CssSelector(item="table.dataframe"),),): {
            "border_top_width": "0 !important",
            "border_left_width": "0 !important",
            "border_bottom_width": "0 !important",
            "border_right_width": "0 !important",
            "border_collapse": "collapse",
            "_pt_class": "dataframe",
        },
        (
            (CssSelector(item="table.dataframe"), CssSelector(item="td")),
            (CssSelector(item="table.dataframe"), CssSelector(item="th")),
        ): {
            "border_top_width": "0",
            "border_left_width": "0",
            "border_bottom_width": "0",
            "border_right_width": "0",
            "padding_left": "1em",
        },
        (
            (
                CssSelector(item="table.dataframe"),
                CssSelector(item="th"),
            ),
        ): {
            "_pt_class": "dataframe,th",
        },
        (
            (
                CssSelector(item="table.dataframe"),
                CssSelector(item="th", pseudo=":first-child"),
            ),
            (
                CssSelector(item=".dataframe"),
                CssSelector(item="th", pseudo=":last-child"),
            ),
            (
                CssSelector(item=".dataframe"),
                CssSelector(item="td", pseudo=":last-child"),
            ),
        ): {"padding_right": "1em"},
        ((CssSelector(item="table.dataframe"), CssSelector(item="td")),): {
            "_pt_class": "dataframe,td"
        },
        (
            (
                CssSelector(item="table.dataframe"),
                CssSelector(item="tr", pseudo=":nth-child(odd)"),
                CssSelector(item="td"),
            ),
        ): {"_pt_class": "dataframe,row-odd,td"},
    },
    Condition(lambda: get_app().config.wrap_cell_outputs): {
        ((CssSelector(item="table.dataframe"),),): {"max_width": "100%"},
    },
}

MARKDOWN_CSS: CssSelectors = {
    Condition(lambda: get_app().config.wrap_cell_outputs): {
        (
            (
                CssSelector(item="pre"),
                CssSelector(comb=">", item="code"),
            ),
        ): {"max_width": "100%", "overflow_x": "auto"},
    },
}
