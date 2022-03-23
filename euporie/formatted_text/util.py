from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.formatted_text.utils import (
    fragment_list_to_text,
    fragment_list_width,
    split_lines,
)
from pygments.util import ClassNotFound  # type: ignore
from pygments.lexers import get_lexer_by_name  # type: ignore
from prompt_toolkit.lexers.pygments import _token_cache

from euporie.box import SquareBorder


def last_line_length(ft):
    line = []
    for style, text in ft[::-1]:
        index = text.find("\n")
        line.append((style, text[index + 1 :]))
        if index > -1:
            break
    return fragment_list_width(line)


def fragment_list_to_words(fragments):
    for style, string, *mouse_handler in fragments:
        parts = string.split(" ")
        for part in parts[:-1]:
            yield (style, part, *mouse_handler)
            yield (style, " ", *mouse_handler)
        yield (style, parts[-1], *mouse_handler)


def apply_style(ft, style):
    return [
        (
            f"{fragment_style} {style}"
            if "[ZeroWidthEscape]" not in fragment_style
            else fragment_style,
            text,
        )
        for (fragment_style, text, *_) in ft
    ]


def strip(ft, left=True, right=True, char: "Optional[str]" = None):
    result = ft[:]
    for toggle, index, strip_func in [(left, 0, str.lstrip), (right, -1, str.rstrip)]:
        if toggle:
            while result and not (text := strip_func(result[index][1], char)):
                del result[index]
            if result and "[ZeroWidthEscape]" not in result[index][0]:
                result[index] = (result[index][0], text)
    return result


def wrap(ft, width):
    result = []
    lines = list(split_lines(ft))
    for i, line in enumerate(lines):
        if fragment_list_width(line) <= width:
            result += line
            if i < len(lines) - 1:
                result.append(("", "\n"))
        else:
            used_width = 0
            for item in fragment_list_to_words(line):
                fragment_width = sum(
                    get_cwidth(c) for c in item[1] if "[ZeroWidthEscape]" not in item[0]
                )
                if used_width + fragment_width > width:
                    # Remove trailing whitespace
                    result = strip(result, left=False)
                    result.append(("", "\n"))
                    used_width = 0
                # Truncate if word longer than line
                if fragment_width > width:
                    result.append((item[0], item[1][: width - 1] + "…"))
                elif used_width == 0:
                    result += strip([item], right=False)
                else:
                    result.append(item)
                used_width += fragment_width
    return result


def align(how, ft, width, style=""):
    result = []
    for line in split_lines(ft):
        line_width = fragment_list_width(line)
        pad_left = pad_right = 0
        if how == "center":
            pad_left = (width - line_width) // 2
            pad_right = width - line_width - pad_left
        elif how == "left":
            pad_right = width - line_width
        elif how == "right":
            pad_left = width - line_width
        if pad_left:
            result.append((style, " " * pad_left))
        result += line
        if pad_right:
            result.append((style, " " * pad_right))
        result.append((style, "\n"))
    result.pop()
    return result


def indent(ft, margin=" ", style="", skip_first: "bool" = False):
    result = []
    for i, line in enumerate(split_lines(ft)):
        if not (i == 0 and skip_first):
            result.append((style, margin))
        result += line
        result.append(("", "\n"))
    result.pop()
    return result


def add_border(ft, width, style="", border=SquareBorder):
    ft = align("left", ft, width - 4)
    result = []
    result.append(
        (
            style,
            border.TOP_LEFT + border.HORIZONTAL * (width - 2) + border.TOP_RIGHT + "\n",
        )
    )
    for line in split_lines(ft):
        result += [
            (style, border.VERTICAL),
            ("", " "),
            *line,
            ("", " "),
            (style, border.VERTICAL + "\n"),
        ]
    result.append(
        (
            style,
            border.BOTTOM_LEFT + border.HORIZONTAL * (width - 2) + border.BOTTOM_RIGHT,
        )
    )
    return result


def lex(ft, lexer_name):
    text = fragment_list_to_text(ft)
    try:
        lexer = get_lexer_by_name(lexer_name)
    except ClassNotFound:
        return ft
    else:
        return [(_token_cache[t], v) for _, t, v in lexer.get_tokens_unprocessed(text)]
