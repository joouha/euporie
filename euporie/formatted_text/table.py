"""Allows drawing tables as :class:`FormattedText`."""

from collections import defaultdict
from functools import partial
from itertools import tee, zip_longest
from typing import TYPE_CHECKING, NamedTuple, cast

from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines, to_plain_text

from euporie.border import GridChar, Invisible, LineStyle, Thin, grid_char
from euporie.formatted_text.utils import FormattedTextAlign, align, max_line_width, wrap

if TYPE_CHECKING:
    from typing import (
        Any,
        Iterable,
        Iterator,
        List,
        Optional,
        Sequence,
        Tuple,
        TypeVar,
        Union,
    )

    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        FormattedText,
        StyleAndTextTuples,
    )

    PairT = TypeVar("PairT")


def pairwise(iterable: "Iterable[PairT]") -> "Iterator[Tuple[PairT, PairT]]":
    """Returns successiver overlapping pairs from an iterable."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


class WeightedLineStyle(NamedTuple):
    """A :class:`LineStyle` with a weight."""

    weight: "int"
    value: "LineStyle"


class WeightedInt(NamedTuple):
    """An :class:`int` with a weight."""

    weight: "int"
    value: "int"


class CellBorder(NamedTuple):
    """A description of a cell border: a :class:`LineStyle` for each edge."""

    top: "Optional[LineStyle]" = None
    right: "Optional[LineStyle]" = None
    bottom: "Optional[LineStyle]" = None
    left: "Optional[LineStyle]" = None


class WeightedCellBorder(NamedTuple):
    """A weighted description of a cell border: weighted values for each edge."""

    top: "WeightedLineStyle"
    right: "WeightedLineStyle"
    bottom: "WeightedLineStyle"
    left: "WeightedLineStyle"


class CellPadding(NamedTuple):
    """A weighted description of a cell padding: weighted values for each edge."""

    top: "Optional[int]"
    right: "Optional[int]"
    bottom: "Optional[int]"
    left: "Optional[int]"


class WeightedCellPadding(NamedTuple):
    """A description of a cell padding: :class:`LineStyle`s for each edge."""

    top: "WeightedInt"
    right: "WeightedInt"
    bottom: "WeightedInt"
    left: "WeightedInt"


class Cell:
    """A table cell."""

    def _set_padding(self, padding: "Optional[Union[CellPadding, int]]") -> "None":
        """Sets the cell's padding."""
        if padding is None:
            padding = CellPadding(None, None, None, None)
        if isinstance(padding, int):
            padding = CellPadding(padding, padding, padding, padding)
        if len(padding) == 2:
            padding = CellPadding(padding[0], padding[1], padding[0], padding[1])
        self._padding = padding or CellPadding(None, None, None, None)

    def _set_border(self, border: "Optional[Union[LineStyle, CellBorder]]") -> "None":
        """Sets the cell's border."""
        if border is None:
            _border = CellBorder(None, None, None, None)
        elif isinstance(border, LineStyle):
            _border = CellBorder(border, border, border, border)
        elif isinstance(border, tuple) and len(border) == 2:
            _border = CellBorder(border[0], border[1], border[0], border[1])
        else:
            _border = border
        self._border = _border

    def __init__(
        self,
        text: "AnyFormattedText" = "",
        row: "Optional[Row]" = None,
        col: "Optional[Col]" = None,
        align: "Optional[FormattedTextAlign]" = None,
        padding: "Optional[CellPadding]" = None,
        border: "Optional[Union[LineStyle, CellBorder]]" = None,
        style: "str" = "",
    ):
        """Creates a new table cell.

        Args:
            text: Text or formatted text to display in the cell
            row: The row to which this cell belongs
            col: The column to which this cell belongs
            align: How the text in the cell should be aligned
            padding: The padding around the contents of the cell
            border: The type of border line to apply to the cell
            style: The style to apply to the cell's contents

        """
        self._text = text
        self.row = row or DummyRow()
        self.col = col or DummyCol()
        self._align = align
        self._set_padding(padding)
        self._set_border(border)
        self._style = ""
        self.style = style

    @property
    def text(self) -> "FormattedText":
        """The cell's input, converted to :class:`FormattedText`."""
        return to_formatted_text(self._text, style=self.style)

    @text.setter
    def text(self, text: "AnyFormattedText") -> "None":
        """Sets the cell's text."""
        self._text = text

    def lines(self, width: "int") -> "Iterable[StyleAndTextTuples]":
        """Wraps the cell's text to a given width.

        Args:
            width: The width at which to wrap the cell's text.

        Returns:
            A list of lines of formatted text
        """
        return split_lines(
            align(
                self.align,
                wrap(
                    [
                        ("", "\n" * (self.padding.top or 0)),
                        *self.text,
                        ("", "\n" * (self.padding.bottom or 0)),
                    ],
                    width=width,
                ),
                width=width,
                style=self.style,
            )
        )

    @property
    def width(self) -> "int":
        """The width of the cell excluding padding."""
        return max_line_width(self.text)

    @property
    def total_width(self) -> "int":
        """The width of the cell including padding."""
        return self.width + (self.padding.left or 0) + (self.padding.right or 0)

    @property
    def height(self) -> "int":
        """The height of the cell excluding padding."""
        return len(list(split_lines(self.text)))

    @property
    def align(self) -> "FormattedTextAlign":
        """The cell's alignment."""
        if self._align is not None:
            return self._align
        else:
            if self.row._align is not None:
                return self.row.align
            return self.col.align

    @align.setter
    def align(self, align: "FormattedTextAlign") -> "None":
        """Set the cell's alignment."""
        self._align = align

    @property
    def weighted_padding(self) -> "WeightedCellPadding":
        """The cell's padding with inheritance weights."""
        return WeightedCellPadding(
            *(
                WeightedInt(
                    2
                    if x is not None
                    else max(
                        self.row.weighted_padding[i],
                        self.col.weighted_padding[i],
                    ).weight,
                    max(
                        self.row.weighted_padding[i], self.col.weighted_padding[i]
                    ).value
                    if x is None
                    else x,
                )
                for i, x in enumerate(self._padding)
            )
        )

    @property
    def padding(self) -> "CellPadding":
        """The cell's padding."""
        return CellPadding(*(x.value for x in self.weighted_padding))

    @padding.setter
    def padding(self, padding: "Optional[Union[CellPadding, int]]") -> "None":
        """Sets the cell's padding."""
        self._set_padding(padding)

    @property
    def weighted_border(self) -> "WeightedCellBorder":
        """The cell's borders with inheritance weights."""
        return WeightedCellBorder(
            *(
                WeightedLineStyle(
                    2
                    if x
                    else max(
                        self.row.weighted_border[i], self.col.weighted_border[i]
                    ).weight,
                    x
                    or max(
                        self.row.weighted_border[i], self.col.weighted_border[i]
                    ).value,
                )
                for i, x in enumerate(self._border)
            )
        )

    @property
    def border(self) -> "CellBorder":
        """The cell's border."""
        return CellBorder(*(x.value for x in self.weighted_border))

    @border.setter
    def border(self, border: "Optional[Union[LineStyle, CellBorder]]") -> "None":
        """Sets the cell's border."""
        self._set_border(border)

    @property
    def style(self) -> "str":
        """The cell's style."""
        if self.row is None and self.col is None:
            return self._style
        if self.row is None:
            return f"{self.col.style} {self._style}"
        if self.col is None:
            return f"{self.col.style} {self._style}"
        return f"{self.col.style} {self.row.style} {self._style}"

    @style.setter
    def style(self, style: "str") -> "None":
        """Sets the cell's style."""
        self._style = style

    def __repr__(self) -> "str":
        """Returns a text representation of the cell."""
        cell_text = to_plain_text(self._text)
        if len(cell_text) > 5:
            cell_text = cell_text[:4] + "???"
        return f'Cell("{cell_text}")'


class RowCol:
    """Base class for table rows and columns."""

    type_: "str"

    def _set_padding(self, padding: "Optional[Union[CellPadding, int]]") -> "None":
        """The default padding for cells in the row/column."""
        if padding is None:
            padding = CellPadding(None, None, None, None)
        if isinstance(padding, int):
            padding = CellPadding(padding, padding, padding, padding)
        if len(padding) == 2:
            padding = CellPadding(padding[0], padding[1], padding[0], padding[1])
        self._padding = padding

    def _set_border(self, border: "Optional[Union[LineStyle, CellBorder]]") -> "None":
        """Set the default border style for cells in the row/column."""
        if border is None:
            _border = CellBorder(None, None, None, None)
        elif isinstance(border, LineStyle):
            _border = CellBorder(border, border, border, border)
        elif isinstance(border, tuple) and len(border) == 2:
            _border = CellBorder(border[0], border[1], border[0], border[1])
        else:
            _border = border
        self._border = _border

    def __init__(
        self,
        table: "Optional[Table]" = None,
        cells: "Optional[Sequence[Cell]]" = None,
        align: "Optional[FormattedTextAlign]" = None,
        padding: "Optional[CellPadding]" = None,
        border: "Optional[Union[LineStyle, CellBorder]]" = None,
        style: "str" = "",
    ):
        """Create a new row/column.

        Args:
            table: The :py:class:`table` that this row/column belongs to
            cells: A list of cells in this row/column
            align: The default alignment for cells in this row/column
            padding: The default padding for cells in this row/column
            border: The default border for cells in this row/column
            style: The default style for cells in this row/column

        """
        self.table = table or DummyTable()
        self._cells = defaultdict(lambda: Cell(), enumerate(cells or []))
        if cells:
            for cell in cells:
                setattr(cell, self.type_, self)

        self._align = align
        self._set_padding(padding)
        self._set_border(border)
        self._style = ""
        self.style = style

    @property
    def cells(self) -> "List[Cell]":
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
            cell.row = cast("Row", self)
            cell.col = self.table._cols[index]
            self.table.sync_rows_to_cols()
        elif self.type_ == "col":
            cell.row = self.table._rows[index]
            cell.col = cast("Col", self)
            self.table.sync_cols_to_rows()

    @property
    def widths(self) -> "List[int]":
        """A list of the width of cell (excluding horizontal padding)."""
        return [cell.width for cell in self.cells]

    @property
    def max_width(self) -> "int":
        """The maximum cell width (excluding horizontal padding)."""
        if self.widths:
            return max(self.widths)
        else:
            return 0

    @property
    def total_widths(self) -> "List[int]":
        """A list of cell widths (including horizontal padding)."""
        return [cell.total_width for cell in self.cells]

    @property
    def max_total_width(self) -> "int":
        """The maximum cell width (including horizontal padding)."""
        if self.widths:
            return max(self.total_widths)
        else:
            return 0

    @property
    def align(self) -> "FormattedTextAlign":
        """The default alignment for cells in the row/column."""
        return self._align or self.table.align

    @align.setter
    def align(self, align: "FormattedTextAlign") -> "None":
        """Set the default alignment for cells in the row/column."""
        self._align = align

    @property
    def weighted_padding(self) -> "WeightedCellPadding":
        """The default padding for cells in the row/column with inheritance weights."""
        return WeightedCellPadding(
            *(
                WeightedInt(
                    1 if x is not None else 0,
                    x if x is not None else self.table.padding[i] or 0,
                )
                for i, x in enumerate(self._padding)
            )
        )

    @property
    def padding(self) -> "CellPadding":
        """The default padding for cells in the row/column."""
        return CellPadding(*(x.value for x in self.weighted_padding))

    @padding.setter
    def padding(self, padding: "Optional[Union[CellPadding, int]]") -> "None":
        """The default padding for cells in the row/column."""
        self._set_padding(padding)

    @property
    def weighted_border(self) -> "WeightedCellBorder":
        """The cell's borders with inheritance weights."""
        return WeightedCellBorder(
            *(
                WeightedLineStyle(
                    1 if x is not None else 0,
                    x if x is not None else self.table.border[i] or Thin,
                )
                for i, x in enumerate(self._border)
            )
        )

    @property
    def border(self) -> "CellBorder":
        """The default border style for cells in the row/column."""
        return CellBorder(*(x.value for x in self.weighted_border))

    @border.setter
    def border(self, border: "Optional[Union[LineStyle, CellBorder]]") -> "None":
        self._set_border(border)

    @property
    def style(self) -> "str":
        """Set the default style for cells' contents in the row or column."""
        return f"{self.table.style} {self._style}"

    @style.setter
    def style(self, style: "str") -> "None":
        """The default style for cells' contents in the row or column."""
        self._style = style

    def __repr__(self) -> "str":
        """Returns a textual representation of the row or column."""
        return f"{self.__class__.__name__}({', '.join(map(str, self._cells.values()))})"


class Row(RowCol):
    """A row in a table."""

    type_ = "row"


class Col(RowCol):
    """A column in a table."""

    type_ = "col"


class DummyCell(Cell):
    """A dummy cell with not content, padding or borders."""


class Table:
    """A table."""

    def _set_border(self, border: "Optional[Union[LineStyle, CellBorder]]") -> "None":
        """Set the default border style for cells in the table."""
        if border is None:
            border = Thin
        if isinstance(border, LineStyle):
            border = CellBorder(border, border, border, border)
        if len(border) == 2:
            border = CellBorder(border[0], border[1], border[0], border[1])
        # None is not a permitted value here - replace with default
        self._border = CellBorder(
            border[0] or Thin,
            border[1] or Thin,
            border[2] or Thin,
            border[3] or Thin,
        )

    def _set_padding(self, padding: "Optional[Union[CellPadding, int]]") -> "None":
        """Set the default padding for cells in the table."""
        if padding is None:
            padding = CellPadding(0, 1, 0, 1)
        if isinstance(padding, int):
            padding = CellPadding(padding, padding, padding, padding)
        if len(padding) == 2:
            padding = CellPadding(padding[0], padding[1], padding[0], padding[1])
        # `None` is not permitted for padding here, as there is nothing to inherit from
        self._padding = CellPadding(
            padding[0] or 0, padding[1] or 0, padding[2] or 0, padding[3] or 0
        )

    def __init__(
        self,
        rows: "Optional[Sequence[Row]]" = None,
        cols: "Optional[Sequence[Col]]" = None,
        width: "Optional[int]" = None,
        expand: "bool" = False,
        align: "FormattedTextAlign" = FormattedTextAlign.LEFT,
        padding: "Optional[CellPadding]" = None,
        border: "Optional[Union[CellBorder, LineStyle]]" = Thin,
        border_style: "str" = "",
        border_collapse: "bool" = False,
        style: "str" = "",
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
            padding: The default padding for cells in the table
            border: The default border style for cells in the table
            border_style: The style to apply to the table's borders
            border_collapse: If :const:`True`, if horizontal border in the table are
                :class:`Invisible` for their entire length, no extra line will be drawn
            style: A style to apply to the table's cells' contents

        """
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

        self.width = width or get_app_session().output.get_size()[1]
        self.align = align
        self.expand = expand

        self._set_padding(padding)
        self._set_border(border)
        self.border_style = border_style
        self.border_collapse = border_collapse
        self.style = style

    @property
    def border(self) -> "CellBorder":
        """The default border style for cells in the table."""
        return self._border

    @border.setter
    def border(self, border: "Optional[Union[LineStyle, CellBorder]]") -> "None":
        self._set_border(border)

    @property
    def padding(self) -> "CellPadding":
        """The default padding for cells in the table."""
        return self._padding

    @padding.setter
    def padding(self, padding: "Optional[Union[CellPadding, int]]") -> "None":
        self._set_padding(padding)

    @property
    def rows(self) -> "List[Row]":
        """A list of rows in the table."""
        return [self._rows[i] for i in range(len(self._rows))]

    @property
    def cols(self) -> "List[Col]":
        """A list of columns in the table."""
        return [self._cols[i] for i in range(len(self._cols))]

    def sync_rows_to_cols(self) -> "None":
        """Ensure cells in rows are present in the relevant columns."""
        for i, row in self._rows.items():
            for j, cell in row._cells.items():
                cell.col = self._cols[j]
                self._cols[j]._cells[i] = cell

    def sync_cols_to_rows(self) -> "None":
        """Ensure cells in columns are present in the relevant rows."""
        for i, col in self._cols.items():
            for j, cell in col._cells.items():
                cell.row = self._rows[j]
                self._rows[j]._cells[i] = cell

    def new_row(self, *args: "Any", **kwargs: "Any") -> "Row":
        """Creates a new row in the table."""
        row = Row(*args, **kwargs)
        self.add_row(row)
        return row

    def add_row(self, row: "Row") -> "None":
        """Add a row to the table."""
        row.table = self
        self._rows[max([-1] + list(self._rows)) + 1] = row

    def new_col(self, *args: "Any", **kwargs: "Any") -> "Col":
        """Creates a new column in the table."""
        col = Col(*args, **kwargs)
        self.add_col(col)
        return col

    def add_col(self, col: "Col") -> "None":
        """Add a column to the table."""
        col.table = self
        self._cols[max([-1] + list(self._cols)) + 1] = col

    def calculate_col_widths(self, width: "int") -> "List[int]":
        """Calculate column widths given the available space.

        Reduce the widest column until we fit in available width, or expand cells to
        to fill the available witdth.

        Args:
            width: The desired width of the table

        Returns:
            List of new column widths

        """
        col_widths = [col.max_total_width for col in self.cols]

        def total_width(col_widths: "List[int]") -> "int":
            return sum(col_widths) + len(self.cols) + 1

        if self.expand:
            while total_width(col_widths) < max(width, len(col_widths) * 7 + 2):
                idxmin = min(enumerate(col_widths), key=lambda x: x[1])[0]
                col_widths[idxmin] += 1
        else:
            while total_width(col_widths) > max(width, len(col_widths) * 7 + 2):
                idxmax = max(enumerate(col_widths), key=lambda x: x[1])[0]
                col_widths[idxmax] -= 1

        return col_widths

    @staticmethod
    def get_node(
        nw: "Cell",
        ne: "Cell",
        se: "Cell",
        sw: "Cell",
    ) -> "str":
        """Calculate which character to use at the intersection of four cells."""
        return grid_char(
            GridChar(
                max(nw.weighted_border.right, ne.weighted_border.left).value,
                max(ne.weighted_border.bottom, se.weighted_border.top).value,
                max(se.weighted_border.left, sw.weighted_border.right).value,
                max(sw.weighted_border.top, nw.weighted_border.bottom).value,
            )
        )

    @staticmethod
    def get_horizontal_edge(n: "Cell", s: "Cell") -> "str":
        """Calculate which character to use to divide horizontally adjacent cells."""
        line_style = max(n.weighted_border.bottom, s.weighted_border.top).value
        return grid_char(GridChar(Invisible, line_style, Invisible, line_style))

    @staticmethod
    def get_vertical_edge(e: "Cell", w: "Cell") -> "str":
        """Calculate which character to use to divide vertically adjacent cells."""
        line_style = max(e.weighted_border.right, w.weighted_border.left).value
        return grid_char(GridChar(line_style, Invisible, line_style, Invisible))

    def draw_border_row(
        self,
        row_above: "Optional[Row]",
        row_below: "Optional[Row]",
        col_widths: "List[int]",
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
        for i, ((nw, ne), (sw, se)) in enumerate(
            zip(
                pairwise(cells_above),
                pairwise(cells_below),
            )
        ):
            output += [(self.border_style, self.get_node(nw, ne, se, sw))]
            if i < len(col_widths):
                edge = self.get_horizontal_edge(ne, se)
                edges += edge
                output += [(self.border_style, edge * (col_widths[i]))]
        # Do not draw border row if border collapse is on and all parts are invisible
        if self.border_collapse and not edges.strip():
            return []
        output += [("", "\n")]
        return output

    def draw_table_row(
        self,
        row: "Optional[RowCol]",
        col_widths: "List[int]",
    ) -> "StyleAndTextTuples":
        """Draws a row in the table."""
        output: "StyleAndTextTuples" = []
        if row:
            # Calculate borders
            borders = []
            for e, w in zip([DummyCell(), *row.cells], [*row.cells, DummyCell()]):
                borders += [(self.border_style, self.get_vertical_edge(e, w))]

            # Draw row contents line by line
            row_lines = list(
                zip_longest(
                    *(
                        cell.lines(
                            width=col_width
                            - (cell.padding.left or 0)
                            - (cell.padding.right or 0)
                        )
                        for cell, col_width in zip(row.cells, col_widths)
                    )
                )
            )
            for row_line in row_lines:
                for i, (line, cell) in enumerate(zip(row_line, row.cells)):
                    output += [borders[i]]
                    if line is not None:
                        output += [
                            (cell.style, " " * (row.cells[i].padding.left or 0)),
                            *line,
                            (cell.style, " " * (row.cells[i].padding.right or 0)),
                        ]
                    else:
                        output += [(cell.style, " " * (col_widths[i]))]
                output += [borders[i + 1]]
                output += [("", "\n")]

        return output

    def render(self, width: "Optional[int]" = None) -> "StyleAndTextTuples":
        """Draws the table, optionally at a given character width."""
        width = width or self.width
        col_widths = self.calculate_col_widths(width)
        output = []

        for row_above, row_below in zip([None, *self.rows], [*self.rows, None]):
            output += self.draw_border_row(row_above, row_below, col_widths)
            output += self.draw_table_row(row_below, col_widths)
        output.pop()

        return output

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

    def __init__(self, *args: "Any", **kwargs: "Any"):
        """Create a new dummy table."""
        kwargs["border"] = Invisible
        super().__init__(*args, **kwargs)

    def add_row(self, row: "Row") -> "None":
        """Prevents rows being added to a dummy table."""
        raise NotImplementedError("Cannot add a row to a DummyTable")

    def add_col(self, col: "Col") -> "None":
        """Prevents columns being added to a dummy table."""
        raise NotImplementedError("Cannot add a column to a DummyTable")
