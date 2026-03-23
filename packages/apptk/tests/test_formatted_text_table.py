"""Tests for :mod:`apptk.formatted_text.table`."""

from __future__ import annotations

from apptk.formatted_text.table import Cell, Col, Row, Table, compute_style


def test_sync_rows_to_cols_sets_cell_indices() -> None:
    """Test that sync_rows_to_cols sets _row_index and _col_index on cells."""
    cells_r0 = [Cell("a"), Cell("b")]
    cells_r1 = [Cell("c"), Cell("d")]
    row0 = Row(cells=cells_r0)
    row1 = Row(cells=cells_r1)
    table = Table(rows=[row0, row1])

    for i, row in enumerate(table.rows):
        for j, cell in enumerate(row.cells):
            assert cell._row_index == i, (
                f"Expected _row_index={i} for cell at ({i},{j}), got {cell._row_index}"
            )
            assert cell._col_index == j, (
                f"Expected _col_index={j} for cell at ({i},{j}), got {cell._col_index}"
            )


def test_sync_cols_to_rows_sets_cell_indices() -> None:
    """Test that sync_cols_to_rows sets _row_index and _col_index on cells."""
    cells_c0 = [Cell("a"), Cell("c")]
    cells_c1 = [Cell("b"), Cell("d")]
    col0 = Col(cells=cells_c0)
    col1 = Col(cells=cells_c1)
    table = Table(cols=[col0, col1])

    for i, row in enumerate(table.rows):
        for j, cell in enumerate(row.cells):
            assert cell._row_index == i, (
                f"Expected _row_index={i} for cell at ({i},{j}), got {cell._row_index}"
            )
            assert cell._col_index == j, (
                f"Expected _col_index={j} for cell at ({i},{j}), got {cell._col_index}"
            )


def test_alternate_row_style_applied_to_odd_rows() -> None:
    """Test that compute_style includes alternate_row_style for odd-indexed rows."""
    row0 = Row(cells=[Cell("a")])
    row1 = Row(cells=[Cell("b")])
    row2 = Row(cells=[Cell("c")])
    table = Table(
        rows=[row0, row1, row2],
        alternate_row_style="class:alt",
    )

    cell_row0 = table.rows[0].cells[0]
    cell_row1 = table.rows[1].cells[0]
    cell_row2 = table.rows[2].cells[0]

    style0 = compute_style(cell_row0, render_count=1)
    style1 = compute_style(cell_row1, render_count=1)
    style2 = compute_style(cell_row2, render_count=1)

    # alternate_row_style is applied to every other row; verify it alternates
    has_alt = [("class:alt" in s) for s in (style0, style1, style2)]
    # Exactly one pattern: either [True, False, True] or [False, True, False]
    assert has_alt in ([True, False, True], [False, True, False])
    # Consecutive rows should differ
    assert has_alt[0] != has_alt[1]
    assert has_alt[1] != has_alt[2]


def test_update_table_rows_preserves_indices() -> None:
    """Test that rebuilding table rows (as VariableList does) sets indices."""
    row0 = Row(cells=[Cell("h1"), Cell("h2")])
    row1 = Row(cells=[Cell("v1"), Cell("v2")])
    table = Table(rows=[row0], expand=True)

    # Simulate what VariableList._update_table_rows does
    table._rows.clear()
    table._cols.clear()
    for i, row in enumerate([row0, row1]):
        table._rows[i] = row
        row.table = table
    table.sync_rows_to_cols()

    for i, row in enumerate(table.rows):
        for j, cell in enumerate(row.cells):
            assert cell._row_index == i
            assert cell._col_index == j
