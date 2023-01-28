"""Allows drawing tables as :class:`FormattedText`."""

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
    DiInt,
    DiStr,
)
from euporie.core.formatted_text.utils import (
    FormattedTextAlign,
    align,
    fragment_list_width,
    join_lines,
    max_line_width,
    wrap,
)

if TYPE_CHECKING:
    from typing import (
        Any,
        Iterable,
        Iterator,
        Optional,
        Sequence,
        TypeVar,
    )

    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        StyleAndTextTuples,
    )
    from prompt_toolkit.layout.dimension import AnyDimension

    PairT = TypeVar("PairT")


def pairwise(iterable: "Iterable[PairT]") -> "Iterator[tuple[PairT, PairT]]":
    """Returns successiver overlapping pairs from an iterable."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


class Cell:
    """A table cell."""

    def __init__(
        self,
        text: "AnyFormattedText" = "",
        row: "Row|None" = None,
        col: "Col|None" = None,
        colspan: "int" = 1,
        rowspan: "int" = 1,
        width: "int|None" = None,
        align: "FormattedTextAlign|None" = None,
        style: "str" = "",
        padding: "DiInt|int" = 0,
        border_line: "DiLineStyle|LineStyle" = NoLine,
        border_style: "DiStr|str" = "",
    ) -> "None":
        """Creates a new table cell.

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

    @property
    def padding(self) -> "DiInt":
        """The cell's padding."""
        return self._padding

    @padding.setter
    def padding(self, padding: "DiInt|int") -> "None":
        """Sets the cell's padding."""
        self._padding = (
            DiInt(padding, padding, padding, padding)
            if isinstance(padding, int)
            else padding
        )

    @property
    def border_line(self) -> "DiLineStyle":
        """The cell's border line."""
        return self._border_line

    @border_line.setter
    def border_line(self, border_line: "DiLineStyle|LineStyle") -> "None":
        """Sets the cell's border line."""
        self._border_line = (
            DiLineStyle(border_line, border_line, border_line, border_line)
            if isinstance(border_line, LineStyle)
            else border_line
        )

    @property
    def border_style(self) -> "DiStr":
        """The cell's border style."""
        return self._border_style

    @border_style.setter
    def border_style(self, border_style: "DiStr|str") -> "None":
        """Sets the cell's border style."""
        self._border_style = (
            DiStr(border_style, border_style, border_style, border_style)
            if isinstance(border_style, str)
            else border_style
        )

    def __repr__(self) -> "str":
        """Returns a text representation of the cell."""
        cell_text = to_plain_text(self.text)
        if len(cell_text) > 5:
            cell_text = cell_text[:4] + "…"
        return f"{self.__class__.__name__}({cell_text!r})"


class SpacerCell(Cell):
    """A dummy cell to virtually occupy space when ``colspan`` or ``rowspan`` are used."""

    def __init__(
        self,
        expands: "Cell",
        span_index: "int",
        text: "AnyFormattedText" = "",
        row: "Optional[Row]" = None,
        col: "Optional[Col]" = None,
        colspan: "int" = 1,
        rowspan: "int" = 1,
        width: "Optional[int]" = None,
        align: "Optional[FormattedTextAlign]" = None,
        style: "str" = "",
        padding: "DiInt|int|None" = None,
        border_line: "DiLineStyle|LineStyle" = NoLine,
        border_style: "DiStr|str" = "",
    ) -> "None":
        """Creates a new table cell.

        Args:
            expands: This should be reference to the spanning cell
            span_index: The index of a spacer cell inside a colspan / rowspan
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
            padding=0,
            border_line=expands.border_line,
            border_style=expands.border_style,
        )
        self.expands = expands
        self.span_index = span_index


class DummyCell(Cell):
    """A dummy cell with not content, padding or borders."""

    def __repr__(self) -> "str":
        """String representation of the cell."""
        return f"{self.__class__.__name__}()"


class RowCol:
    """Base class for table rows and columns."""

    type_: "str"
    span_type: "str"

    def __init__(
        self,
        table: "Optional[Table]" = None,
        cells: "Optional[Sequence[Cell]]" = None,
        align: "Optional[FormattedTextAlign]" = None,
        style: "str" = "",
        padding: "DiInt|int" = 0,
        border_line: "DiLineStyle|LineStyle" = NoLine,
        border_style: "DiStr|str" = "",
    ) -> "None":
        """Create a new row/column.

        Args:
            table: The :py:class:`table` that this row/column belongs to
            cells: A list of cells in this row/column
            align: The default alignment for cells in this row/column
            style: The default style for cells in this row/column
            padding: The default padding for cells in this row/column
            border_line: The line to use for the borders
            border_style: The style to apply to the table's borders

        """
        self.table = table or DummyTable()
        self._cells = defaultdict(lambda: DummyCell(), enumerate(cells or []))
        if cells:
            for cell in cells:
                setattr(cell, self.type_, self)

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

    @property
    def padding(self) -> "DiInt":
        """The cell's padding."""
        return self._padding

    @padding.setter
    def padding(self, padding: "DiInt|int") -> "None":
        """Sets the cell's padding."""
        self._padding = (
            DiInt(padding, padding, padding, padding)
            if isinstance(padding, int)
            else padding
        )

    @property
    def border_line(self) -> "DiLineStyle":
        """The cell's border line."""
        return self._border_line

    @border_line.setter
    def border_line(self, border_line: "DiLineStyle|LineStyle") -> "None":
        """Sets the cell's border line."""
        self._border_line = (
            DiLineStyle(border_line, border_line, border_line, border_line)
            if isinstance(border_line, LineStyle)
            else border_line
        )

    @property
    def border_style(self) -> "DiStr":
        """The cell's border style."""
        return self._border_style

    @border_style.setter
    def border_style(self, border_style: "DiStr|str") -> "None":
        """Sets the cell's border style."""
        self._border_style = (
            DiStr(border_style, border_style, border_style, border_style)
            if isinstance(border_style, str)
            else border_style
        )

    @property
    def cells(self) -> "list[Cell]":
        """Lists the cells in the row/column."""
        return [self._cells[i] for i in range(len(self._cells))]

    def new_cell(self, *args: "Any", **kwargs: "Any") -> "Cell":
        """Create a new cell in this row/column."""
        cell = Cell(*args, **kwargs)
        self.add_cell(cell)
        return cell

    def add_cell(self, cell: "Cell") -> "None":
        """Adds a cell to the row/ column."""
        index = max([-1] + list(self._cells.keys())) + 1
        self._cells[index] = cell

        if self.type_ == "row":
            assert isinstance(self, Row)
            cell.row = cast("Row", self)
            cell.col = self.table._cols[index]

            row_index = self.table.rows.index(self)
            col_index = index

            cell.col._cells[row_index] = cell

            if cell.colspan > 1:
                for i in range(1, cell.colspan):
                    spacer = SpacerCell(
                        expands=cell,
                        span_index=i,
                        row=cell.row,
                        col=self.table._cols[col_index + i],
                    )
                    self._cells[col_index + i] = spacer
                    spacer.col._cells[row_index] = spacer

            if cell.rowspan > 1:
                for i in range(1, cell.rowspan):
                    spacer = SpacerCell(
                        expands=cell,
                        span_index=i,
                        row=self.table._rows[row_index + i],
                        col=cell.col,
                    )
                    cell.col._cells[row_index + i] = spacer
                    spacer.row._cells[col_index] = spacer

        elif self.type_ == "col":
            assert isinstance(self, Col)
            cell.row = self.table._rows[index]
            cell.col = cast("Col", self)

            row_index = index
            col_index = self.table.cols.index(self)

            cell.row._cells[col_index] = cell

            if cell.rowspan > 1:
                for i in range(1, cell.rowspan):
                    spacer = SpacerCell(
                        expands=cell,
                        span_index=i,
                        row=self.table._rows[index + i],
                        col=cell.col,
                    )
                    self._cells[row_index + i] = spacer
                    spacer.row._cells[col_index] = spacer

            if cell.colspan > 1:
                index = max(cell.row._cells.keys())
                for i in range(1, cell.colspan):
                    spacer = SpacerCell(
                        expands=cell,
                        span_index=i,
                        row=cell.row,
                        col=self.table._cols[col_index + i],
                    )
                    cell.row._cells[col_index + i] = spacer
                    spacer.col._cells[row_index] = spacer

    def __repr__(self) -> "str":
        """Returns a textual representation of the row or column."""
        return f"{self.__class__.__name__}({', '.join(map(str, self._cells.values()))})"


class Row(RowCol):
    """A row in a table."""

    type_ = "row"
    span_type = "colspan"


class Col(RowCol):
    """A column in a table."""

    type_ = "col"
    span_type = "rowspan"


@lru_cache
def compute_style(cell: Cell, render_count: int = 0) -> "str":
    """The cell's computed style."""
    return f"{cell.row.table.style} {cell.col.style} {cell.row.style} {cell.style}"


###############


@lru_cache
def compute_text(cell: Cell, render_count: int = 0) -> "StyleAndTextTuples":
    """The cell's input, converted to :class:`FormattedText`."""
    return to_formatted_text(cell.text, style=compute_style(cell))


@lru_cache
def compute_padding(cell: Cell, render_count: int = 0) -> "DiInt":
    """The cell's padding."""
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


###############


@lru_cache
def calculate_cell_width(cell: Cell, render_count: int = 0) -> int:
    """The width of the cell including padding."""
    if cell.colspan > 1:
        return 0
    padding = compute_padding(cell, render_count)
    return (
        (cell.width or max_line_width(compute_text(cell, render_count)))
        + padding.left
        + padding.right
    )


@lru_cache
def compute_border_line(cell: Cell, render_count: int = 0) -> "DiLineStyle":
    """The cell's border line."""
    output = {}
    cell_border_line = cell.border_line
    row_border_line = cell.row.border_line
    col_border_line = cell.col.border_line
    table_border_line = cell.row.table.border_line
    for direction in ("top", "right", "bottom", "left"):
        for source in (
            cell_border_line,
            row_border_line,
            col_border_line,
            table_border_line,
        ):
            value = getattr(source, direction, NoLine)
            if value is not NoLine:
                break
        output[direction] = value

    expands = cell.expands
    if expands != cell:
        # Set left border to invisible in colspan
        if expands.colspan > 1:
            output["left"] = InvisibleLine
        # Set top border to invisible in rowspan
        if expands.rowspan > 1:
            output["top"] = InvisibleLine

    return DiLineStyle(**output)


@lru_cache
def compute_border_width(cell: Cell, render_count: int = 0) -> "DiInt":
    """The style for the cell's borders."""
    if isinstance(cell, DummyCell):
        return DiInt(0, 0, 0, 0)

    output = {"top": 1, "right": 1, "bottom": 1, "left": 1}

    row = cell.row
    col = cell.col
    table = col.table

    if row not in table._rows.values():
        # The table has not yet been fully constructed
        return DiInt(1, 1, 1, 1)

    row_index = table.rows.index(row)
    col_index = table.cols.index(col)

    row_top = table._rows.get(row_index - 1)
    col_right = table._cols.get(col_index + 1)
    row_bottom = table._rows.get(row_index + 1)
    col_left = table._cols.get(col_index - 1)

    if table.collapse_empty_borders:
        output["top"] = (
            any(
                compute_border_line(cell.expands, render_count).top.visible
                for cell in row.cells
            )
            or (
                row_top
                and any(
                    compute_border_line(cell.expands, render_count).bottom.visible
                    for cell in row_top.cells
                )
            )
            or 0
        )
        output["right"] = (
            any(
                compute_border_line(cell.expands, render_count).right.visible
                for cell in col.cells
            )
            or (
                col_right
                and any(
                    compute_border_line(cell.expands, render_count).left.visible
                    for cell in col_right.cells
                )
            )
            or 0
        )
        output["bottom"] = (
            any(
                compute_border_line(cell.expands, render_count).bottom.visible
                for cell in row.cells
            )
            or (
                row_bottom
                and any(
                    compute_border_line(cell.expands, render_count).top.visible
                    for cell in row_bottom.cells
                )
            )
            or 0
        )
        output["left"] = (
            any(
                compute_border_line(cell.expands, render_count).left.visible
                for cell in col.cells
            )
            or (
                col_left
                and any(
                    compute_border_line(cell.expands, render_count).right.visible
                    for cell in col_left.cells
                )
            )
            or 0
        )

    return DiInt(**output)


@lru_cache
def calculate_col_widths(
    cols: "tuple[Col]",
    width: "Dimension",
    expand_to_width: "bool",
    min_col_width: "int" = 2,
    render_count: int = 0,
) -> "list[int]":
    """Calculate column widths given the available space.

    Reduce the widest column until we fit in available width, or expand cells to
    to fill the available width.

    Args:
        width: The desired width of the table
        min_col_width: The minimum width allowed for a column

    Returns:
        List of new column widths

    """
    # TODO - this function is too slow
    col_widths = [
        max(
            [
                *[calculate_cell_width(cell, render_count) for cell in col.cells],
                min_col_width,
            ]
        )
        for col in cols
    ]

    def total_width(col_widths: "list[int]") -> "int":
        """Calculate the total width of the columns including borders."""
        width = sum(col_widths)
        for col in cols:
            width += compute_border_width(col.cells[0], render_count).right
        if cols:
            width += compute_border_width(cols[0].cells[0], render_count).left
        return width

    def expand(target: "int") -> "None":
        """Expand the columns."""
        max_width = max(target, len(col_widths) * min_col_width)
        while total_width(col_widths) < max_width:
            # Expand only columns which do not have a width set if possible
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

    def contract(target: "int") -> "None":
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
    elif width.max_specified:
        if current_width > width.max:
            contract(width.max)
        if current_width < width.max and expand_to_width:
            expand(width.max)
    elif width.min_specified and current_width < width.min:
        expand(width.min)

    return col_widths


@lru_cache
def get_node(
    nw_bl: "DiLineStyle",
    ne_bl: "DiLineStyle",
    se_bl: "DiLineStyle",
    sw_bl: "DiLineStyle",
) -> "str":
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
def get_horizontal_edge(n_bl: "DiLineStyle", s_bl: "DiLineStyle") -> "str":
    """Calculate which character to use to divide horizontally adjacent cells."""
    line_style = max(n_bl.bottom, s_bl.top)
    return get_grid_char(GridChar(NoLine, line_style, NoLine, line_style))


@lru_cache
def get_vertical_edge(w_bl: "DiLineStyle", e_bl: "DiLineStyle") -> "str":
    """Calculate which character to use to divide vertically adjacent cells."""
    line_style = max(w_bl.right, e_bl.left)
    return get_grid_char(GridChar(line_style, NoLine, line_style, NoLine))


@lru_cache
def compute_align(cell: Cell, render_count: int = 0) -> "FormattedTextAlign":
    """The cell's alignment."""
    if (align := cell.align) is not None:
        return align
    else:
        return cell.row.align or cell.col.align or cell.row.table.align


def compute_lines(
    cell: Cell, width: "int", render_count: int = 0
) -> "Iterable[StyleAndTextTuples]":
    """Wraps the cell's text to a given width.

    Args:
        width: The width at which to wrap the cell's text.

    Returns:
        A list of lines of formatted text
    """
    padding = compute_padding(cell, render_count)
    return split_lines(
        align(
            wrap(
                [
                    ("", "\n" * (padding.top or 0)),
                    *compute_text(cell, render_count),
                    ("", "\n" * (padding.bottom or 0)),
                ],
                width=width,
            ),
            compute_align(cell, render_count),
            width=width,
            style=compute_style(cell, render_count),
        )
    )


@lru_cache
def compute_border_style(cell: Cell, render_count: int = 0) -> "DiStr":
    """The style for the cell's borders."""
    table_ = cell.row.table.border_style
    row_ = cell.row.border_style
    col_ = cell.col.border_style
    cell_ = cell.border_style
    output = {}
    for direction, line in zip(
        ("top", "right", "bottom", "left"),
        compute_border_line(cell, render_count),
    ):
        if line.visible:
            output[direction] = " ".join(
                (
                    getattr(table_, direction),
                    getattr(row_, direction),
                    getattr(col_, direction),
                    getattr(cell_, direction),
                )
            )
        else:
            output[direction] = ""

    expands = cell.expands
    if expands != cell:
        # Set left border to invisible in colspan
        if expands.colspan > 1:
            output["left"] = expands.style
        # Set top border to invisible in rowspan
        if expands.rowspan > 1:
            output["top"] = expands.style

    return DiStr(**output)


class Table:
    """A table."""

    collapse_empty_borders: bool

    def __init__(
        self,
        rows: "Optional[Sequence[Row]]" = None,
        cols: "Optional[Sequence[Col]]" = None,
        width: "AnyDimension|None" = None,
        expand: "bool" = False,
        align: "FormattedTextAlign" = FormattedTextAlign.LEFT,
        style: "str" = "",
        padding: "DiInt|int|None" = None,
        border_line: "DiLineStyle|LineStyle" = ThinLine,
        border_style: "DiStr|str" = "",
        border_spacing: "int" = 0,
        collapse_empty_borders: "bool" = True,
    ) -> "None":
        """Creates a new table instance.

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
            border_spacing: The distance between cell borders
            collapse_empty_borders: If :const:`True`, if borders in the table are
                :class:`Invisible` for their entire length, no extra line will be drawn

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

        self.collapse_empty_borders = collapse_empty_borders
        self.border_spacing = border_spacing

    @property
    def padding(self) -> "DiInt":
        """The cell's padding."""
        return self._padding

    @padding.setter
    def padding(self, padding: "DiInt|int") -> "None":
        """Sets the cell's padding."""
        self._padding = (
            DiInt(padding, padding, padding, padding)
            if isinstance(padding, int)
            else padding
        )

    @property
    def border_line(self) -> "DiLineStyle":
        """The cell's border line."""
        return self._border_line

    @border_line.setter
    def border_line(self, border_line: "DiLineStyle|LineStyle") -> "None":
        """Sets the cell's border line."""
        self._border_line = (
            DiLineStyle(border_line, border_line, border_line, border_line)
            if isinstance(border_line, LineStyle)
            else border_line
        )

    @property
    def border_style(self) -> "DiStr":
        """The cell's border style."""
        return self._border_style

    @border_style.setter
    def border_style(self, border_style: "DiStr|str") -> "None":
        """Sets the cell's border style."""
        self._border_style = (
            DiStr(border_style, border_style, border_style, border_style)
            if isinstance(border_style, str)
            else border_style
        )

    @property
    def width(self) -> "Dimension":
        """The table's width."""
        return self._width

    @width.setter
    def width(self, value: "AnyDimension") -> "None":
        """Set the table's width."""
        self._width = to_dimension(value)

    @property
    def rows(self) -> "list[Row]":
        """A list of rows in the table."""
        return [self._rows[i] for i in range(len(self._rows))]

    @property
    def cols(self) -> "list[Col]":
        """A list of columns in the table."""
        return [self._cols[i] for i in range(len(self._cols))]

    def sync_rows_to_cols(self) -> "None":
        """Ensure cells in rows are present in the relevant columns."""
        cols = self._cols
        for i, row in self._rows.items():
            for j, cell in row._cells.items():
                cell.col = cols[j]
                cols[j]._cells[i] = cell

    def sync_cols_to_rows(self) -> "None":
        """Ensure cells in columns are present in the relevant rows."""
        rows = self._rows
        for i, col in self._cols.items():
            for j, cell in col._cells.items():
                cell.row = rows[j]
                rows[j]._cells[i] = cell

    def new_row(self, *args: "Any", **kwargs: "Any") -> "Row":
        """Creates a new row in the table."""
        row = Row(*args, **kwargs)
        self.add_row(row)
        return row

    def add_row(self, row: "Row") -> "None":
        """Add a row to the table."""
        row.table = self

        unfilled = [
            i
            for i, row in self._rows.items()
            if all([isinstance(cell, SpacerCell) for cell in row._cells.values()])
        ]

        index = min(
            min(unfilled + [len(self._rows)]),
            max([-1] + list(self._rows)) + 1,
        )

        # Merge existing row with new row
        cells = self._rows[index]._cells
        i = 0
        for cell in row.cells:
            while i in cells:
                i += 1
            cells[i] = cell
        row._cells = cells
        self._rows[index] = row

    def new_col(self, *args: "Any", **kwargs: "Any") -> "Col":
        """Creates a new column in the table."""
        col = Col(*args, **kwargs)
        self.add_col(col)
        return col

    def add_col(self, col: "Col") -> "None":
        """Add a column to the table."""
        col.table = self

        unfilled = [
            i
            for i, col in self._cols.items()
            if all([isinstance(cell, SpacerCell) for cell in col._cells.values()])
        ]

        index = min(
            min(unfilled + [len(self._cols)]),
            max([-1] + list(self._cols)) + 1,
        )

        # Merge existing col with new col
        cells = self._cols[index]._cells
        i = 0
        for cell in col.cells:
            while i in cells:
                i += 1
            cells[i] = cell
        col._cells = cells
        self._cols[index] = col

    def calculate_col_widths(
        self,
        width: "AnyDimension|None" = None,
        min_col_width: "int" = 4,
    ) -> "list[int]":
        """Calculate the table's column widths."""
        width = self.width if width is None else to_dimension(width)
        return calculate_col_widths(tuple(self.cols), width, self.expand)

    def draw_border_row(
        self,
        row_above: "Optional[Row]",
        row_below: "Optional[Row]",
        col_widths: "list[int]",
        collapse_empty_borders: "bool",
    ) -> "StyleAndTextTuples":
        """Draws a border line separating two rows in the table."""
        output: "StyleAndTextTuples" = []
        if row_above is not None:
            row_above_cells = row_above.cells
        else:
            assert row_below is not None
            row_above_cells = [DummyCell()] * len(row_below.cells)
        if row_below is not None:
            row_below_cells = row_below.cells
        else:
            assert row_above is not None
            row_below_cells = [DummyCell()] * len(row_above.cells)

        cells_above = [DummyCell(), *(row_above_cells), DummyCell()]
        cells_below = [DummyCell(), *(row_below_cells), DummyCell()]
        edges = ""

        render_count = self.render_count

        for i, ((nw, ne), (sw, se)) in enumerate(
            zip(
                pairwise(cells_above),
                pairwise(cells_below),
            )
        ):
            sw_bs = compute_border_style(sw, render_count)
            ne_bs = compute_border_style(ne, render_count)
            se_bs = compute_border_style(se, render_count)
            nw_bs = compute_border_style(nw, render_count)

            node_style = " ".join(
                (
                    sw_bs.top,
                    sw_bs.right,
                    ne_bs.bottom,
                    ne_bs.left,
                    se_bs.top,
                    se_bs.left,
                    nw_bs.bottom,
                    nw_bs.right,
                )
            )
            node_char = get_node(
                compute_border_line(nw, render_count),
                ne_bl := compute_border_line(ne, render_count),
                se_bl := compute_border_line(se, render_count),
                compute_border_line(sw, render_count),
            )

            # Do not draw border row if border collapse is on and all parts are invisible
            if (
                not compute_border_width(nw, render_count).right
                and not compute_border_width(ne, render_count).left
            ):
                node_char = node_char.strip()

            if node_char:
                output.append((node_style, node_char))

            if i < len(col_widths):
                style = " ".join((se_bs.top, ne_bs.bottom))
                edge = get_horizontal_edge(ne_bl, se_bl)
                edges = f"{edges}{edge}"
                output += [(style, edge * col_widths[i])]

        # Do not draw border row if border collapse is on and all parts are invisible
        if collapse_empty_borders and not edges.strip():
            return []

        return output

    def draw_table_row(
        self,
        row: "Optional[RowCol]",
        col_widths: "list[int]",
        collapse_empty_borders: "bool",
    ) -> "StyleAndTextTuples":
        """Draws a row in the table."""
        output_lines: "list[StyleAndTextTuples]" = []
        if row:
            # Calculate borders
            borders = []
            render_count = self.render_count
            for w, e in zip([DummyCell(), *row.cells], [*row.cells, DummyCell()]):

                border_style = " ".join(
                    (
                        compute_border_style(w, render_count).right,
                        compute_border_style(e, render_count).left,
                    )
                )
                border_char = get_vertical_edge(
                    compute_border_line(w, render_count),
                    compute_border_line(e, render_count),
                )

                # We only need to check on cell to the left and one cell to the right
                if self.collapse_empty_borders and (
                    not compute_border_width(w, render_count).right
                    and not compute_border_width(e, render_count).left
                ):
                    border_char = border_char.strip()

                borders.append((border_style, border_char))

            def _calc_cell_width(
                cell: "Cell", col: "int", col_widths: "list[int]"
            ) -> "int":
                """Calculate a cell's width."""
                if isinstance(cell, SpacerCell) and cell.expands.colspan > 1:
                    return 0
                width = col_widths[col]
                # Remove padding
                padding = compute_padding(cell, render_count)
                width -= (padding.left or 0) + (padding.right or 0)

                # Expand if colspan
                for i in range(col + 1, col + cell.colspan):
                    width += col_widths[i]
                    if borders[col]:
                        width += 1

                return width

            # Draw row contents line by line
            row_lines = zip_longest(
                *(
                    compute_lines(
                        cell,
                        width=_calc_cell_width(cell, col, col_widths),
                        render_count=render_count,
                    )
                    for col, cell in enumerate(row.cells)
                )
            )

            for row_line in row_lines:
                output_line: "StyleAndTextTuples" = []
                for i, (line, cell) in enumerate(zip(row_line, row.cells)):
                    # Skip spacer cells
                    if isinstance(cell, SpacerCell) and cell.expands.colspan > 1:
                        continue
                    output_line.append(borders[i])

                    padding_style = f"{cell.style} nounderline"
                    padding = compute_padding(cell, render_count)
                    padding_left, padding_right = padding.left, padding.right

                    excess = (
                        sum(col_widths[i : i + cell.colspan])
                        - padding_left
                        - fragment_list_width(line or [])
                        - padding_right
                    )

                    output_line.extend(
                        [
                            (padding_style, " " * (padding.left or 0)),
                            *(line or []),
                            (cell.style, " " * excess),
                            (padding_style, " " * (padding.right or 0)),
                        ]
                    )
                output_line.append(borders[i + 1])
                output_lines.append(output_line)

        return join_lines(output_lines)

    def render(self, width: "AnyDimension|None" = None) -> "StyleAndTextTuples":
        """Draws the table, optionally at a given character width."""
        self.render_count += 1
        width = self.width if width is None else to_dimension(width)
        col_widths = self.calculate_col_widths(width)
        lines = []

        if self.rows:
            collapse_empty_borders = self.collapse_empty_borders
            for row_above, row_below in zip([None, *self.rows], [*self.rows, None]):
                if line := self.draw_border_row(
                    row_above, row_below, col_widths, collapse_empty_borders
                ):
                    lines.append(line)
                if line := self.draw_table_row(
                    row_below, col_widths, collapse_empty_borders
                ):
                    lines.append(line)
        return join_lines(lines)

    def __pt_formatted_text__(self) -> "StyleAndTextTuples":
        """Render the table as formatted text."""
        return self.render()


class DummyRow(Row):
    """A dummy row - created to hold cells without an assigned column."""

    def add_cell(self, cell: "Cell") -> "None":
        """Prevents cells being added to a dummy row."""
        raise NotImplementedError("Cannot add a cell to a DummyRow")


class DummyCol(Col):
    """A dummy column - created to hold cells without an assigned column."""

    def add_cell(self, cell: "Cell") -> "None":
        """Prevents cells being added to a dummy column."""
        raise NotImplementedError("Cannot add a cell to a DummyCol")


class DummyTable(Table):
    """A dummy table - created to hold rows and columns without an assigned table."""

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Create a new dummy table."""
        kwargs["border_line"] = NoLine
        super().__init__(*args, **kwargs)

    def add_row(self, row: "Row") -> "None":
        """Prevents rows being added to a dummy table."""
        raise NotImplementedError("Cannot add a row to a DummyTable")

    def add_col(self, col: "Col") -> "None":
        """Prevents columns being added to a dummy table."""
        raise NotImplementedError("Cannot add a column to a DummyTable")
