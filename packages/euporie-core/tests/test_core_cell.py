"""Tests for notebook cell widgets."""

from __future__ import annotations

from apptk.border import NoLine, ThickLine, ThinLine

from euporie.core.widgets.cell import _get_border_style, get_cell_id


def test_cell_borders_hidden_when_disabled_and_unselected() -> None:
    """Cells without borders enabled or selection show no border."""
    assert _get_border_style(False, False, False, False) is NoLine.grid
    assert _get_border_style(False, True, False, False) is NoLine.grid


def test_cell_borders_shown_when_selected_or_enabled() -> None:
    """Selected cells and cells with borders enabled use a thin border."""
    assert _get_border_style(True, False, False, False) is ThinLine.outer
    assert _get_border_style(False, True, True, False) is ThinLine.outer
    assert _get_border_style(True, True, False, False) is ThinLine.outer


def test_cell_borders_thick_when_multi_selected_and_focused() -> None:
    """A focused cell within a multi-selection uses a thick border."""
    assert _get_border_style(True, True, False, True) is ThickLine.outer
    assert _get_border_style(False, True, True, True) is ThickLine.outer


def test_get_cell_id_generates_and_persists_id() -> None:
    """Missing cell IDs are generated and stored on the cell."""
    cell_json = {}
    cell_id = get_cell_id(cell_json)
    assert cell_id
    assert cell_json["id"] == cell_id
    assert get_cell_id(cell_json) == cell_id
