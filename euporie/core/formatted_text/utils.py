"""Utilities for manipulating formatted text."""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Optional, cast

from prompt_toolkit.formatted_text.base import OneStyleAndTextTuple, StyleAndTextTuples
from prompt_toolkit.formatted_text.utils import (
    fragment_list_to_text,
    fragment_list_width,
    split_lines,
)
from prompt_toolkit.utils import get_cwidth
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from euporie.core.border import GridStyle, Padding, Thin


class FormattedTextAlign(Enum):
    """Alignment of formatted text."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"


def last_line_length(ft: StyleAndTextTuples) -> int:
    """Calculate the length of the last line in formatted text."""
    line: StyleAndTextTuples = []
    for style, text, *_ in ft[::-1]:
        index = text.find("\n")
        line.append((style, text[index + 1 :]))
        if index > -1:
            break
    return fragment_list_width(line)


def max_line_width(ft: StyleAndTextTuples) -> int:
    """Calculate the length of the longest line in formatted text."""
    return max(fragment_list_width(line) for line in split_lines(ft))


def fragment_list_to_words(
    fragments: "StyleAndTextTuples", sep: "str" = " "
) -> "Iterable[OneStyleAndTextTuple]":
    """Split formatted text into word fragments."""
    for style, string, *mouse_handler in fragments:
        parts = string.split(sep)
        for part in parts[:-1]:
            yield cast("OneStyleAndTextTuple", (style, part, *mouse_handler))
            yield cast("OneStyleAndTextTuple", (style, " ", *mouse_handler))
        yield cast("OneStyleAndTextTuple", (style, parts[-1], *mouse_handler))


def apply_style(ft: StyleAndTextTuples, style: str) -> StyleAndTextTuples:
    """Apply a style to formatted text."""
    return [
        (
            f"{fragment_style} {style}"
            if "[ZeroWidthEscape]" not in fragment_style
            else fragment_style,
            text,
        )
        for (fragment_style, text, *_) in ft
    ]


def strip(
    ft: StyleAndTextTuples,
    left: bool = True,
    right: bool = True,
    char: Optional[str] = None,
) -> StyleAndTextTuples:
    """Strip whitespace (or a given character) from the ends of formatted text.

    Args:
        ft: The formatted text to strip
        left: If :py:const:`True`, strip from the left side of the input
        right: If :py:const:`True`, strip from the right side of the input
        char: The character to strip. If :py:const:`None`, strips whitespace

    Returns:
        The stripped formatted text

    """
    result = ft[:]
    for toggle, index, strip_func in [(left, 0, str.lstrip), (right, -1, str.rstrip)]:
        if result and toggle:
            text = strip_func(result[index][1], char)
            while result and not text:
                del result[index]
                if not result:
                    break
                text = strip_func(result[index][1], char)
            if result and "[ZeroWidthEscape]" not in result[index][0]:
                result[index] = (result[index][0], text)
    return result


def truncate(
    ft: StyleAndTextTuples,
    width: int,
    style: str = "",
    placeholder: str = "…",
) -> StyleAndTextTuples:
    """Truncates all lines at a given length.

    Args:
        ft: The formatted text to truncate
        width: The width at which to truncate the text
        style: The style to apply to the truncation placeholder. The style of the
            truncated text will be used if not provided
        placeholder: The string that will appear at the end of a truncated line

    Returns:
        The truncated formatted text

    """
    result: StyleAndTextTuples = []
    phw = sum(get_cwidth(c) for c in placeholder)
    for line in split_lines(ft):
        used_width = 0
        for item in line:
            fragment_width = sum(
                get_cwidth(c) for c in item[1] if "[ZeroWidthEscape]" not in item[0]
            )
            if used_width + fragment_width > width - phw:
                remaining_width = width - used_width - fragment_width - phw
                result.append((item[0], item[1][:remaining_width]))
                result.append((style or item[0], placeholder))
                break
            else:
                result.append(item)
                used_width += fragment_width
        result.append(("", "\n"))
    result.pop()
    return result


def wrap(
    ft: StyleAndTextTuples,
    width: int,
    style: str = "",
    placeholder: str = "…",
    left: "int" = 0,
    truncate_long_words: "bool" = True,
) -> StyleAndTextTuples:
    """Wraps formatted text at a given width.

    If words are longer than the given line they will be truncated

    Args:
        ft: The formatted text to wrap
        width: The width at which to wrap the text
        style: The style to apply to the truncation placeholder
        placeholder: The string that will appear at the end of a truncated line
        left: The starting position within the first list
        truncate_long_words: If :const:`True` words longer than a line will be
            truncated

    Returns:
        The wrapped formatted text
    """
    result: StyleAndTextTuples = []
    lines = list(split_lines(ft))
    output_line = 0
    for i, line in enumerate(lines):
        if fragment_list_width(line) <= width - left:
            result += line
            if i < len(lines) - 1:
                result.append(("", "\n"))
            output_line += 1
            left = 0
        else:
            for item in fragment_list_to_words(line):
                # Skip empty fragments
                if item[1] == "":
                    continue
                fragment_width = sum(
                    get_cwidth(c) for c in item[1] if "[ZeroWidthEscape]" not in item[0]
                )
                # Start a new line - we are at the end of the current output line
                if left + fragment_width > width and left > 0:
                    # Remove trailing whitespace
                    result = strip(result, left=False)
                    result.append(("", "\n"))
                    output_line += 1
                    left = 0
                # Strip left-hand whitespace from a word at the start of a line
                # if output_line != 0 and left == 0:
                if left == 0:
                    item = (item[0], item[1].lstrip(" "))
                # Truncate words longer than a line
                if truncate and left == 0 and fragment_width > width - left:
                    result += truncate([item], width - left, style, placeholder)
                    left += fragment_width
                # Otherwise just add the word to the line
                else:
                    result.append(item)
                    left += fragment_width

    return result


def align(
    how: FormattedTextAlign,
    ft: StyleAndTextTuples,
    width: Optional[int] = None,
    style: str = "",
    placeholder: str = "…",
) -> StyleAndTextTuples:
    """Align formatted text at a given width.

    Args:
        how: The alignment direction
        ft: The formatted text to strip
        width: The width to which the output should be padded. If :py:const:`None`, the
            length of the longest line is used
        style: The style to apply to the padding
        placeholder: The string that will appear at the end of a truncated line

    Returns:
        The aligned formatted text

    """
    style = f"{style} nounderline"
    lines = split_lines(ft)
    if width is None:
        lines = [strip(line) for line in split_lines(ft)]
        width = max(fragment_list_width(line) for line in lines)
    result: StyleAndTextTuples = []
    for line in lines:
        line_width = fragment_list_width(line)
        # Truncate the line if it is too long
        if line_width > width:
            result += truncate(line, width, style, placeholder)
        else:
            pad_left = pad_right = 0
            if how == FormattedTextAlign.CENTER:
                pad_left = (width - line_width) // 2
                pad_right = width - line_width - pad_left
            elif how == FormattedTextAlign.LEFT:
                pad_right = width - line_width
            elif how == FormattedTextAlign.RIGHT:
                pad_left = width - line_width
            if pad_left:
                result.append((style, " " * pad_left))
            result += line
            if pad_right:
                result.append((style, " " * pad_right))
        result.append((style, "\n"))
    result.pop()
    return result


def indent(
    ft: StyleAndTextTuples,
    margin: str = " ",
    style: str = "",
    skip_first: bool = False,
) -> StyleAndTextTuples:
    """Indents formatted text with a given margin.

    Args:
        ft: The formatted text to strip
        margin: The margin string to add
        style: The style to apply to the margin
        skip_first: If :py:const:`True`, the first line is skipped

    Returns:
        The indented formatted text

    """
    result: StyleAndTextTuples = []
    for i, line in enumerate(split_lines(ft)):
        if not (i == 0 and skip_first):
            result.append((style, margin))
        result += line
        result.append(("", "\n"))
    result.pop()
    return result


def add_border(
    ft: StyleAndTextTuples,
    width: "Optional[int]" = None,
    style: str = "",
    border: "GridStyle" = Thin.grid,
    padding: "Optional[Padding]" = None,
) -> StyleAndTextTuples:
    """Adds a border around formatted text.

    Args:
        ft: The formatted text to enclose with a border
        width: The target width including the border and padding
        style: The style to apply to the border
        border: The grid style to use for the border
        padding: The width of spacing to apply between the content and the border

    Returns:
        The indented formatted text

    """
    if padding is None:
        padding = Padding(0, 1, 0, 1)
    if isinstance(padding, int):
        padding = Padding(padding, padding, padding, padding)
    if len(padding) == 2:
        padding = Padding(padding[0], padding[1], padding[0], padding[1])
    # `None` is not permitted for padding here
    padding = Padding(
        padding[0] or 0, padding[1] or 0, padding[2] or 0, padding[3] or 0
    )

    max_lw = max_line_width(ft)
    if width is None:
        width = max_lw + (padding.right or 0) + (padding.left or 0) + 2

    inner_width = width - 2
    # Ensure all lines are the same length
    ft = align(
        FormattedTextAlign.LEFT,
        ft,
        width=inner_width - (padding.right or 0) - (padding.left or 0),
        style=style,
    )

    result: StyleAndTextTuples = []

    style = f"{style} nounderline"

    result.extend(
        [
            (
                f"{style} class:border,left,top",
                border.TOP_LEFT,
            ),
            (
                f"{style} class:border,top",
                border.TOP_MID * inner_width,
            ),
            (
                f"{style} class:border,right,top",
                border.TOP_RIGHT + "\n",
            ),
        ]
    )
    for _ in range(padding.top or 0):
        result.extend(
            [
                (f"{style} class:border,left", border.MID_LEFT),
                (style, " " * inner_width),
                (f"{style} class:border,right", border.MID_RIGHT + "\n"),
            ]
        )
    for line in split_lines(ft):
        result.extend(
            [
                (f"{style} class:border,left", border.MID_LEFT),
                (style, " " * (padding.left or 0)),
                *line,
                (style, " " * (padding.right or 0)),
                (f"{style} class:border,right", border.MID_RIGHT + "\n"),
            ]
        )
    for _ in range(padding.bottom or 0):
        result.extend(
            [
                (f"{style} class:border,left", border.MID_LEFT),
                (style, " " * inner_width),
                (f"{style} class:border,right", border.MID_RIGHT + "\n"),
            ]
        )
    result.extend(
        [
            (
                f"{style} class:border,left,bottom",
                border.BOTTOM_LEFT,
            ),
            (
                f"{style} class:border,bottom",
                border.BOTTOM_MID * inner_width,
            ),
            (
                f"{style} class:border,right,bottom",
                border.BOTTOM_RIGHT + "\n",
            ),
        ]
    )
    return result


def lex(ft: StyleAndTextTuples, lexer_name: str) -> StyleAndTextTuples:
    """Format formatted text using a named :py:mod:`pygments` lexer."""
    from prompt_toolkit.lexers.pygments import _token_cache

    text = fragment_list_to_text(ft)
    try:
        lexer = get_lexer_by_name(lexer_name)
    except ClassNotFound:
        return ft
    else:
        return [(_token_cache[t], v) for _, t, v in lexer.get_tokens_unprocessed(text)]
