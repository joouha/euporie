"""Defines borders."""

from abc import ABCMeta
from collections import defaultdict
from textwrap import dedent

## MASKS


def mask(chars):
    chars = dedent(chars)
    chars = chars.strip()
    chars += "\n" * (9 - chars.count("\n"))
    chars = chars.ljust(10)
    # Remove any spaces - no longer human viewable
    chars = "".join(chars.split())
    return [x == "x" for x in chars]


edge = mask(
    """
xxxx  xxx
x╋━x  x╈x
x┃ x  x╀x
xxxx  x┿x
      x╁x
      x╇x
xxxxxx╆╽╅x
x╊┽╂┾╉╼ ╾x
xxxxxx╄╿╃x
      x┷x
"""
)

top = mask(
    """
xxxx  xxx
┣╋━┫  ┢╈┪
┃┃ ┃  ┞╀┦
┗┻━┛  ┝┿┥
      ┟╁┧
      ┡╇┩
xxxxxx╆╽╅x
┠╊┽╂┾╉╼ ╾┨
┖┺┵┸┶┹╄╿╃┚
      ┕┷┙
"""
)


top = mask(
    """
xxxx  xxx
┣╋━┫  ┢╈┪
┃┃ ┃  ┞╀┦
┗┻━┛  ┝┿┥
      ┟╁┧
      ┡╇┩
xxxxxx╆╽╅x
┠╊┽╂┾╉╼ ╾┨
┖┺┵┸┶┹╄╿╃┚
      ┕┷┙
"""
)

bottom = mask(
    """
┏┳━┓  ┍┯┑
┣╋━┫  ┢╈┪
┃┃ ┃  ┞╀┦
xxxx  ┝┿┥
      ┟╁┧
      ┡╇┩
┎┲┭┰┮┱╆╽╅┒
┠╊┽╂┾╉╼ ╾┨
xxxxxx╄╿╃x
      xxx
"""
)

left = mask(
    """
x┳━┓  x┯┑
x╋━┫  x╈┪
x┃ ┃  x╀┦
x┻━┛  x┿┥
      x╁┧
      x╇┩
x┲┭┰┮┱╆╽╅┒
x╊┽╂┾╉╼ ╾┨
x┺┵┸┶┹╄╿╃┚
      x┷┙
"""
)

right = mask(
    """
┏┳━1  ┍┯1
┣╋━1  ┢╈1
┃┃ 1  ┞╀1
┗┻━1  ┝┿1
      ┟╁1
      ┡╇1
┎┲┭┰┮┱╆╽╅1
┠╊┽╂┾╉╼ ╾1
┖┺┵┸┶┹╄╿╃1
      ┕┷1
"""
)

verticals = mask(
    """
xx━x  ┍┯┑
xx━x  ┢╈┪
xx x  ┞╀┦
xx━x  ┝┿┥
      ┟╁┧
      ┡╇┩
x┲┭┰┮┱╆╽╅x
x╊┽╂┾╉╼ ╾x
x┺┵┸┶┹╄╿╃x
      ┕┷┙
    """
)

joins = mask(
    """
┏┳━┓  xxx
┣╋━┫  xxx
┃┃ ┃  xxx
┗┻━┛  xxx
      xxx
      xxx
xxxxxxxxxx
xxxxxxxxxx
xxxxxxxxxx
      xxx
"""
)


### STYLES


class BorderStyle(metaclass=ABCMeta):
    chars: str


class Hidden(BorderStyle):
    chars = ""


# This is the default border style
class Thin(BorderStyle):
    chars = """
┌─┬┐  ┌┬┐
│ ││  ├┼┤
├─┼┤  ├┼┤
└─┴┘  ├┼┤
      ├┼┤
      ├┼┤
┌┬┬┬┬┬┼│┼┐
├┼┼┼┼┼─ ─┤
└┴┴┴┴┴┼│┼┘
      └┴┘
"""


class Round(Thin):
    chars = """
╭─┬╮  ╭┬╮
│ ││  ├┼┤
├─┼┤  ├┼┤
╰─┴╯  ├┼┤
      ├┼┤
      ├┼┤
╭┬┬┬┬┬┼│┼╮
├┼┼┼┼┼─ ─┤
╰┴┴┴┴┴┼│┼╯
      ╰┴╯
"""


class Thick(Thin):
    chars = """
┏┳━┓  ┍┯┑
┣╋━┫  ┢╈┪
┃┃ ┃  ┞╀┦
┗┻━┛  ┝┿┥
      ┟╁┧
      ┡╇┩
┎┲┭┰┮┱╆╽╅┒
┠╊┽╂┾╉╼ ╾┨
┖┺┵┸┶┹╄╿╃┚
      ┕┷┙
    """


class Double(Thin):
    """
    ╔╦═╗  ╒╤╕
    ╠╬═╣  ├┼┤
    ║║ ║  ├┼┤
    ╚╩═╝  ╞╪╡
          ├┼┤
          ├┼┤
    ╓┬┬╥┬┬┼│┼╖
    ╟┼┼╫┼┼─ ─╢
    ╙┴┴╨┴┴┼│┼╜
          ╘╧╛
    """


class DoubleDashBorderStyle:
    char = """
┌╌┬┐  ┌┬┐
╎ ╎╎  ├┼┤
├╌┼┤  ├┼┤
└╌┴┘  ├┼┤
      ├┼┤
      ├┼┤
┌┬┬┬┬┬┼╎┼┐
├┼┼┼┼┼╌ ╌┤
└┴┴┴┴┴┼╎┼┘
      └┴┘
"""


class ThickDoubleDash(Thick):
    chars = """
┏┳╍┓
┣╋╍┫
╏╏ ╏
┗┻╍┛
"""


class ASCII(BorderStyle):
    char = """
+-++  +++
| ||  +++
+-++  +++
+-++  +++
      +++
      +++
+++++++|++
++++++- -+
+++++++|++
      +++
"""


'''
    _axes = (
        (
            "JOINUP",
            "TOP",
            "MID",
            "SPLIT",
            "BOTTOM",
            "JOINDOWN",
            "BUTT",
        ),
        (
            "JOINLEFT",
            "LEFT",
            "MID",
            "SPLIT",
            "RIGHT",
            "JOIN_IGHT",
            "BUTT",
        ),
    )

    _aliases = {
        "HORIZONTAL": "MID_SPLIT",
        "VERTICAL": "SPLIT_MID",
    }

    def __init__(self, chars):

        self.matrix = [list(line.strip().ljust(7)) for line in chars.split("\n")]

    def __getattr__(self, value: "str"):

        # Look up aliases
        value = self._aliases.get(value, value)

        x_label, _, y_label = value.partition("_")
        if x_label in self._axes[0]:
            x_index = self._axes[0].index(x_label)
        if y_label in self._axes[1]:
            y_index = self._axes[1].index(y_label)

        return self.matrix[x_index][y_index]

    def Vertical

BorderSquare = BorderStyle(
    """ ┼├┴┼┤┼┬
        ┬┌─┬┐┬
        ┤│ ││├
        ┼├─┼┤┼
        ┴└─┴┘┴
        ┼├┬┼┤┼┴
        ├    ┤ """
)


BorderThick = BorderStyle(
    """ ╆┢┷╈┪╅┰
        ┲┏━┳┓┱
        ┨┃ ┃┃┠
        ╊┣━╋┫╉╂
        ┺┗━┻┛┹
        ╄┡┯╇┩╃┸
        ┝  ┿ ┥ """
)


BorderDouble = BorderStyle(
    """ ╆┢╧╈┪╅╥
        ┲╔═╦╗┱
        ╢║ ║║┠
        ╊╠═╬╣╉
        ┺╚═╩╝┹
        ╄┡╤╇┩╃╨
        ╞    ╡ """
)
"""
 	 	╒╓╕╖╘╙ 	╛╜
 	 	╪ ╫
"""
# class RoundCornerBorder(SquareBorder):
# """A border with round corners."""
#
# TOP_LEFT = "╭"
# TOP_RIGHT = "╮"
# BOTTOM_LEFT = "╰"
# BOTTOM_RIGHT = "╯"


class ThickOuterBorder:
    """A border with thick outer lines."""

    chars = """┏━┯┓
               ┃ │┃
               ┠─┼┨
               ┗━┷┛"""


class ThickVerticalBorder:
    """Box drawing characters with thick outer vertical lines."""

    chars = """┎─┬┒
               ┃ ┃┃
               ┠─╂┨
               ┖─┴┚"""


class ThickInnerVerticalsBorder:
    """Box drawing characters with thick outer vertical lines."""

    chars = """┌─┬┐
               │ ││
               ├─┼┤
               └─┴┘"""


class DoubleBorder:
    """Box drawing characters with thick outer vertical lines."""

    chars = """


               """


class DoubleOuterBorder:
    """Box drawing characters with thick outer vertical lines."""

    chars = """╔═╦╗
               ║ ║║
               ╠═╬╢
               ╚═╩╝"""


class DoubleInnerBorder:
    """Box drawing characters with thick outer vertical lines."""

    chars = """╔═╤╗
               ║ │║
               ╟─┼╢
               ╚═╧╝"""



"""

    ─ 	━ 	│ 	┃ 	┄ 	┅ 	┆ 	┇ 	┈ 	┉ 	┊ 	┋ 	┌ 	┍ 	┎ 	┏
    ┐ 	┑ 	┒ 	┓ 	└ 	┕ 	┖ 	┗ 	┘ 	┙ 	┚ 	┛ 	├ 	┝ 	┞ 	┟
    ┠ 	┡ 	┢ 	┣ 	┤ 	┥ 	┦ 	┧ 	┨ 	┩ 	┪ 	┫ 	┬ 	┭ 	┮ 	┯
    ┰ 	┱ 	┲ 	┳ 	┴ 	┵ 	┶ 	┷ 	┸ 	┹ 	┺ 	┻ 	┼ 	┽ 	┾ 	┿
    ╀ 	╁ 	╂ 	╃ 	╄ 	╅ 	╆ 	╇ 	╈ 	╉ 	╊ 	╋ 	╌ 	╍ 	╎ 	╏
    ═ 	║ 	╒ 	╓ 	╔ 	╕ 	╖ 	╗ 	╘ 	╙ 	╚ 	╛ 	╜ 	╝ 	╞ 	╟
    ╠ 	╡ 	╢ 	╣ 	╤ 	╥ 	╦ 	╧ 	╨ 	╩ 	╪ 	╫ 	╬ 	╭ 	╮ 	╯
    ╰

                     ╭┈┈┈┈┄┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ LEFT ╮
                     ┊ ╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ MID ┼ START
                     ┊ ┊ ╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ RIGHT ╯
                     ┊ ┊ ┊ ╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈ LEFT ╮
                     ┊ ┊ ┊ ┊ ╭┈┈┈┈┈┈┈┈┈┈┈┈┈ MID ┼ CORE
                     ┊ ┊ ┊ ┊ ┊ ╭┈┈┈┈┈┈┈┈┈ SPLIT ┤
                     ┊ ┊ ┊ ┊ ┊ ┊ ╭┈┈┈┈┈┈┈ RIGHT ╯
                     ┊ ┊ ┊ ┊ ┊ ┊ ┊ ╭┈┈┈┈┈┈ LEFT ╮
                     ┊ ┊ ┊ ┊ ┊ ┊ ┊ ┊ ╭┈┈┈┈┈ MID ┼ END
                     ┊ ┊ ┊ ┊ ┊ ┊ ┊ ┊ ┊ ╭┈ RIGHT ╯
                     ∨ ∨ ∨ ∨ ∨ ∨ ∨ ∨ ∨ ∨
         ╭ TOP ┈┈┈┈> ┌───┬ ┌───┬─┐ ┬───┐
    HEAD ┼ MIDDLE ┈> │   │ │   │ │ │   │
         ╰ BOTTOM ┈> ├───┼ ├───┼─┤ ┼───┤
         ╭ TOP ┈┈┈┈> ┌───┬ ┌───┬─┐ ┬───┐
    BODY ┼ MIDDLE ┈> │   │ │   │ │ │   │
         ├ SPLIT ┈┈> ├───┼ ├───┼─┤ ┼───┤
         ╰ BOTTOM ┈> └───┴ └───┴─┘ ┴───┘
         ╭ TOP ┈┈┈┈> ├───┼ ├───┼─┤ ┼───┤
    FOOT ┼ MIDDLE ┈> │   │ │   │ │ │   │
         ╰ BOTTOM ┈> └───┴ └───┴─┘ ┴───┘

           START  CORE    END
           ╭─┴─╮ ╭──┴──╮ ╭─┴─╮
         ╭ ┌───┬ ┌───┬─┐ ┬───┐
    HEAD ┤ │   │ │   │ │ │   │
         ╰ ├───┼ ├───┼─┤ ┼───┤
         ╭ ┌───┬ ┌───┬─┐ ┬───┐
    BODY ┤ │   │ │   │ │ │   │
         │ ├───┼ ├───┼─┤ ┼───┤
         ╰ └───┴ └───┴─┘ ┴───┘
         ╭ ├───┼ ├───┼─┤ ┼───┤
    FOOT ┤ │   │ │   │ │ │   │
         ╰ └───┴ └───┴─┘ ┴───┘

    Borders Consist of the following characters:

                ╭┈┈┈┈┈┈┈┈┈┈┈┈JOIN_LEFT
                ┊ ╭┈┈┈┈┈┈┈┈┈┈LEFT
                ┊ ┊ ╭┈┈┈┈┈┈┈┈MID
                ┊ ┊ ┊ ╭┈┈┈┈┈┈SPLIT
                ┊ ┊ ┊ ┊ ╭┈┈┈┈RIGHT
                ┊ ┊ ┊ ┊ ┊ ╭┈┈JOIN_RIGHT
                ┊ ┊ ┊ ┊ ┊ ┊ ╭BUTT
                ∨ ∨ ∨ ∨ v v V
      JOIN_UP┈> ╆ ┢ ┷ ╈ ┪ ╅ ┰
          TOP┈> ┲ ┏ ━ ┳ ┓ ┱
          MID┈> ┨ ┃   ┃ ┃ ┠
        SPLIT┈> ╊ ┣ ━ ╋ ┫ ╉ ╂
       BOTTOM┈> ┺ ┗ ━ ┻ ┛ ┹
    JOIN_DOWN┈> ╄ ┡ ┯ ╇ ┩ ╃ ┸
         BUTT┈> ┝     ┿   ┥
                 ┎┒┍┑
                 ┖┚┕┙

                ╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈BUTT_LEFT
                ┊ ╭┈┈┈┈┈┈┈┈┈┈┈┈JOIN_LEFT
                ┊ ┊ ╭┈┈┈┈┈┈┈┈┈┈LEFT
                ┊ ┊ ┊ ╭┈┈┈┈┈┈┈┈MID
                ┊ ┊ ┊ ┊ ╭┈┈┈┈┈┈SPLIT
                ┊ ┊ ┊ ┊ ┊ ╭┈┈┈┈RIGHT
                ┊ ┊ ┊ ┊ ┊ ┊ ╭┈┈JOIN_RIGHT
                ┊ ┊ ┊ ┊ ┊ ┊ ┊ ╭BUTT_RIGHT
                v ∨ ∨ ∨ ∨ v v V
      BUTT_UP┈>     ┍ ━ ┯ ┑
      JOIN_UP┈>   ╆ ┢   ╈ ┪ ╅
          TOP┈> ┎ ┲ ┏ ━ ┳ ┓ ┱ ┒
          MID┈>     ┃   ┃ ┃
        SPLIT┈> ┠ ╊ ┣ ━ ╋ ┫ ╉ ┨
       BOTTOM┈> ┖ ┺ ┗ ━ ┻ ┛ ┹ ┚
    JOIN_DOWN┈>   ╄ ┡ ━ ╇ ┩ ╃     ┰
    BUTT_DOWN┈>     ┕ ━ ┷ ┙ ┰     ╹
    """


'''
