"""The video extension allows you to embed videos in HTML output.

Based on https://github.com/sphinx-contrib/video/

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from docutils import nodes
from docutils.parsers.rst import Directive, directives

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from docutils.writers._html_base import HTMLTranslator
    from sphinx.application import Sphinx


def get_option(options: dict[str, Any], key: str, default: Any) -> Any:
    """Get an option."""
    if key not in options:
        return default

    if isinstance(default, bool):
        return True
    return options[key]


class video(nodes.General, nodes.Element):
    """A video node."""


class Video(Directive):
    """A docutils video directive."""

    has_content = True
    required_arguments = 1
    optional_arguments = 5
    final_argument_whitespace = False
    option_spec: ClassVar[
        dict[
            str,
            Directive,
        ]
    ] = {
        "alt": directives.unchanged,
        "width": directives.unchanged,
        "height": directives.unchanged,
        "autoplay": directives.flag,
        "nocontrols": directives.flag,
    }

    def run(self) -> list[video]:
        """Return the nodes generated from this directive."""
        alt = get_option(self.options, "alt", "Video")
        width = get_option(self.options, "width", "")
        height = get_option(self.options, "height", "")
        autoplay = get_option(self.options, "autoplay", False)
        nocontrols = get_option(self.options, "nocontrols", False)

        return [
            video(
                path=self.arguments[0],
                alt=alt,
                width=width,
                height=height,
                autoplay=autoplay,
                nocontrols=nocontrols,
            )
        ]


def visit_video_node(self: HTMLTranslator, node: video) -> None:
    """Return an HTML block when the video node is visited."""
    extension = Path(node["path"]).suffix[1:]

    html_block = """
    <video {width} {height} {nocontrols} {autoplay} preload="metadata">
    <source src="{path}" type="video/{filetype}">
    {alt}
    </video>
    """.format(
        width='width="' + node["width"] + '"' if node["width"] else "",
        height='height="' + node["height"] + '"' if node["height"] else "",
        path=node["path"],
        filetype=extension,
        alt=node["alt"],
        autoplay="autoplay" if node["autoplay"] else "",
        nocontrols="" if node["nocontrols"] else "controls",
    )
    self.body.append(html_block)


def depart_video_node(self: HTMLTranslator, node: video) -> None:
    """Do nothing when departing a video node."""


def setup(app: Sphinx) -> None:
    """Register this extensions with sphinx."""
    app.add_node(
        video,
        html=(visit_video_node, depart_video_node),
        # Do nothing for text & latex output - they do not support vidoe
        latex=(depart_video_node, depart_video_node),
        text=(depart_video_node, depart_video_node),
    )
    app.add_directive("video", Video)


"""
Copyright (c) 2018 by Raphael Massabot <rmassabot@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
=======
BSD 2-Clause License

Copyright (c) 2018,
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
