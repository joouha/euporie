#!/usr/bin/env python
"""Example demonstrating extended style attributes in apptk.

This example shows the additional style attributes available in apptk
beyond what prompt_toolkit provides, including:

- Various underline styles (double, curvy, dotted, dashed)
- Overline
- Fast blink
- Underline color
- Hyperlinks (OSC 8)

Run this example to see all the extended styles rendered in your terminal.
Note: Not all terminals support all of these features.
"""

from __future__ import annotations

from apptk.formatted_text import FormattedText
from apptk.shortcuts import print_formatted_text


def main() -> None:
    """Print examples of all extended style attributes."""
    print_formatted_text(
        FormattedText(
            [
                ("", "\n"),
                ("bold", "Extended Style Attributes in apptk"),
                ("", "\n"),
                ("", "=" * 40),
                ("", "\n\n"),
                # Standard underline for comparison
                ("underline", "Standard underline"),
                ("", " - basic underline\n"),
                # Double underline
                ("doubleunderline", "Double underline"),
                ("", " - two lines under text\n"),
                # Curvy/wavy underline (often used for spell check errors)
                ("curvyunderline", "Curvy underline"),
                ("", " - wavy line (spell check style)\n"),
                # Dotted underline
                ("dottedunderline", "Dotted underline"),
                ("", " - dotted line under text\n"),
                # Dashed underline
                ("dashedunderline", "Dashed underline"),
                ("", " - dashed line under text\n"),
                ("", "\n"),
                # Overline
                ("overline", "Overline text"),
                ("", " - line above text\n"),
                ("", "\n"),
                # Fast blink (not widely supported)
                ("blinkfast", "Fast blink"),
                ("", " - rapid blinking (if supported)\n"),
                ("", "\n"),
                # Underline with color
                ("underline ul:red", "Red underline"),
                ("", " - colored underline\n"),
                ("curvyunderline ul:#ff8800", "Orange curvy underline"),
                ("", " - colored wavy line\n"),
                ("doubleunderline ul:#00ff00", "Green double underline"),
                ("", " - colored double line\n"),
                ("", "\n"),
                # Hyperlinks
                ("link:https://github.com/joouha/euporie", "Euporie on GitHub"),
                ("", " - clickable hyperlink (Ctrl+click or Cmd+click)\n"),
                ("bold fg:blue underline link:https://example.com", "Styled hyperlink"),
                ("", " - link with additional styling\n"),
                ("", "\n"),
                # Combinations
                ("bold italic curvyunderline ul:red fg:yellow", "Combined styles"),
                ("", " - multiple attributes together\n"),
                ("reverse overline", "Reverse with overline"),
                ("", " - inverted colors with line above\n"),
                ("", "\n"),
                (
                    "dim",
                    "Terminal support varies - some styles may not render correctly.",
                ),
                ("", "\n"),
            ]
        )
    )


if __name__ == "__main__":
    main()
