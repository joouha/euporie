"""Tests for the web-view control's error handling."""

from __future__ import annotations

from pathlib import Path

from upath import UPath

from euporie.core.widgets.webview import (
    ERROR_HEADING_NOT_FOUND,
    ERROR_HEADING_UNREACHABLE,
    ERROR_TITLE_GENERIC,
    ERROR_TITLE_NOT_FOUND,
    ERROR_TITLE_UNREACHABLE,
    WebViewControl,
    _error_page,
    _load_error_details,
)


def test_load_error_details_dns() -> None:
    """DNS failures produce an offline-style message."""
    title, heading, message = _load_error_details(
        OSError("[Errno 8] nodename nor servname provided, or not known")
    )
    assert ERROR_TITLE_UNREACHABLE in title
    assert ERROR_HEADING_UNREACHABLE in heading
    assert "offline" in message


def test_load_error_details_not_found() -> None:
    """404-style errors produce a "not found" message."""
    title, _, _ = _load_error_details(FileNotFoundError("404"))
    assert ERROR_TITLE_NOT_FOUND in title
    title, _, _ = _load_error_details(OSError("404 Not Found"))
    assert ERROR_TITLE_NOT_FOUND in title
    title, _, _ = _load_error_details(
        FileNotFoundError("[Errno 2] No such file or directory: 'page.html'")
    )
    assert ERROR_TITLE_NOT_FOUND in title


def test_load_error_details_connection() -> None:
    """Connection-refused / timeout errors are reported helpfully."""
    title, _, _ = _load_error_details(OSError("Connection refused"))
    assert ERROR_TITLE_UNREACHABLE in title
    _, _, message = _load_error_details(OSError("Connection timed out"))
    assert "refused" in message


def test_load_error_details_generic() -> None:
    """Unknown errors fall back to a generic message."""
    title, _, _ = _load_error_details(RuntimeError("Something exploded"))
    assert ERROR_TITLE_GENERIC in title


def test_load_error_details_wrapped_connection() -> None:
    """Connect failures wrapped by the fs layer are reported as unreachable."""
    exc = FileNotFoundError("http://127.0.0.1:9/")
    exc.__cause__ = OSError("Cannot connect to host 127.0.0.1:9")
    title, heading, message = _load_error_details(exc)
    assert ERROR_TITLE_UNREACHABLE in title
    assert ERROR_HEADING_UNREACHABLE in heading
    assert "refused" in message


def test_error_page_contains_url_and_friendly_message() -> None:
    """The error page includes the url and a friendly message."""
    url = UPath("https://euporie.readthedocs.io")
    markup = _error_page(
        url, OSError("[Errno 8] nodename nor servname provided, or not known")
    )
    assert "https://euporie.readthedocs.io" in markup
    assert ERROR_HEADING_UNREACHABLE in markup
    assert "offline" in markup
    assert markup.startswith("<html>")


def test_error_page_shows_inner_cause() -> None:
    """The error page shows the underlying cause rather than just the URL."""
    exc = FileNotFoundError("http://example.com")
    exc.__cause__ = OSError("[Errno 61] Connect call failed ('127.0.0.1', 9)")
    markup = _error_page(UPath("http://example.com"), exc)
    assert "Connect call failed" in markup
    assert ERROR_HEADING_UNREACHABLE in markup


def test_error_page_renders() -> None:
    """The error page renders to formatted text without crashing."""
    from apptk.formatted_text.html import RichHTML
    from apptk.formatted_text.utils import to_plain_text

    url = UPath("https://euporie.readthedocs.io")
    markup = _error_page(
        url, OSError("[Errno 8] nodename nor servname provided, or not known")
    )
    text = to_plain_text(RichHTML(markup, width=80))
    assert ERROR_HEADING_UNREACHABLE in text
    assert "euporie.readthedocs.io" in text
    assert "offline" in text


def test_webview_get_dom_renders_error_page() -> None:
    """``get_dom`` returns a renderable error page when a page cannot load."""
    from apptk.formatted_text.utils import to_plain_text

    control = WebViewControl(url="about:blank")
    dom = control.get_dom(Path("/no/such/page.html"))
    text = to_plain_text(dom)
    assert ERROR_HEADING_NOT_FOUND in text
    assert "/no/such/page.html" in text


def test_webview_error_page_triggers_redraw() -> None:
    """Creating the error page must fire ``rendered`` so the app redraws."""
    control = WebViewControl(url="about:blank")
    fired: list[bool] = []
    control.rendered += lambda sender: fired.append(True)
    control.get_dom(Path("/no/such/page.html"))
    assert fired


def _wait_for(control: WebViewControl, timeout: float = 5) -> None:
    """Wait for the web-view's render task to finish."""
    import time

    deadline = time.monotonic() + timeout
    while not control.render_task.done() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert control.render_task.done()


def test_webview_not_stuck_loading_when_render_fails(tmp_path: Path) -> None:
    """A render failure must not leave the web-view stuck on "Loading…"."""
    page = tmp_path / "index.html"
    page.write_text("<html><body><h1>Hi</h1></body></html>")

    control = WebViewControl(url=page)
    dom = control.dom

    async def _boom(width: int | None, height: int | None) -> None:
        raise RuntimeError("deliberate render failure")

    dom._render = _boom  # type: ignore[assignment]

    control.create_content(80, 24)
    _wait_for(control)

    assert control.loading is False
    assert control.rendering is False
    assert any(
        "Unable to render" in "".join(str(t[1]) for t in line) for line in control.lines
    )


def test_webview_renders_despite_unrenderable_image(tmp_path: Path) -> None:
    """A binary asset which cannot be decoded doesn't break page rendering."""
    page = tmp_path / "index.html"
    page.write_text(
        '<html><body><h1>Hello</h1><img src="logo.bin"><p>Tail</p></body></html>'
    )
    (tmp_path / "logo.bin").write_bytes(b"\x00\x01\x02\xff\xfe binary garbage")

    control = WebViewControl(url=page)
    control.create_content(80, 24)
    _wait_for(control)

    assert control.loading is False
    texts = ["".join(str(t[1]) for t in line) for line in control.lines]
    assert any("Hello" in text for text in texts)
    assert any("Tail" in text for text in texts)


def test_webview_resize_triggers_rere_e_render() -> None:
    """A resize must supersede an in-flight render and re-render at the new size."""
    control = WebViewControl(url="http://127.0.0.1:1/unreachable")
    # Schedule a render before the control has a size
    control.render()
    assert control.rendering
    # This should supersede the width-0 render and render at the new size
    control.create_content(80, 24)
    _wait_for(control)

    assert control.loading is False
    assert control.width == 80
    assert control.lines
    assert any(
        ERROR_HEADING_UNREACHABLE in "".join(str(t[1]) for t in line)
        for line in control.lines
    )
