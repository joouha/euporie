"""Allow drawing tables as :class:`FormattedText`."""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache, partial
from itertools import tee, zip_longest
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines, to_plain_text
from prompt_toolkit.layout.dimension import Dimension, to_dimension

from euporie.core.border import (
    DiLineStyle,
    GridChar,
    InvisibleLine,
    LineStyle,
    NoLine,
    ThinLine,
    get_grid_char,
)
from euporie.core.data_structures import (
    DiBool,
    DiInt,
    DiStr,
)
from euporie.core.ft.utils import (
    FormattedTextAlign,
    align,
    fragment_list_width,
    join_lines,
    max_line_width,
    wrap,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from typing import (
        Any,
        TypeVar,
    )

    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        StyleAndTextTuples,
    )
    from prompt_toolkit.layout.dimension import AnyDimension

    PairT = TypeVar("PairT")


def pairwise(iterable: Iterable[PairT]) -> Iterator[tuple[PairT, PairT]]:
    """Return successiver overlapping pairs from an iterable."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


class Cell:
    """A table cell."""

    def __init__(
        self,
        text: AnyFormattedText = "",
        row: Row | None = None,
        col: Col | None = None,
        colspan: int = 1,
        rowspan: int = 1,
        width: int | None = None,
        align: FormattedTextAlign | None = None,
        style: str = "",
        padding: DiInt | int = 0,
        border_line: DiLineStyle | LineStyle = ThinLine,
        border_style: DiStr | str = "",
        border_visibility: DiBool | bool | None = True,
    ) -> None:
        """Create a new table cell.

        Args:
            text: Text or formatted text to display in the cell
            row: The row to which this cell belongs
            col: The column to which this cell belongs
            colspan: The number of columns this cell spans
            rowspan: The number of row this cell spans
            width: The desired width of the cell
            align: How the text in the cell should be aligned
            style: The style to apply to the cell's contents
            padding: The padding around the contents of the cell
            border_line: The line to use for the borders
            border_style: The style to apply to the cell's borders
            border_visibility: The visibility of each border edge

        """
        self.expands = self
        self.text = text
        self.row = row or DummyRow()
        self.col = col or DummyCol()
        self.colspan = colspan
        self.rowspan = rowspan
        self.width = width
        self.align = align
        self.style = style

        self.padding = (
            DiInt(padding, padding, padding, padding)
            if isinstance(padding, int)
            else padding
        )
        self.border_line = (
            DiLineStyle(border_line, border_line, border_line, border_line)
            if isinstance(border_line, LineStyle)
            else border_line
        )
        self.border_style = (
            DiStr(border_style, border_style, border_style, border_style)
            if isinstance(border_style, str)
            else border_style
        )
        self.border_visibility = (
            DiBool(
                border_visibility,
                border_visibility,
                border_visibility,
                border_visibility,
            )
            if isinstance(border_visibility, bool)
            else border_visibility
        )

        self._col_index: int | None = None
        self._row_index: int | None = None

    @property
    def padding(self) -> DiInt:
        """The cell's padding."""
        return self._padding

    @padding.setter
    def padding(self, padding: DiInt | int) -> None:
        """Set the cell's padding."""
        self._padding = (
            DiInt(padding, padding, padding, padding)
            if isinstance(padding, int)
            else padding
        )

    @property
    def border_line(self) -> DiLineStyle:
        """The cell's border line."""
        return self._border_line

    @border_line.setter
    def border_line(self, border_line: DiLineStyle | LineStyle) -> None:
        """Set the cell's border line."""
        self._border_line = (
            DiLineStyle(border_line, border_line, border_line, border_line)
            if isinstance(border_line, LineStyle)
            else border_line
        )

    @property
    def border_style(self) -> DiStr:
        """The cell's border style."""
        return self._border_style

    @border_style.setter
    def border_style(self, border_style: DiStr | str) -> None:
        """Set the cell's border style."""
        self._border_style = (
            DiStr(border_style, border_style, border_style, border_style)
            if isinstance(border_style, str)
            else border_style
        )

    def __repr__(self) -> str:
        """Return a text representation of the cell."""
        cell_text = to_plain_text(self.text)
        if len(cell_text) > 5:
            cell_text = cell_text[:4] + "…"
        return f"{self.__class__.__name__}({cell_text!r})"


class SpacerCell(Cell):
    """A dummy cell to virtually occupy space when ``colspan`` or ``rowspan`` are used."""

    def __init__(
        self,
        expands: Cell,
        span_row_index: int,
        span_col_index: int,
        text: AnyFormattedText = "",
        row: Row | None = None,
        col: Col | None = None,
        colspan: int = 1,
        rowspan: int = 1,
        width: int | None = None,
        align: FormattedTextAlign | None = None,
        style: str = "",
        padding: DiInt | int | None = None,
        border_line: DiLineStyle | LineStyle = NoLine,
        border_style: DiStr | str = "",
        border_visibility: DiBool | bool | None = None,
    ) -> None:
        """Create a new table cell.

        Args:
            expands: This should be reference to the spanning cell
            span_col_index: The index of a spacer cell inside a colspan
            span_row_index: The index of a spacer cell inside a rowspan
            text: Text or formatted text to display in the cell
            row: The row to which this cell belongs
            col: The column to which this cell belongs
            colspan: The number of columns this cell spans
            rowspan: The number of row this cell spans
            width: The desired width of the cell
            align: How the text in the cell should be aligned
            style: The style to apply to the cell's contents
            padding: The padding around the contents of the cell
            border_line: The line to use for the borders
            border_style: The style to apply to the cell's borders
            border_visibility: The visibility of each border edge

        """
        super().__init__(
            text="",
            row=row,
            col=col,
            colspan=1,
            rowspan=1,
            width=None,
            align=align,
            style=expands.style,
            padding=expands.padding,
            border_line=expands.border_line,
            border_style=expands.border_style,
            border_visibility=expands.border_visibility,
        )
        self.expands = expands
        self.span_row_index = span_row_index
        self.span_col_index = span_col_index


class _Dummy(Cell):
    """A dummy cell with not content, padding or borders."""

    def __init__(
        self,
        text: AnyFormattedText = "",
        row: Row | None = None,
        col: Col | None = None,
        colspan: int = 1,
        rowspan: int = 1,
        width: int | None = None,
        align: FormattedTextAlign | None = None,
        style: str = "",
        padding: DiInt | int = 0,
        border_line: DiLineStyle | LineStyle = NoLine,
        border_style: DiStr | str = "",
        border_visibility: DiBool | bool | None = None,
    ) -> None:
        """Create an dummy cells to fill empty space in a table."""
        table = (row or col or DummyRow()).table
        background_style = table.background_style
        super().__init__(
            row=row,
            col=col,
            style=background_style,
            padding=0,
            border_line=NoLine,
            border_style=background_style,
            border_visibility=False,
        )

    def __repr__(self) -> str:
        """Represent the cell instance as a string."""
        return f"{self.__class__.__name__}()"


class RowCol:
    """Base class for table rows and columns."""

    _type: str
    span_type: str

    def __init__(
        self,
        table: Table | None = None,
        cells: Sequence[Cell] | None = None,
        align: FormattedTextAlign | None = None,
        style: str = "",
        padding: DiInt | int = 0,
        border_line: DiLineStyle | LineStyle = NoLine,
        border_style: DiStr | str = "",
        border_visibility: DiBool | bool | None = None,
    ) -> None:
        """Create a new row/column.

        Args:
            table: The :py:class:`table` that this row/column belongs to
            cells: A list of cells in this row/column
            align: The default alignment for cells in this row/column
            style: The default style for cells in this row/column
            padding: The default padding for cells in this row/column
            border_line: The line to use for the borders
            border_style: The style to apply to the table's borders
            border_visibility: The visibility of each border edge

        """
        self.table = table or DummyTable()
        if isinstance(self, Row):
            row = self
            col = None
        elif isinstance(self, Col):
            row = None
            col = self
        else:
            raise ValueError("%s is not a `Row` or `Col`", self)

        self._cells = defaultdict(
            lambda: _Dummy(border_style=self.table.style, row=row, col=col),
            dict(enumerate(cells or [])),
        )
        if cells:
            for cell in cells:
                setattr(cell, self._type, self)

        self.align = align
        self.style = style

        self._padding = (
            DiInt(padding, padding, padding, padding)
            if isinstance(padding, int)
            else padding
        )
        self._border_line = (
            DiLineStyle(border_line, border_line, border_line, border_line)
            if isinstance(border_line, LineStyle)
            else border_line
        )
        self._border_style = (
            DiStr(border_style, border_style, border_style, border_style)
            if isinstance(border_style, str)
            else border_style
        )
        self.border_visibility = (
            DiBool(
                border_visibility,
                border_visibility,
                border_visibility,
                border_visibility,
            )
            if isinstance(border_visibility, bool)
            else border_visibility
        )

    @property
    def padding(self) -> DiInt:
        """The cell's padding."""
        return self._padding

    @padding.setter
    def padding(self, padding: DiInt | int) -> None:
        """Set the cell's padding."""
        self._padding = (
            DiInt(padding, padding, padding, padding)
            if isinstance(padding, int)
            else padding
        )

    @property
    def border_line(self) -> DiLineStyle:
        """The cell's border line."""
        return self._border_line

    @border_line.setter
    def border_line(self, border_line: DiLineStyle | LineStyle) -> None:
        """Set the cell's border line."""
        self._border_line = (
            DiLineStyle(border_line, border_line, border_line, border_line)
            if isinstance(border_line, LineStyle)
            else border_line
        )

    @property
    def border_style(self) -> DiStr:
        """The cell's border style."""
        return self._border_style

    @border_style.setter
    def border_style(self, border_style: DiStr | str) -> None:
        """Set the cell's border style."""
        self._border_style = (
            DiStr(border_style, border_style, border_style, border_style)
            if isinstance(border_style, str)
            else border_style
        )

    @property
    def cells(self) -> list[Cell]:
        """List the cells in the row/column."""
        n = len(self.table._cols) if self._type == "row" else len(self.table._rows)
        cells = []
        for i in range(n):
            cell = self._cells[i]
            if isinstance(cell, _Dummy):
                if isinstance(self, Row):
                    cell.row = self
                    cell.col = self.table._cols[i]
                elif isinstance(self, Col):
                    cell.col = self
                    cell.row = self.table._rows[i]
            cells.append(cell)

        return cells

    def new_cell(self, *args: Any, **kwargs: Any) -> Cell:
        """Create a new cell in this row/column."""
        cell = Cell(*args, **kwargs)
        self.add_cell(cell)
        return cell

    def add_cell(self, cell: Cell, index: int | None = None) -> None:
        """Add a cell to the row/ column."""
        if index is None:
            # Fit cells into available space
            # TODO - also check fit by colspan
            index = 0
            cells = self._cells
            rowspan = cell.rowspan
            colspan = cell.colspan
            while any(
                index + y in cells
                for y in range(rowspan if self._type == "col" else colspan)
            ):
                index += 1

        self._cells[index] = cell

        if self._type == "row":
            assert isinstance(self, Row)
            cell.row = cast("Row", self)
            cell.col = self.table._cols[index]

            row_index = next(i for i, row in self.table._rows.items() if row is self)
            col_index = index

            cell.col._cells[row_index] = cell

            cell._row_index = row_index
            cell._col_index = index

        elif self._type == "col":
            assert isinstance(self, Col)
            cell.row = self.table._rows[index]
            cell.col = cast("Col", self)

            row_index = index
            col_index = next(i for i, col in self.table._cols.items() if col is self)

            cell.row._cells[col_index] = cell

            cell._row_index = index
            cell._col_index = col_index

        for i in range(cell.rowspan):
            for j in range(cell.colspan):
                if i > 0 or j > 0:
                    spacer = SpacerCell(
                        expands=cell,
                        span_row_index=i,
                        span_col_index=j,
                        row=self.table._rows[row_index + i],
                        col=self.table._cols[col_index + j],
                    )
                    spacer._row_index = row_index + i
                    spacer._col_index = col_index + j
                    self.table._rows[row_index + i]._cells[col_index + j] = spacer
                    self.table._cols[col_index + j]._cells[row_index + i] = spacer

    def __repr__(self) -> str:
        """Return a textual representation of the row or column."""
        return f"{self.__class__.__name__}({', '.join(map(str, self._cells.values()))})"


class Row(RowCol):
    """A row in a table."""

    _type = "row"
    span_type = "colspan"


class Col(RowCol):
    """A column in a table."""

    _type = "col"
    span_type = "rowspan"


@lru_cache
def compute_style(cell: Cell, render_count: int = 0) -> str:
    """Compute a cell's style string."""
    return f"{cell.row.table.style} {cell.col.style} {cell.row.style} {cell.style}"


###############


@lru_cache
def compute_text(cell: Cell, render_count: int = 0) -> StyleAndTextTuples:
    """Compute a cell's input, converted to :class:`FormattedText`."""
    return to_formatted_text(cell.text, style=compute_style(cell))


@lru_cache
def compute_padding(cell: Cell, render_count: int = 0) -> DiInt:
    """Compute a cell's padding."""
    output = {}
    table_padding = cell.row.table.padding
    row_padding = cell.row.padding
    col_padding = cell.col.padding
    cell_padding = cell.padding
    for direction in ("top", "right", "bottom", "left"):
        output[direction] = max(
            getattr(table_padding, direction, 0),
            getattr(row_padding, direction, 0),
            getattr(col_padding, direction, 0),
            getattr(cell_padding, direction, 0),
            0,
        )
    return DiInt(**output)


@lru_cache
def compute_border_visibility(cell: Cell, render_count: int = 0) -> DiBool:
    """Compute a cell's border visibility."""
    output = {}

    row = cell.row
    col = cell.col
    table = row.table
    n_rows = len(table._rows)
    n_cols = len(table._cols)
    cell_border_visibility = cell.border_visibility
    row_border_visibility = row.border_visibility
    col_border_visibility = col.border_visibility
    table_border_visibility = table.border_visibility

    output["top"] = (
        (cell_border_visibility and cell_border_visibility.top)
        or (row_border_visibility and row_border_visibility.top)
        or (
            cell._row_index == 0 and col_border_visibility and col_border_visibility.top
        )
        or (
            cell._row_index == 0
            and table_border_visibility
            and table_border_visibility.top
        )
    )

    output["bottom"] = (
        (cell_border_visibility and cell_border_visibility.bottom)
        or (row_border_visibility and row_border_visibility.bottom)
        or (
            cell._row_index == n_rows - 1
            and col_border_visibility
            and col_border_visibility.bottom
        )
        or (
            table_border_visibility
            and cell._row_index == n_rows - 1
            and table_border_visibility.bottom
        )
    )

    output["left"] = (
        (cell_border_visibility and cell_border_visibility.left)
        or (
            cell._col_index == 0
            and row_border_visibility
            and row_border_visibility.left
        )
        or (col_border_visibility and col_border_visibility.left)
        or (
            cell._col_index == 0
            and table_border_visibility
            and table_border_visibility.left
        )
    )

    output["right"] = (
        (cell_border_visibility and cell_border_visibility.right)
        or (
            cell._col_index == n_cols - 1
            and row_border_visibility
            and row_border_visibility.left
        )
        or (col_border_visibility and col_border_visibility.left)
        or (
            table_border_visibility
            and cell._col_index == n_cols - 1
            and table_border_visibility.right
        )
    )

    return DiBool(**output)


###############


@lru_cache
def calculate_cell_width(cell: Cell, render_count: int = 0) -> int:
    """Compute the final width of a cell, including padding."""
    if cell.colspan > 1:
        return 0
    padding = compute_padding(cell, render_count)
    return (
        (cell.width or max_line_width(compute_text(cell, render_count)))
        + padding.left
        + padding.right
    )


@lru_cache
def compute_border_line(cell: Cell, render_count: int = 0) -> DiLineStyle:
    """Compute a cell's border line."""
    if isinstance(cell, _Dummy):
        return DiLineStyle(NoLine, NoLine, NoLine, NoLine)
    output = {}

    row = cell.row
    col = cell.col
    table = cell.row.table
    row_cells = row.cells
    col_cells = col.cells
    cell_border_line = cell.border_line
    row_border_line = row.border_line
    col_border_line = col.border_line
    table_border_line = table.border_line

    if (value := row_border_line.top) is not NoLine or (
        cell == col_cells[0] and (value := table_border_line.top) is not NoLine
    ):
        output["top"] = value

    if (value := row_border_line.bottom) is not NoLine or (
        cell == col_cells[-1] and (value := table_border_line.bottom) is not NoLine
    ):
        output["bottom"] = value

    if (value := col_border_line.left) is not NoLine or (
        cell == row_cells[0] and (value := table_border_line.left) is not NoLine
    ):
        output["left"] = value

    if (value := col_border_line.right) is not NoLine or (
        cell == row_cells[-1] and (value := table_border_line.right) is not NoLine
    ):
        output["right"] = value

    for direction in ("top", "right", "bottom", "left"):
        if (value := getattr(cell_border_line, direction, NoLine)) is not NoLine:
            output[direction] = value

    if isinstance(cell, SpacerCell):
        expands = cell.expands
        # Set left border to invisible in colspan
        if 0 < cell.span_col_index < expands.colspan:
            output["left"] = InvisibleLine
        # Set top border to invisible in rowspan
        if 0 < cell.span_row_index < expands.rowspan:
            output["top"] = InvisibleLine

    return DiLineStyle(**output)


@lru_cache
def compute_border_width(cell: Cell, render_count: int = 0) -> DiInt:
    """Compute the width of a cell's borders."""
    if isinstance(cell, _Dummy):
        output = {"top": 0, "right": 0, "bottom": 0, "left": 0}
    else:
        output = {"top": 1, "right": 1, "bottom": 1, "left": 1}

    # XXX If don't understand why row needs to follow cell expansion but column doesn't
    row = cell.row
    col = cell.col
    table = row.table

    if row not in table._rows.values() or col not in table._cols.values():
        # The table has not yet been fully constructed
        return DiInt(**output)

    row_index = table.rows.index(row)
    col_index = table.cols.index(col)

    row_cells_bv = [compute_border_visibility(cell, render_count) for cell in row.cells]
    col_cells_bv = [compute_border_visibility(cell, render_count) for cell in col.cells]

    for cell, cell_left in zip(row.cells, table.rows[row_index - 1].cells):
        if (
            compute_border_visibility(cell).left
            or compute_border_visibility(cell_left).right
        ):
            break

    row_top_cells_bv = (
        compute_border_visibility(cell, render_count)
        for cell in (
            table.rows[row_index - 1].cells if row_index - 1 in table._rows else []
        )
    )
    col_left_cells_bv = (
        compute_border_visibility(cell, render_count)
        for cell in (
            table.cols[col_index - 1].cells if col_index - 1 in table._cols else []
        )
    )
    col_right_cells_bv = (
        compute_border_visibility(cell, render_count)
        for cell in (
            table.cols[col_index + 1].cells if col_index + 1 in table._cols else []
        )
    )
    row_bottom_cells_bv = (
        compute_border_visibility(cell, render_count)
        for cell in (
            table.rows[row_index + 1].cells if row_index + 1 in table._rows else []
        )
    )

    output["top"] = int(
        any(
            bv.top or (bv_other and bv_other.bottom)
            for bv, bv_other in zip_longest(row_cells_bv, row_top_cells_bv)
        )
    )
    output["right"] = int(
        any(
            bv.right or (bv_other and bv_other.left)
            for bv, bv_other in zip_longest(col_cells_bv, col_right_cells_bv)
        )
    )
    output["bottom"] = int(
        any(
            bv.bottom or (bv_other and bv_other.top)
            for bv, bv_other in zip_longest(row_cells_bv, row_bottom_cells_bv)
        )
    )
    output["left"] = int(
        any(
            bv.left or (bv_other and bv_other.right)
            for bv, bv_other in zip_longest(col_cells_bv, col_left_cells_bv)
        )
    )

    return DiInt(**output)


@lru_cache
def calculate_col_widths(
    cols: tuple[Col],
    width: Dimension,
    expand_to_width: bool,
    min_col_width: int = 2,
    render_count: int = 0,
) -> list[int]:
    """Calculate column widths given the available space.

    Reduce the widest column until we fit in available width, or expand cells to
    to fill the available width.

    Args:
        cols: A list of columns in the table
        width: The desired width of the table
        expand_to_width: Whether the column should expand to fill the available width
        min_col_width: The minimum width allowed for a column
        render_count: The number of times the app has been rendered

    Returns:
        List of new column widths

    """
    # TODO - this function is too slow

    col_widths = [
        max(
            min_col_width,
            *(calculate_cell_width(cell, render_count) for cell in col.cells),
        )
        for col in cols
    ]

    def total_width(col_widths: list[int]) -> int:
        """Calculate the total width of the columns including borders."""
        width = sum(col_widths)
        if cols:
            width += compute_border_width(cols[0].cells[0], render_count).left
        for _i, col in enumerate(cols):
            width += compute_border_width(col.cells[0], render_count).right
        return width

    def expand(target: int) -> None:
        """Expand the columns."""
        max_width = max(target, len(col_widths) * min_col_width)
        while total_width(col_widths) < max_width:
            # Expand only columns which do not have a width set if possible
            # TODO - expand proportionately to given widths
            col_index_widths = [
                (i, col_widths[i])
                for i, col in enumerate(cols)
                if all(cell.width is None for cell in col.cells)
            ]
            if not col_index_widths:
                col_index_widths = list(enumerate(col_widths))
            if col_index_widths:
                idxmin = min(col_index_widths, key=lambda x: x[1])[0]
                col_widths[idxmin] += 1
            else:
                break

    def contract(target: int) -> None:
        """Contract the columns."""
        max_width = max(target, len(col_widths) * min_col_width)
        while total_width(col_widths) > max_width:
            idxmax = max(enumerate(col_widths), key=lambda x: x[1])[0]
            col_widths[idxmax] -= 1

    # Determine whether to expand or contract the table
    current_width = total_width(col_widths)
    if width.preferred_specified:
        if current_width < width.preferred:
            expand(width.preferred)
        elif current_width > width.preferred:
            contract(width.preferred)
    if width.max_specified:
        if current_width > width.max:
            contract(width.max)
        if current_width < width.max and expand_to_width:
            expand(width.max)
    if width.min_specified and current_width < width.min:
        expand(width.min)

    return col_widths


@lru_cache
def get_node(
    nw_bl: DiLineStyle,
    ne_bl: DiLineStyle,
    se_bl: DiLineStyle,
    sw_bl: DiLineStyle,
) -> str:
    """Calculate which character to use at the intersection of four cells."""
    return get_grid_char(
        GridChar(
            max(nw_bl.right, ne_bl.left),
            max(ne_bl.bottom, se_bl.top),
            max(se_bl.left, sw_bl.right),
            max(sw_bl.top, nw_bl.bottom),
        )
    )


@lru_cache
def get_horizontal_edge(n_bl: DiLineStyle, s_bl: DiLineStyle) -> str:
    """Calculate which character to use to divide horizontally adjacent cells."""
    line_style = max(n_bl.bottom, s_bl.top)
    return get_grid_char(GridChar(NoLine, line_style, NoLine, line_style))


@lru_cache
def get_vertical_edge(w_bl: DiLineStyle, e_bl: DiLineStyle) -> str:
    """Calculate which character to use to divide vertically adjacent cells."""
    line_style = max(w_bl.right, e_bl.left)
    return get_grid_char(GridChar(line_style, NoLine, line_style, NoLine))


@lru_cache
def compute_align(cell: Cell, render_count: int = 0) -> FormattedTextAlign:
    """Compute the alignment of a cell."""
    if (align := cell.align) is not None:
        return align
    else:
        return cell.row.align or cell.col.align or cell.row.table.align


@lru_cache
def compute_lines(
    cell: Cell, width: int, render_count: int = 0
) -> list[StyleAndTextTuples]:
    """Wrap the cell's text to a given width.

    Args:
        cell: The cell whose lines to compute
        width: The width at which to wrap the cell's text.
        render_count: The number of times the application has been rendered

    Returns:
        A list of lines of formatted text
    """
    padding = compute_padding(cell, render_count)
    return list(
        split_lines(
            align(
                wrap(
                    [
                        *([("", "\n" * padding.top)] if padding.top else []),
                        *compute_text(cell, render_count),
                        *([("", "\n" * padding.bottom)] if padding.bottom else []),
                    ],
                    width=width,
                    placeholder="",
                ),
                compute_align(cell, render_count),
                width=width,
                style=compute_style(cell, render_count),
                placeholder="",
            )
        )
    )


@lru_cache
def compute_border_style(cell: Cell, render_count: int = 0) -> DiStr:
    """Compute the cell's final style for each of a cell's borders."""
    output = {}

    row = cell.row
    col = cell.col
    table = row.table
    max_row = len(table._rows) - 1
    max_col = len(table._cols) - 1
    cell_border_style = cell.border_style
    row_border_style = row.border_style
    col_border_style = col.border_style
    table_border_style = table.border_style

    output["top"] = "".join(
        (
            table_border_style.top if cell._row_index == 0 else "",
            col_border_style.top if cell._row_index == 0 else "",
            row_border_style.top,
            cell_border_style.top,
        )
    )
    output["right"] = "".join(
        (
            table_border_style.right if cell._col_index == max_col else "",
            col_border_style.right,
            row_border_style.right if cell._col_index == max_col else "",
            cell_border_style.right,
        )
    )
    output["bottom"] = "".join(
        (
            table_border_style.bottom if cell._row_index == max_row else "",
            col_border_style.bottom if cell._row_index == max_row else "",
            row_border_style.bottom,
            cell_border_style.bottom,
        )
    )
    output["left"] = "".join(
        (
            table_border_style.left if cell._col_index == 0 else "",
            col_border_style.left,
            row_border_style.left if cell._col_index == 0 else "",
            cell_border_style.left,
        )
    )

    return DiStr(**output)


class Table:
    """A table."""

    def __init__(
        self,
        rows: Sequence[Row] | None = None,
        cols: Sequence[Col] | None = None,
        width: AnyDimension | None = None,
        expand: bool = False,
        align: FormattedTextAlign = FormattedTextAlign.LEFT,
        style: str = "",
        padding: DiInt | int | None = None,
        border_line: DiLineStyle | LineStyle = NoLine,
        border_style: DiStr | str = "",
        border_visibility: DiBool | bool = False,
        background_style: str = "",
    ) -> None:
        """Create a new table instance.

        Args:
            rows: A list of :class:`Row`s to add to the table
            cols: A list of :class:`Col`s to add to the table. Cells specified in rows
                take priority, so cells in column positions already defined by rows
                will be ignored.
            width: The width of the table
            expand: Whether the table should expand to fill the available space
            align: The default alignment for cells in the table
            style: A style to apply to the table's cells' contents
            padding: The default padding for cells in the table
            border_line: The line to use for the borders
            border_style: The style to apply to the table's borders
            border_visibility: If :const:`True`, if borders in the table are
                :class:`Invisible` for their entire length, no extra line will be drawn
            background_style: The style to apply to missing cells

        """
        self.render_count = 0

        self._rows = defaultdict(partial(Row, self), enumerate(rows or []))
        if rows:
            for row in rows:
                row.table = self
        self._cols = defaultdict(partial(Col, self), enumerate(cols or []))
        if cols:
            for col in cols:
                col.table = self
        if rows:
            self.sync_rows_to_cols()
        elif cols:
            self.sync_cols_to_rows()

        if width is None:
            width = Dimension(max=get_app_session().output.get_size()[1])
        self._width = to_dimension(width)
        self.expand = expand

        self.align = align
        self.style = style

        if padding is None:
            padding = DiInt(0, 1, 0, 1)
        self.padding = (
            DiInt(padding, padding, padding, padding)
            if isinstance(padding, int)
            else padding
        )
        self.border_line = (
            DiLineStyle(border_line, border_line, border_line, border_line)
            if isinstance(border_line, LineStyle)
            else border_line
        )
        self.border_style = (
            DiStr(border_style, border_style, border_style, border_style)
            if isinstance(border_style, str)
            else border_style
        )
        self.border_visibility: DiBool = (
            DiBool(
                border_visibility,
                border_visibility,
                border_visibility,
                border_visibility,
            )
            if isinstance(border_visibility, bool)
            else border_visibility
        )
        self.background_style: str = background_style

    @property
    def padding(self) -> DiInt:
        """The cell's padding."""
        return self._padding

    @padding.setter
    def padding(self, padding: DiInt | int) -> None:
        """Set the cell's padding."""
        self._padding = (
            DiInt(padding, padding, padding, padding)
            if isinstance(padding, int)
            else padding
        )

    @property
    def border_line(self) -> DiLineStyle:
        """The cell's border line."""
        return self._border_line

    @border_line.setter
    def border_line(self, border_line: DiLineStyle | LineStyle) -> None:
        """Set the cell's border line."""
        self._border_line = (
            DiLineStyle(border_line, border_line, border_line, border_line)
            if isinstance(border_line, LineStyle)
            else border_line
        )

    @property
    def border_style(self) -> DiStr:
        """The cell's border style."""
        return self._border_style

    @border_style.setter
    def border_style(self, border_style: DiStr | str) -> None:
        """Set the cell's border style."""
        self._border_style = (
            DiStr(border_style, border_style, border_style, border_style)
            if isinstance(border_style, str)
            else border_style
        )

    @property
    def width(self) -> Dimension:
        """The table's width."""
        return self._width

    @width.setter
    def width(self, value: AnyDimension) -> None:
        """Set the table's width."""
        self._width = to_dimension(value)

    @property
    def rows(self) -> list[Row]:
        """A list of rows in the table."""
        return [self._rows[i] for i in range(len(self._rows))]

    @property
    def cols(self) -> list[Col]:
        """A list of columns in the table."""
        return [self._cols[i] for i in range(len(self._cols))]

    def sync_rows_to_cols(self) -> None:
        """Enure cells in rows are present in the relevant columns."""
        cols = self._cols
        for i, row in self._rows.items():
            for j, cell in row._cells.items():
                cell.col = cols[j]
                cols[j]._cells[i] = cell

    def sync_cols_to_rows(self) -> None:
        """Enure cells in columns are present in the relevant rows."""
        rows = self._rows
        for i, col in self._cols.items():
            for j, cell in col._cells.items():
                cell.row = rows[j]
                rows[j]._cells[i] = cell

    def new_row(self, *args: Any, **kwargs: Any) -> Row:
        """Create a new row in the table."""
        row = Row(*args, **kwargs)
        self.add_row(row)
        return row

    def add_row(self, row: Row) -> None:
        """Add a row to the table."""
        row.table = self

        unfilled = [
            i
            for i, row in self._rows.items()
            if all(isinstance(cell, SpacerCell) for cell in row._cells.values())
        ]

        index = min(
            min([*unfilled, len(self._rows)]),
            max([-1, *list(self._rows)]) + 1,
        )

        # Merge existing row with new row
        cells = self._rows[index]._cells
        # Update column reference on existing cells
        for cell in cells.values():
            cell.row = row
        # Add cells from new row to the current cell list
        i = 0
        for cell in row._cells.values():
            while i in cells:
                i += 1
            cell._col_index = i
            cells[i] = cell
        # Update the new row's cell list
        row._cells = cells
        # Add the new row to the table
        self._rows[index] = row

    def new_col(self, *args: Any, **kwargs: Any) -> Col:
        """Create a new column in the table."""
        col = Col(*args, **kwargs)
        self.add_col(col)
        return col

    def add_col(self, col: Col) -> None:
        """Add a column to the table."""
        col.table = self

        unfilled = [
            i
            for i, col in self._cols.items()
            if all(isinstance(cell, SpacerCell) for cell in col._cells.values())
        ]

        index = min(
            min([*unfilled, len(self._cols)]),
            max([-1, *list(self._cols)]) + 1,
        )

        # Merge existing col with new col
        cells = self._cols[index]._cells
        # Update column reference on existing cells
        for cell in cells.values():
            cell.col = col
        # Add cells from new column to the current cell list
        i = 0
        for cell in col._cells.values():
            while i in cells:
                i += 1
            cell._row_index = i
            cells[i] = cell
        # Update the new columns's cell list
        col._cells = cells
        # Add the new column to the table
        self._cols[index] = col

    def calculate_col_widths(
        self,
        width: AnyDimension | None = None,
        min_col_width: int = 4,
    ) -> list[int]:
        """Calculate the table's column widths."""
        width = self.width if width is None else to_dimension(width)
        return calculate_col_widths(
            tuple(self.cols), width, self.expand, self.render_count
        )

    def calculate_cell_widths(
        self, width: AnyDimension | None = None
    ) -> dict[Cell, int]:
        """Calculate widths for each table cell, taking colspans into account."""
        render_count = self.render_count
        col_widths = self.calculate_col_widths(width)
        widths = {}
        for _y, row in enumerate(self.rows):
            for x, cell in enumerate(row.cells):
                widths[cell] = 0
                if cell.expands == cell:
                    colspan = cell.colspan
                    widths[cell] += sum(col_widths[x : x + colspan]) + sum(
                        compute_border_width(w, render_count).right
                        or compute_border_width(e, render_count).left
                        for w, e in pairwise(row.cells[x : x + colspan])
                    )
        return widths

    def draw_table_row(
        self,
        row_above: RowCol | None,
        row_below: RowCol | None,
        cell_widths: dict[Cell, int],
        col_widths: list[int],
        row_edge_visibility: bool,
        col_edge_visibilities: dict[int, bool],
    ) -> Iterable[StyleAndTextTuples]:
        """Draw a row in the table."""

        def _calc_cell_inner_width(cell: Cell) -> int:
            """Calculate a cell's inner width."""
            if isinstance(cell, SpacerCell) and cell.span_col_index > 0:
                return 0
            cell = cell.expands
            # Sum widths of spanned columns
            width = cell_widths[cell]
            # Remove padding
            padding = compute_padding(cell, render_count)
            width -= (padding.left or 0) + (padding.right or 0)
            return max(width, 0)

        #################

        assert row_above is not None or row_below is not None

        render_count = self.render_count
        dummy = _Dummy()

        row_above_cells: list[Cell]
        row_below_cells: list[Cell]
        if row_above is None:
            assert row_below is not None
            row_above_cells = [dummy] * len(row_below.cells)
        else:
            row_above_cells = row_above.cells
        if row_below is None:
            assert row_above is not None
            row_below_cells = [dummy] * len(row_above.cells)
        else:
            row_below_cells = row_below.cells
        row_above_cells_pad = [dummy, *row_above_cells, dummy]
        row_below_cells_pad = [dummy, *row_below_cells, dummy]

        if row_above is not None:
            # Skip rows where all cells expand a cell above
            # if all(
            #     isinstance(cell, SpacerCell) and cell.span_row_index > 0
            #     for cell in row_above_cells
            # ):
            #     return output_lines

            # Calculate borders
            borders = []
            render_count = self.render_count
            for i, (w, e) in enumerate(pairwise(row_above_cells_pad)):
                # We only need to check on cell to the left and one cell to the right
                if not col_edge_visibilities[i]:
                    borders.append(("", ""))

                else:
                    border_style = " ".join(
                        (
                            compute_border_style(e, render_count).left,
                            compute_border_style(w, render_count).right,
                        )
                    )
                    border_char = get_vertical_edge(
                        compute_border_line(w, render_count),
                        compute_border_line(e, render_count),
                    )
                    borders.append((border_style, border_char))

            # Draw row contents line by line

            # Calculate the lines in each cell.
            # The result of `compute_lines` is memoized, so the same list instance gets
            # returned each time we call this.
            # We will remove rows from the returned instance of each cell's line list
            # to keep track of remaining lines for row-span cells
            row_cell_lines = [
                compute_lines(
                    cell.expands,
                    width=_calc_cell_inner_width(cell),
                    render_count=render_count,
                )
                for col, cell in enumerate(row_above_cells)
            ]

            # We will iterate over a copy of each cell's lines, as we are removing
            # items from the list as we go
            row_lines = zip_longest(*(x[:] for x in row_cell_lines))
            for row_line in row_lines:
                output_line: StyleAndTextTuples = []

                # If we are not on the last row of a rowspan, carry lines over to the
                # next table row
                if all(
                    line is None
                    or (cell.rowspan > 1)
                    or (
                        isinstance(cell, SpacerCell)
                        and cell.expands.rowspan > 1
                        and (cell.span_row_index > 1 or cell.span_col_index)
                        and cell.span_row_index < cell.expands.rowspan - 1
                    )
                    or (
                        isinstance(cell, SpacerCell)
                        and cell.expands.colspan > 1
                        and cell.span_col_index
                    )
                    for line, cell in zip(row_line, row_above_cells)
                ):
                    break

                for i, (cell_line, cell, row_cell_line) in enumerate(
                    zip(row_line, row_above_cells, row_cell_lines)
                ):
                    # Skip horizontal spacer cells
                    if isinstance(cell, SpacerCell) and (cell.span_col_index):
                        continue

                    output_line.append(borders[i])

                    cell_style = compute_style(cell, render_count)
                    padding_style = f"{cell_style} nounderline"
                    padding = compute_padding(cell, render_count)
                    padding_left, padding_right = padding.left, padding.right

                    excess = _calc_cell_inner_width(cell) - fragment_list_width(
                        cell_line or []
                    )

                    output_line.extend(
                        [
                            (padding_style, " " * (padding_left or 0)),
                            *(cell_line or []),
                            (cell_style + " nounderline", " " * excess),
                            (padding_style, " " * (padding_right or 0)),
                        ]
                    )

                    if row_cell_line:
                        row_cell_line.pop(0)

                output_line.append(borders[i + 1])
                yield output_line

        ##################################
        # Draw border row below
        ##################################

        # Don't draw border rows if all cells expand a cell above
        if row_below and all(
            isinstance(cell, SpacerCell) and cell.span_row_index > 0
            for cell in row_below_cells
        ):
            return

        # Draw a border row if at least once cell above have a visible bottom border
        # or a cell below has a visible top border
        if row_edge_visibility:
            output_line = []

            for i, ((nw, ne), (sw, se)) in enumerate(
                zip(
                    pairwise(row_above_cells_pad),
                    pairwise(row_below_cells_pad),
                )
            ):
                cell = se

                # Skip horizontal spacer cells
                if (
                    isinstance(cell, SpacerCell)
                    and cell.span_col_index
                    and cell.span_row_index
                ):
                    continue

                nw_bs = compute_border_style(nw, render_count)
                ne_bs = compute_border_style(ne, render_count)
                se_bs = compute_border_style(se, render_count)
                sw_bs = compute_border_style(sw, render_count)

                if sw.expands == se.expands == nw.expands == ne.expands:
                    node_style = sw.expands.style
                else:
                    # TODO - use style where most directions agree
                    node_style = " ".join(
                        (
                            se_bs.left,
                            se_bs.top,
                            ne_bs.bottom,
                            ne_bs.left,
                            sw_bs.right,
                            sw_bs.top,
                            nw_bs.bottom,
                            nw_bs.right,
                        )
                    )
                # Do not draw border nodes if one dimension is not visible
                ne_bl = compute_border_line(ne, render_count)
                se_bl = compute_border_line(se, render_count)

                if not row_edge_visibility or not col_edge_visibilities[i]:
                    node_char = ""
                else:
                    node_char = get_node(
                        compute_border_line(nw, render_count),
                        ne_bl,
                        se_bl,
                        compute_border_line(sw, render_count),
                    )

                if node_char:
                    output_line.append((node_style, node_char))

                if i < len(row_above_cells):
                    if isinstance(cell, SpacerCell) and cell.span_row_index:
                        if remaining_lines := row_cell_lines[i]:
                            line = remaining_lines.pop(0)
                        else:
                            line = []
                        cell_style = compute_style(cell, render_count)
                        padding_style = f"{cell_style} nounderline"
                        padding = compute_padding(cell, render_count)
                        padding_left, padding_right = padding.left, padding.right
                        excess = _calc_cell_inner_width(cell) - fragment_list_width(
                            line or []
                        )
                        output_line.extend(
                            [
                                (padding_style, " " * (padding_left or 0)),
                                *line,
                                (cell_style, " " * excess),
                                (padding_style, " " * (padding_right or 0)),
                            ]
                        )
                        continue

                    style = " ".join((se_bs.top, ne_bs.bottom))
                    edge = get_horizontal_edge(ne_bl, se_bl)
                    text = edge * col_widths[i]
                    output_line += [(style, text)]

            yield output_line

    def render(self, width: AnyDimension | None = None) -> StyleAndTextTuples:
        """Draw the table, optionally at a given character width."""
        self.render_count += 1
        width = self.width if width is None else to_dimension(width)

        # Calculate border visibility
        render_count = self.render_count
        row_edge_visibilities: dict[int, bool] = defaultdict(bool)
        col_edge_visibilities: dict[int, bool] = defaultdict(bool)
        for y, row in enumerate(self.rows):
            for x, cell in enumerate(row.cells):
                bv = compute_border_visibility(cell, render_count)
                if bv.left:
                    col_edge_visibilities[x] = True
                if bv.right:
                    col_edge_visibilities[x + 1] = True
                if bv.top:
                    row_edge_visibilities[y] = True
                if bv.bottom:
                    row_edge_visibilities[y + 1] = True

        col_widths = self.calculate_col_widths(width)
        cell_widths = self.calculate_cell_widths(width)

        lines: list[StyleAndTextTuples] = []

        if self.rows:
            for i, (row_above, row_below) in enumerate(
                pairwise([None, *self.rows, None])
            ):
                lines.extend(
                    self.draw_table_row(
                        row_above,
                        row_below,
                        cell_widths,
                        col_widths,
                        row_edge_visibilities[i],
                        col_edge_visibilities,
                    )
                )

        return join_lines(lines)

    def __pt_formatted_text__(self) -> StyleAndTextTuples:
        """Render the table as formatted text."""
        return self.render()


class DummyRow(Row):
    """A dummy row - created to hold cells without an assigned column."""

    def add_cell(self, cell: Cell, index: int | None = None) -> None:
        """Prevent cells being added to a dummy row."""
        raise NotImplementedError("Cannot add a cell to a DummyRow")


class DummyCol(Col):
    """A dummy column - created to hold cells without an assigned column."""

    def add_cell(self, cell: Cell, index: int | None = None) -> None:
        """Prevent cells being added to a dummy column."""
        raise NotImplementedError("Cannot add a cell to a DummyCol")


class DummyTable(Table):
    """A dummy table - created to hold rows and columns without an assigned table."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Create a new dummy table."""
        kwargs["border_line"] = NoLine
        super().__init__(*args, **kwargs)

    def add_row(self, row: Row) -> None:
        """Prevent rows being added to a dummy table."""
        raise NotImplementedError("Cannot add a row to a DummyTable")

    def add_col(self, col: Col) -> None:
        """Prevent columns being added to a dummy table."""
        raise NotImplementedError("Cannot add a column to a DummyTable")
