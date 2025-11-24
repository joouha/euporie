"""Defines a logo widget."""

from __future__ import annotations

from prompt_toolkit.layout.containers import Window, WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets.base import Label

from euporie.core import __version__

logo_micro = Label(" ⚈ ", style="class:menu,logo", width=3, dont_extend_width=True)

logo_medium = Window(
    content=FormattedTextControl(
        [
            ("fg:white", "•"),
            ("fg:darkred", "▗▆██▆▖"),
            ("fg:yellow", "*"),
            ("", "       \n"),
            ("", " "),
            ("fg:darkred", "████"),
            ("fg:darkred bg:black reverse", "●"),
            ("fg:darkred", "█"),
            ("bold", " euporie\n"),
            ("fg:orange", "."),
            ("fg:darkred", "▝🮅██🮅▘"),
            ("", "    "),
            ("fg:#888 dim", f"v{__version__}"),
        ]
    ),
    height=3,
    dont_extend_width=True,
    wrap_lines=False,
    align=WindowAlign.LEFT,
)

"""
    ⢠⣶⣿⣿⣶⡄  ▗▆██▆▖  ▗▆██▆▖  🭊🭂██🭍🬿  🭉🭂██🭍🬾  🬞🬹██🬹🬏
    ⣿⣿⣿⣿⣉⣿  ████𜶮█  ████●█  ████●█  ▐███●▌  🬫██🯩🯫🬛
    ⠘⠿⣿⣿⠿⠃  ▝🮅██🮅▘  ▝🮅██🮅▘  🭥🭓██🭞🭚  🭤🭓██🭞🭙  🬁🬎██🬎🬀

"""
