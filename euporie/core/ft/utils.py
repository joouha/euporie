"""Utilities for manipulating formatted text."""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING, cast

from prompt_toolkit.formatted_text.utils import (
    fragment_list_to_text,
    split_lines,
    to_plain_text,
)
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.utils import get_cwidth
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from euporie.core.border import GridStyle, ThinGrid
from euporie.core.data_structures import DiBool, DiInt, DiStr

if TYPE_CHECKING:
    from collections.abc import Iterable

    from prompt_toolkit.formatted_text.base import (
        OneStyleAndTextTuple,
        StyleAndTextTuples,
    )

_ZERO_WIDTH_FRAGMENTS = ("[ZeroWidthEscape]", "[ReverseOverwrite]")


class FormattedTextAlign(Enum):
    """Alignment of formatted text."""

    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class FormattedTextVerticalAlign(Enum):
    """Vertical alignment of formatted text."""

    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


def fragment_list_width(fragments: StyleAndTextTuples) -> int:
    """Return the character width of this text fragment list.

    Takes double width characters into account, and ignore special fragments:
    * ZeroWidthEscape
    * ReverseOverwrite

    Args:
        fragments: List of ``(style_str, text)`` or
            ``(style_str, text, mouse_handler)`` tuples.

    Returns:
        The width of the fragment list
    """
    return sum(
        get_cwidth(c)
        for item in (
            frag
            for frag in fragments
            if not any(x in frag[0] for x in _ZERO_WIDTH_FRAGMENTS)
        )
        for c in item[1]
    )


def max_line_width(ft: StyleAndTextTuples) -> int:
    """Calculate the length of the longest line in formatted text."""
    return max(fragment_list_width(line) for line in split_lines(ft))


def last_char(ft: StyleAndTextTuples) -> str | None:
    """Retrieve the last character of formatted text."""
    for frag in reversed(ft):
        text = frag[1]
        for c in reversed(text):
            if c:
                return c
    return None


def fragment_list_to_words(
    fragments: StyleAndTextTuples, sep: str = " "
) -> Iterable[StyleAndTextTuples]:
    """Split formatted text into a list of word fragments which form words."""
    word: StyleAndTextTuples = []
    for style, string, *rest in fragments:
        parts = re.split(r"(?<=[\s\-\/])", string)
        if len(parts) == 1:
            word.append(cast("OneStyleAndTextTuple", (style, parts[0], *rest)))
        else:
            for part in parts[:-1]:
                word.append(cast("OneStyleAndTextTuple", (style, part, *rest)))
                yield word[:]
                word.clear()
            word.append(cast("OneStyleAndTextTuple", (style, parts[-1], *rest)))
    if word:
        yield word


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
    chars: str | None = None,
    only_unstyled: bool = False,
) -> StyleAndTextTuples:
    """Strip whitespace (or a given character) from the ends of formatted text.

    Args:
        ft: The formatted text to strip
        left: If :py:const:`True`, strip from the left side of the input
        right: If :py:const:`True`, strip from the right side of the input
        chars: The character to strip. If :py:const:`None`, strips whitespace
        only_unstyled: If :py:const:`True`, only strip unstyled fragments

    Returns:
        The stripped formatted text

    """
    result = ft[:]
    for toggle, index, strip_func in [(left, 0, str.lstrip), (right, -1, str.rstrip)]:
        if result and toggle:
            text = strip_func(result[index][1], chars)
            while result and not text:
                del result[index]
                if not result:
                    break
                text = strip_func(result[index][1], chars)
            if result and "[ZeroWidthEscape]" not in result[index][0]:
                result[index] = (result[index][0], text)
    return result


def strip_one_trailing_newline(ft: StyleAndTextTuples) -> StyleAndTextTuples:
    """Remove up to one trailing new-line character from formatted text."""
    for i in range(len(ft) - 1, -1, -1):
        frag = ft[i]
        if not frag[1]:
            continue
        if frag[1] == "\n":
            del ft[i]
        elif frag[1].endswith("\n"):
            ft[i] = (frag[0], frag[1][:-1])
        break
    return ft


def truncate(
    ft: StyleAndTextTuples,
    width: int,
    style: str = "",
    placeholder: str = "…",
    ignore_whitespace: bool = False,
) -> StyleAndTextTuples:
    """Truncate all lines at a given length.

    Args:
        ft: The formatted text to truncate
        width: The width at which to truncate the text
        style: The style to apply to the truncation placeholder. The style of the
            truncated text will be used if not provided
        placeholder: The string that will appear at the end of a truncated line
        ignore_whitespace: Do not use placeholder when truncating whitespace

    Returns:
        The truncated formatted text

    """
    lines = split_lines(ft)
    if max(fragment_list_width(line) for line in lines) <= width:
        return ft
    result: StyleAndTextTuples = []
    phw = sum(get_cwidth(c) for c in placeholder)
    for line in split_lines(ft):
        used_width = 0
        for i, item in enumerate(line):
            fragment_width = sum(
                get_cwidth(c)
                for c in item[1]
                if not any(x in item[0] for x in _ZERO_WIDTH_FRAGMENTS)
            )
            if (
                used_width + fragment_width > width - phw
                # Do not truncate if we have the exact width
                and used_width + fragment_width != width
            ):
                remaining_width = width - used_width - fragment_width - phw
                result.append((item[0], item[1][:remaining_width]))
                if ignore_whitespace and not fragment_list_to_text(line[i:]).strip():
                    result.append(
                        (item[0], item[1][remaining_width : remaining_width + 1])
                    )
                else:
                    result.append((style or item[0], placeholder))
                break
            else:
                result.append(item)
                used_width += fragment_width
        result.append(("", "\n"))
    result.pop()
    return result


def substring(
    ft: StyleAndTextTuples, start: int | None = None, end: int | None = None
) -> StyleAndTextTuples:
    """Extract a substring from formatted text."""
    output: StyleAndTextTuples = []
    if start is None:
        start = 0
    if end is None or start < 0 or end < 0:
        width = fragment_list_width(ft)
        if end is None:
            end = width
        if start < 0:
            start = width + start
        if end < 0:
            end = width + end
    x = 0
    for style, text, *extra in ft:
        if any(x in style for x in _ZERO_WIDTH_FRAGMENTS):
            frag_len = 0
        else:
            frag_len = sum(get_cwidth(c) for c in text)
        if (start <= x + frag_len <= end + frag_len) and (
            (text := text[max(0, start - x) : end - x]) or style
        ):
            output.append(cast("OneStyleAndTextTuple", (style, text, *extra)))
        x += frag_len
    return output


def wrap(
    ft: StyleAndTextTuples,
    width: int,
    style: str = "",
    placeholder: str = "…",
    left: int = 0,
    truncate_long_words: bool = True,
    strip_trailing_ws: bool = False,
    margin: str = "",
) -> StyleAndTextTuples:
    """Wrap formatted text at a given width.

    If words are longer than the given line they will be truncated

    Args:
        ft: The formatted text to wrap
        width: The width at which to wrap the text
        style: The style to apply to the truncation placeholder
        placeholder: The string that will appear at the end of a truncated line
        left: The starting position within the first line
        truncate_long_words: If :const:`True` words longer than a line will be
            truncated
        strip_trailing_ws: If :const:`True`, trailing whitespace will be removed from
            the ends of lines
        margin: Text to use a margin for the continuation of wrapped lines

    Returns:
        The wrapped formatted text
    """
    result: StyleAndTextTuples = []
    lines = list(split_lines(ft))
    n_lines = len(lines)
    output_line = 0
    for i, line in enumerate(lines):
        if fragment_list_width(line) <= width - left:
            result += line
            if i < len(lines) - 1:
                result.append(("", "\n"))
            output_line += 1
            left = 0
        else:
            for word in fragment_list_to_words(line):
                # Skip empty fragments
                # if word[0] == word[1] == "":
                #     continue

                fragment_width = fragment_list_width(word)

                # Start a new line - we are at the end of the current output line
                if left + fragment_width > width and left > 0:
                    # Add as much trailing whitespace as we can
                    if not strip_trailing_ws and (
                        trailing_ws := (not to_plain_text(word).strip())
                    ):
                        result.extend(substring(word, end=width - left))

                    # Remove trailing whitespace
                    if strip_trailing_ws:
                        result = strip(result, left=False)

                    # Start new line
                    result.append(("", "\n"))
                    if margin:
                        result.append((style, margin))
                    output_line += 1
                    left = len(margin)

                    # If we added trailing whitespace, process the next fragment
                    if not strip_trailing_ws and trailing_ws:
                        continue

                # Strip left-hand whitespace from a word at the start of a line
                # if output_line != 0 and left == 0:
                if left == 0:
                    word = strip(word, right=False)
                # Truncate words longer than a line
                if (
                    truncate_long_words
                    # Detect start of line
                    and result
                    and result[-1][1] == f"\n{margin}"
                    # Check the word is too long
                    and fragment_width > width - left
                ):
                    result += truncate(word, width - left, style, placeholder)
                    left += fragment_width
                # Otherwise just add the word to the line
                else:
                    result.extend(word)
                    left += fragment_width
            left = 0
            if i + 1 < n_lines:
                result.append(("", "\n"))

    if strip_trailing_ws:
        result = strip(result, left=False)

    return result


def align(
    ft: StyleAndTextTuples,
    how: FormattedTextAlign = FormattedTextAlign.LEFT,
    width: int | None = None,
    style: str = "",
    placeholder: str = "…",
    ignore_whitespace: bool = False,
) -> StyleAndTextTuples:
    """Align formatted text at a given width.

    Args:
        how: The alignment direction
        ft: The formatted text to strip
        width: The width to which the output should be padded. If :py:const:`None`, the
            length of the longest line is used
        style: The style to apply to the padding
        placeholder: The string that will appear at the end of a truncated line
        ignore_whitespace: If True, whitespace will be ignored

    Returns:
        The aligned formatted text

    """
    style = f"{style} nounderline"
    lines = split_lines(ft)
    if width is None:
        lines = [strip(line) if ignore_whitespace else line for line in split_lines(ft)]
        width = max(fragment_list_width(line) for line in lines)
    result: StyleAndTextTuples = []

    for line in lines:
        line_width = fragment_list_width(line)
        # Truncate the line if it is too long
        if line_width > width:
            result += truncate(line, width, style, placeholder, ignore_whitespace)
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
            result.extend(line)
            if pad_right:
                result.append((style, " " * pad_right))
        result.append((style, "\n"))
    result.pop()
    return result


def valign(
    ft: StyleAndTextTuples,
    how: FormattedTextVerticalAlign = FormattedTextVerticalAlign.MIDDLE,
    height: int | None = None,
    style: str = "",
) -> StyleAndTextTuples:
    """Align formatted text vertically."""
    if height is None:
        return ft
    lines = list(split_lines(ft))
    width = max(fragment_list_width(line) for line in lines)
    remaining = height - len(lines)
    if how == FormattedTextVerticalAlign.TOP:
        above = 0
        below = remaining
    elif how == FormattedTextVerticalAlign.MIDDLE:
        above = remaining // 2
        below = remaining - above
    else:
        above = remaining
        below = 0
    return [
        (style, ((" " * width) + "\n") * above),
        *ft,
        (style, ("\n" + (" " * width)) * below),
    ]


def join_lines(fragments: list[StyleAndTextTuples]) -> StyleAndTextTuples:
    """Join a list of lines of formatted text."""
    ft = []
    if fragments:
        for line in fragments[:-1]:
            ft.extend(line)
            ft.append(("", "\n"))
        lines = list(split_lines(fragments[-1]))
        for line in lines[:-1]:
            ft.extend(line)
            ft.append(("", "\n"))
        ft.extend(lines[-1])
    return ft


def pad(
    ft: StyleAndTextTuples,
    width: int | None = None,
    char: str = " ",
    style: str = "",
) -> StyleAndTextTuples:
    """Fill space at the end of lines."""
    if width is None:
        width = max_line_width(ft)
    filled_output = []
    for line in split_lines(ft):
        if (remaining := (width - fragment_list_width(line))) > 0:
            line.append((style + " nounderline", (char * remaining)))
        filled_output.append(line)
    return join_lines(filled_output)


def paste(
    ft_top: StyleAndTextTuples,
    ft_bottom: StyleAndTextTuples,
    row: int = 0,
    col: int = 0,
    transparent: bool = False,
) -> StyleAndTextTuples:
    """Pate formatted text on top of other formatted text."""
    ft: StyleAndTextTuples = []
    top_lines = dict(enumerate(split_lines(ft_top), start=row))
    for y, line_b in enumerate(split_lines(ft_bottom)):
        if y in top_lines:
            line_t = top_lines[y]
            line_t_width = fragment_list_width(line_t)
            ft += substring(line_b, 0, col)
            if transparent:
                chars_t = explode_text_fragments(line_t)
                chars_b = explode_text_fragments(
                    substring(line_b, col, col + line_t_width)
                )
                for char_t, char_b in zip(chars_t, chars_b):
                    if char_t[0] == "" and char_t[1] == " ":
                        ft.append(char_b)
                    else:
                        ft.append(char_t)
            else:
                ft += line_t
            ft += substring(line_b, col + line_t_width)
        else:
            ft += line_b
        ft.append(("", "\n"))

    if ft:
        ft.pop()

    return ft


def concat(
    ft_a: StyleAndTextTuples,
    ft_b: StyleAndTextTuples,
    baseline_a: int = 0,
    baseline_b: int = 0,
    style: str = "",
) -> tuple[StyleAndTextTuples, int]:
    """Concatenate two blocks of formatted text, aligning at a given baseline.

    Args:
        ft_a: The first block of formatted text to combine
        ft_b: The second block of formatted text to combine
        baseline_a: The row to use to align the first block of formatted text with the
            second, counted in lines down from the top of the block
        baseline_b: The row to use to align the second block of formatted text with the
            second, counted in lines down from the top of the block
        style: The style to use for any extra lines added

    Returns:
        A tuple containing the combined formatted text and the new baseline position
    """
    rows_a = len(list(split_lines(ft_a))) - 1
    rows_b = len(list(split_lines(ft_b))) - 1
    cols_a = max_line_width(ft_a)

    lines_above = max(baseline_a, baseline_b) - min(baseline_a, baseline_b)
    lines_below = max(rows_a - baseline_a, rows_b - baseline_b) - min(
        rows_a - baseline_a,
        rows_b - baseline_b,
    )

    if baseline_a < baseline_b:
        ft_a = [("", lines_above * "\n"), *ft_a]
    elif baseline_a > baseline_b:
        ft_b = [("", lines_above * "\n"), *ft_b]

    if rows_a - baseline_a < rows_b - baseline_b:
        ft_a = [*ft_a, ("", lines_below * "\n")]
    elif rows_a - baseline_a > rows_b - baseline_b:
        ft_b = [*ft_b, ("", lines_below * "\n")]

    ft = paste(
        ft_b,
        pad(ft_a, style=style),
        row=0,
        col=cols_a,
    )

    new_baseline = max(baseline_a, baseline_b)

    return ft, new_baseline


def indent(
    ft: StyleAndTextTuples,
    margin: str = " ",
    style: str = "",
    skip_first: bool = False,
) -> StyleAndTextTuples:
    """Indent formatted text with a given margin.

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
    width: int | None = None,
    style: str = "",
    border_grid: GridStyle = ThinGrid,
    border_visibility: DiBool | bool = True,
    border_style: DiStr | str = "",
    padding: DiInt | int = 0,
    padding_style: DiStr | str = "",
) -> StyleAndTextTuples:
    """Add a border around formatted text.

    Args:
        ft: The formatted text to enclose with a border
        width: The target width including the border and padding
        style: The style to apply to the content background
        border_grid: The grid style to use for the border
        border_visibility: Determines which edges should receive a border
        border_style: The style to apply to the border
        padding: The width of spacing to apply between the content and the border
        padding_style: The style to apply to the border

    Returns:
        The indented formatted text

    """
    if isinstance(border_visibility, bool):
        border_visibility = DiBool.from_value(border_visibility)
    if isinstance(padding, int):
        padding = DiInt.from_value(padding)
    if isinstance(border_style, str):
        border_style = DiStr.from_value(border_style)
    if isinstance(padding_style, str):
        padding_style = DiStr.from_value(padding_style)

    edge_width = (
        border_visibility.left + border_visibility.right + padding.left + padding.right
    )
    if width is None:
        inner_width = max_line_width(ft)
        width = inner_width + edge_width
    else:
        inner_width = width - edge_width

    # Ensure all lines are the same length
    if ft:
        ft = align(
            ft,
            FormattedTextAlign.LEFT,
            width=inner_width,
            style=style,
        )

    output: list[StyleAndTextTuples] = []

    base_style = f"{style} nounderline"

    # Add top row
    if border_visibility.top:
        new_line: StyleAndTextTuples = []
        if border_visibility.left:
            new_line.append(
                (
                    f"{base_style} class:border,left,top {border_style.top} {border_style.left}",
                    border_grid.TOP_LEFT,
                )
            )
        new_line.append(
            (
                f"{base_style} class:border,top {border_style.top}",
                border_grid.TOP_MID * (inner_width + padding.left + padding.right),
            )
        )
        if border_visibility.right:
            new_line.append(
                (
                    f"{base_style} class:border,right,top {border_style.top} {border_style.right}",
                    border_grid.TOP_RIGHT,
                )
            )
        output.append(new_line)
    # Add top padding
    for _ in range(padding.top or 0):
        new_line = []
        if border_visibility.left:
            new_line.append(
                (
                    f"{base_style} class:border,left {border_style.left}",
                    border_grid.MID_LEFT,
                )
            )
        if padding.top:
            new_line.append(
                (
                    f"{base_style} class:padding,top {padding_style.top}",
                    " " * (inner_width + padding.left + padding.right),
                )
            )
        if border_visibility.right:
            new_line.append(
                (
                    f"{base_style} class:border,right {border_style.right}",
                    border_grid.MID_RIGHT,
                )
            )
        output.append(new_line)
    # Add contents with left & right padding
    if ft:
        for line in split_lines(ft):
            new_line = []
            if border_visibility.left:
                new_line.append(
                    (
                        f"{base_style} class:border,left {border_style.left}",
                        border_grid.MID_LEFT,
                    )
                )
            if padding.left:
                new_line.append(
                    (
                        f"{base_style} class:padding,left {padding_style.left}",
                        " " * (padding.left or 0),
                    )
                )

            new_line.extend(line)
            if padding.right:
                new_line.append(
                    (
                        f"{base_style} class:padding,right {padding_style.right}",
                        " " * (padding.right or 0),
                    )
                )
            if border_visibility.right:
                new_line.append(
                    (
                        f"{base_style} class:border,right {border_style.right}",
                        border_grid.MID_RIGHT,
                    )
                )
            output.append(new_line)
    # Add bottom padding
    for _ in range(int(padding.bottom) or 0):
        new_line = []
        if border_visibility.left:
            new_line.append(
                (
                    f"{base_style} class:border,left {border_style.left}",
                    border_grid.MID_LEFT,
                )
            )
        if padding.bottom:
            new_line.append(
                (
                    f"{base_style} class:padding,bottom {padding_style.bottom}",
                    " " * (inner_width + padding.left + padding.right),
                )
            )
        if border_visibility.right:
            new_line.append(
                (
                    f"{base_style} class:border,right {border_style.right}",
                    border_grid.MID_RIGHT,
                )
            )
        output.append(new_line)
    # Add bottom row
    if border_visibility.bottom:
        new_line = []
        if border_visibility.left:
            new_line.append(
                (
                    f"{base_style} class:border,left,bottom {border_style.bottom} {border_style.left}",
                    border_grid.BOTTOM_LEFT,
                )
            )
        new_line.append(
            (
                f"{base_style} class:border,bottom {border_style.bottom}",
                border_grid.BOTTOM_MID * (inner_width + padding.left + padding.right),
            )
        )
        if border_visibility.right:
            new_line.append(
                (
                    f"{base_style} class:border,right,bottom {border_style.bottom} {border_style.right}",
                    border_grid.BOTTOM_RIGHT,
                )
            )

        output.append(new_line)

    return join_lines(output)


def lex(ft: StyleAndTextTuples, lexer_name: str) -> StyleAndTextTuples:
    """Format formatted text using a named :py:mod:`pygments` lexer."""
    from prompt_toolkit.lexers.pygments import _token_cache

    try:
        lexer = get_lexer_by_name(lexer_name)
    except ClassNotFound:
        return ft
    else:
        output: StyleAndTextTuples = []
        for style, text, *_rest in ft:
            for _, t, v in lexer.get_tokens_unprocessed(text):
                output.append((f"{style} {_token_cache[t]}", v))
        return output


def apply_reverse_overwrites(ft: StyleAndTextTuples) -> StyleAndTextTuples:
    """Write fragments tagged with "[ReverseOverwrite]" over text to their left."""

    def _apply_overwrites(
        overwrites: StyleAndTextTuples, transformed_line: StyleAndTextTuples
    ) -> tuple[StyleAndTextTuples, StyleAndTextTuples]:
        """Pate `overwrites` over the end of `transformed_line`."""
        # Remove the ``[ReverseOverwrite]`` from the overwrite fragments
        top = cast(
            "StyleAndTextTuples",
            [(x[0].replace("[ReverseOverwrite]", ""), *x[1:]) for x in overwrites],
        )
        top_width = fragment_list_width(top)
        if fragment_list_width(transformed_line) >= top_width:
            # Replace the end of the line with the overwrite-fragments if the overwrite
            # -fragments are shorter than the line
            transformed_line = [*substring(transformed_line, 0, -top_width), *top]
        else:
            # Otherwise, replace the whole line with the overwrites
            transformed_line = overwrites[:]
        overwrites.clear()
        return overwrites, transformed_line

    transformed_lines = []
    for untransformed_line in split_lines(ft):
        overwrites = []
        transformed_line: StyleAndTextTuples = []
        for frag in untransformed_line:
            # Collect overwrite fragments
            if "[ReverseOverwrite]" in frag[0]:
                overwrites.append(frag)
                continue
            # If we have any overwrite-fragments, apply them on top of the current line
            if overwrites:
                overwrites, transformed_line = _apply_overwrites(
                    overwrites, transformed_line
                )
            # Collect non-overwrite fragments
            transformed_line.append(frag)
        # Add this list to
        transformed_lines.append(transformed_line)
    return join_lines(transformed_lines)
