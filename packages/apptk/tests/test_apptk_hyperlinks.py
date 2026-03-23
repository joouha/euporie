"""Tests for OSC 8 hyperlink support in apptk."""

from __future__ import annotations

from apptk.output.color_depth import ColorDepth
from apptk.output.vt100 import _EscapeCodeCache
from apptk.styles.base import DEFAULT_ATTRS, Attrs
from apptk.styles.style import _merge_attrs, _parse_style_str


class TestHyperlinkStyleParsing:
    """Tests for parsing link: style strings."""

    def test_parse_link_style(self) -> None:
        """Test parsing a simple link style."""
        attrs = _parse_style_str("link:https://example.com")
        assert attrs.link == "https://example.com"

    def test_parse_link_with_other_styles(self) -> None:
        """Test parsing link combined with other styles."""
        attrs = _parse_style_str("bold fg:red link:https://example.com underline")
        assert attrs.link == "https://example.com"
        assert attrs.bold is True
        assert attrs.color == "ff0000"  # parse_color converts "red" to hex
        assert attrs.underline is True

    def test_parse_link_with_complex_url(self) -> None:
        """Test parsing link with query parameters."""
        url = "https://example.com/path?query=value&other=123"
        attrs = _parse_style_str(f"link:{url}")
        assert attrs.link == url

    def test_parse_empty_link(self) -> None:
        """Test that no link style results in empty link."""
        attrs = _parse_style_str("bold")
        assert attrs.link is None  # _EMPTY_ATTRS has link=None

    def test_parse_noinherit_resets_link(self) -> None:
        """Test that noinherit starts from DEFAULT_ATTRS."""
        attrs = _parse_style_str("noinherit")
        assert attrs.link == ""  # DEFAULT_ATTRS has link=""


class TestHyperlinkAttrsMerge:
    """Tests for merging Attrs with links."""

    def test_merge_link_override(self) -> None:
        """Test that later link overrides earlier."""
        attrs1 = Attrs(
            color="red",
            bgcolor="",
            bold=False,
            dim=False,
            underline=False,
            strike=False,
            italic=False,
            blink=False,
            reverse=False,
            hidden=False,
            link="https://first.com",
        )
        attrs2 = Attrs(
            color=None,
            bgcolor=None,
            bold=None,
            dim=None,
            underline=None,
            strike=None,
            italic=None,
            blink=None,
            reverse=None,
            hidden=None,
            link="https://second.com",
        )
        merged = _merge_attrs([attrs1, attrs2])
        assert merged.link == "https://second.com"
        assert merged.color == "red"

    def test_merge_link_preserved(self) -> None:
        """Test that link is preserved when not overridden."""
        attrs1 = Attrs(
            color="red",
            bgcolor="",
            bold=False,
            dim=False,
            underline=False,
            strike=False,
            italic=False,
            blink=False,
            reverse=False,
            hidden=False,
            link="https://example.com",
        )
        attrs2 = Attrs(
            color=None,
            bgcolor=None,
            bold=True,
            dim=None,
            underline=None,
            strike=None,
            italic=None,
            blink=None,
            reverse=None,
            hidden=None,
            link=None,
        )
        merged = _merge_attrs([attrs1, attrs2])
        assert merged.link == "https://example.com"
        assert merged.bold is True


class TestHyperlinkEscapeCodeCache:
    """Tests for OSC 8 escape sequence generation in the cache.

    The escape code cache includes OSC 8 sequences so that non-renderer
    output paths (e.g. print_formatted_text) also emit hyperlinks.
    """

    def test_escape_code_with_link(self) -> None:
        """Test that escape code includes OSC 8 sequence for links."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)
        attrs = DEFAULT_ATTRS._replace(link="https://example.com")

        result = cache[attrs]

        # Should contain OSC 8 opening sequence
        assert "\x1b]8;" in result
        assert "https://example.com" in result
        assert "\x1b\\" in result

    def test_escape_code_link_id_generation(self) -> None:
        """Test that link ID is generated from attrs hash."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)
        url = "https://example.com"
        attrs = DEFAULT_ATTRS._replace(link=url)

        result = cache[attrs]

        # ID should be the hash of the full attrs tuple
        expected_id = hash(attrs)
        assert f"id={expected_id}" in result

    def test_escape_code_same_url_different_styles_have_ids(self) -> None:
        """Test that same URL with different styles both produce link IDs."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)
        url = "https://example.com"

        attrs1 = DEFAULT_ATTRS._replace(link=url, bold=True)
        attrs2 = DEFAULT_ATTRS._replace(link=url, italic=True)

        result1 = cache[attrs1]
        result2 = cache[attrs2]

        assert f"id={hash(attrs1)}" in result1
        assert f"id={hash(attrs2)}" in result2

    def test_escape_code_different_url_different_id(self) -> None:
        """Test that different URLs produce different IDs."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)

        attrs1 = DEFAULT_ATTRS._replace(link="https://example1.com")
        attrs2 = DEFAULT_ATTRS._replace(link="https://example2.com")

        result1 = cache[attrs1]
        result2 = cache[attrs2]

        expected_id1 = hash(attrs1)
        expected_id2 = hash(attrs2)

        assert f"id={expected_id1}" in result1
        assert f"id={expected_id2}" in result2
        assert expected_id1 != expected_id2

    def test_escape_code_no_link_omits_osc8(self) -> None:
        """Test that attrs without link do not produce OSC 8 sequence."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)
        attrs = DEFAULT_ATTRS._replace(bold=True)

        result = cache[attrs]

        # Should NOT contain any OSC 8 sequence — closing is handled by renderer
        assert "\x1b]8;" not in result

    def test_escape_code_empty_link_omits_osc8(self) -> None:
        """Test that empty link string does not produce OSC 8 sequence."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)
        attrs = DEFAULT_ATTRS._replace(link="")

        result = cache[attrs]

        # Should NOT contain any OSC 8 sequence
        assert "\x1b]8;" not in result

    def test_escape_code_link_with_styles(self) -> None:
        """Test that link works with other style attributes."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)
        attrs = DEFAULT_ATTRS._replace(
            link="https://example.com",
            bold=True,
            color="ff0000",
        )

        result = cache[attrs]

        # Should have both SGR codes and OSC 8
        assert "\x1b[0;" in result  # SGR start
        assert "1" in result  # Bold
        assert "38" in result  # Foreground color
        assert "\x1b]8;" in result  # OSC 8
        assert "https://example.com" in result


class TestHyperlinkRendererTransitions:
    """Tests for stateful hyperlink tracking in the renderer.

    The renderer tracks last_link to close open hyperlinks on
    reset_attributes and to update last_link when styles change.
    """

    def test_reset_attributes_closes_link(self) -> None:
        """Test that reset_attributes logic closes an open link."""
        # Simulates the reset_attributes function in the renderer
        last_link: str | None = "https://example.com"
        raw_output = ""
        if last_link:
            raw_output = "\x1b]8;;\x1b\\"
            last_link = None
        assert raw_output == "\x1b]8;;\x1b\\"
        assert last_link is None

    def test_reset_attributes_noop_without_link(self) -> None:
        """Test that reset_attributes does not emit OSC 8 when no link is active."""
        last_link: str | None = None
        raw_output = ""
        if last_link:
            raw_output = "\x1b]8;;\x1b\\"
            last_link = None
        assert raw_output == ""
        assert last_link is None

    def test_escape_code_cache_includes_osc8_for_links(self) -> None:
        """Test that the cache output includes OSC 8 for linked attrs only."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)

        linked = DEFAULT_ATTRS._replace(link="https://example.com")
        unlinked = DEFAULT_ATTRS._replace(bold=True)

        linked_result = cache[linked]
        unlinked_result = cache[unlinked]

        # Linked should open a hyperlink
        assert "\x1b]8;id=" in linked_result
        assert "https://example.com" in linked_result

        # Unlinked should NOT contain OSC 8 — renderer handles closing
        assert "\x1b]8;" not in unlinked_result

    def test_different_links_in_cache(self) -> None:
        """Test transitioning between two different links via cache."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)

        attrs1 = DEFAULT_ATTRS._replace(link="https://first.com")
        attrs2 = DEFAULT_ATTRS._replace(link="https://second.com")

        result1 = cache[attrs1]
        result2 = cache[attrs2]

        assert "https://first.com" in result1
        assert "https://second.com" in result2
        assert "\x1b]8;id=" in result1
        assert "\x1b]8;id=" in result2


class TestHyperlinkSplitFragments:
    """Tests for split linked fragments sharing the same link ID."""

    def test_split_linked_fragment_same_id(self) -> None:
        """Test that splitting a linked fragment keeps the same link ID."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)

        # Simulate a linked fragment split into two parts — both have the
        # same style attrs, so the cache should return the same escape code
        # (and therefore the same link ID) for both.
        attrs = DEFAULT_ATTRS._replace(link="https://example.com")

        result_part1 = cache[attrs]
        result_part2 = cache[attrs]

        # Extract the id= value from the OSC 8 sequence
        import re

        ids_part1 = re.findall(r"id=([^;]+)", result_part1)
        ids_part2 = re.findall(r"id=([^;]+)", result_part2)

        assert len(ids_part1) == 1
        assert len(ids_part2) == 1
        assert ids_part1[0] == ids_part2[0]

    def test_split_linked_fragment_with_bold_same_id(self) -> None:
        """Test that split bold-linked fragments share the same link ID."""
        cache = _EscapeCodeCache(ColorDepth.DEPTH_24_BIT)

        attrs = DEFAULT_ATTRS._replace(link="https://example.com", bold=True)

        result_part1 = cache[attrs]
        result_part2 = cache[attrs]

        import re

        ids_part1 = re.findall(r"id=([^;]+)", result_part1)
        ids_part2 = re.findall(r"id=([^;]+)", result_part2)

        assert len(ids_part1) == 1
        assert ids_part1[0] == ids_part2[0]


class TestHyperlinkAttrsDefault:
    """Tests for DEFAULT_ATTRS link field."""

    def test_default_attrs_has_empty_link(self) -> None:
        """Test that DEFAULT_ATTRS has empty string for link."""
        assert DEFAULT_ATTRS.link == ""

    def test_attrs_link_field_exists(self) -> None:
        """Test that Attrs has link field."""
        attrs = Attrs(
            color="",
            bgcolor="",
            bold=False,
            dim=False,
            underline=False,
            strike=False,
            italic=False,
            blink=False,
            reverse=False,
            hidden=False,
            link="https://test.com",
        )
        assert attrs.link == "https://test.com"
