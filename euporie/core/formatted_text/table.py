"""Allows drawing tables as :class:`FormattedText`."""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache, partial
from itertools import tee, zip_longest
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import (
    fragment_list_width,
    split_lines,
    to_plain_text,
)

from euporie.core.border import (
    BorderLineStyle,
    GridChar,
    Invisible,
    LineStyle,
    Padding,
    Thin,
    WeightedBorderLineStyle,
    WeightedInt,
    WeightedLineStyle,
    WeightedPadding,
    grid_char,
)
from euporie.core.formatted_text.utils import (
    FormattedTextAlign,
    align,
    max_line_width,
    wrap,
)

if TYPE_CHECKING:
    from typing import (
        Any,
        Hashable,
        Iterable,
        Iterator,
        Optional,
        Sequence,
        TypeVar,
        Union,
    )

    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        FormattedText,
        StyleAndTextTuples,
    )

    PairT = TypeVar("PairT")


def pairwise(iterable: "Iterable[PairT]") -> "Iterator[tuple[PairT, PairT]]":
    """Returns successiver overlapping pairs from an iterable."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


class Cell:
    """A table cell."""

    def _set_padding(self, padding: "Optional[Union[Padding, int]]") -> "None":
        """Sets the cell's padding."""
        if padding is None:
            padding = Padding(None, None, None, None)
        if isinstance(padding, int):
            padding = Padding(padding, padding, padding, padding)
        if len(padding) == 2:
            padding = Padding(padding[0], padding[1], padding[0], padding[1])
        self._padding = padding or Padding(None, None, None, None)

    def _set_border(
        self, border: "Optional[Union[LineStyle, BorderLineStyle]]"
    ) -> "None":
        """Sets the cell's border."""
        if border is None:
            _border = BorderLineStyle(None, None, None, None)
        elif isinstance(border, LineStyle):
            _border = BorderLineStyle(border, border, border, border)
        elif isinstance(border, tuple) and len(border) == 2:
            _border = BorderLineStyle(border[0], border[1], border[0], border[1])
        else:
            _border = border
        self._border = _border

    def __init__(
        self,
        text: "AnyFormattedText" = "",
        row: "Optional[Row]" = None,
        col: "Optional[Col]" = None,
        colspan: "int" = 1,
        rowspan: "int" = 1,
        align: "Optional[FormattedTextAlign]" = None,
        padding: "Optional[Union[Padding, int]]" = None,
        border: "Optional[Union[LineStyle, BorderLineStyle]]" = None,
        style: "str" = "",
        width: "Optional[int]" = None,
    ):
        """Creates a new table cell.

        Args:
            text: Text or formatted text to display in the cell
            row: The row to which this cell belongs
            col: The column to which this cell belongs
            colspan: The number of columns this cell spans
            rowspan: The number of row this cell spans
            align: How the text in the cell should be aligned
            padding: The padding around the contents of the cell
            border: The type of border line to apply to the cell
            style: The style to apply to the cell's contents
            width: The desired width of the cell

        """
        self._text = text
        self.row = row or DummyRow()
        self.col = col or DummyCol()
        self.colspan = colspan
        self.rowspan = rowspan
        self._align = align
        self._set_padding(padding)
        self._set_border(border)
        self._style = ""
        self.style = style
        self._width = width

        self._weighted_border_cache: "SimpleCache[Hashable, WeightedBorderLineStyle]" = (
            SimpleCache()
        )
        self._weighted_padding_cache: "SimpleCache[Hashable, WeightedPadding]" = (
            SimpleCache()
        )

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
        padding = self.padding
        return split_lines(
            align(
                self.align,
                wrap(
                    [
                        ("", "\n" * (padding.top or 0)),
                        *self.text,
                        ("", "\n" * (padding.bottom or 0)),
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
        if self.colspan > 1:
            return 0
        return self._width or max_line_width(self.text)  # // self.rowspan

    @width.setter
    def width(self, value: "Optional[int]") -> "None":
        """Set the width of the cell."""
        self._width = value

    @property
    def total_width(self) -> "int":
        """The width of the cell including padding."""
        if self.colspan > 1:
            return 0
        padding = self.padding
        return self.width + (padding.left or 0) + (padding.right or 0)

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
    def weighted_padding(self) -> "WeightedPadding":
        """The cell's padding with inheritance weights."""

        def _get_weighted_padding() -> "WeightedPadding":
            weights = []
            for i, x in enumerate(self._padding):
                if x is None:
                    weights.append(
                        WeightedInt(
                            max(
                                self.row.weighted_padding[i],
                                self.col.weighted_padding[i],
                            ).weight,
                            max(
                                self.row.weighted_padding[i],
                                self.col.weighted_padding[i],
                            ).value,
                        )
                    )
                else:
                    weights.append(WeightedInt(2, x))
            return WeightedPadding(*weights)

        return self._weighted_padding_cache.get(
            (
                self._padding,
                self.row.weighted_padding,
                self.col.weighted_padding,
            ),
            _get_weighted_padding,
        )

    @property
    def padding(self) -> "Padding":
        """The cell's padding."""
        return cast("Padding", self.weighted_padding.padding)

    @padding.setter
    def padding(self, padding: "Optional[Union[Padding, int]]") -> "None":
        """Sets the cell's padding."""
        self._set_padding(padding)

    @property
    def weighted_border(self) -> "WeightedBorderLineStyle":
        """The cell's borders with inheritance weights."""

        def _get_weighted_border() -> "WeightedBorderLineStyle":
            values = []
            for i, x in enumerate(self._border):
                if i == 1 and self.colspan > 1:
                    # Set right edge to invisible
                    values.append(WeightedLineStyle(3, Invisible))
                elif i == 2 and self.rowspan > 1:
                    # Set bottom edge to invisible
                    values.append(WeightedLineStyle(3, Invisible))
                elif x:
                    values.append(WeightedLineStyle(2, x))
                else:
                    values.append(
                        WeightedLineStyle(
                            max(
                                self.row.weighted_border[i], self.col.weighted_border[i]
                            ).weight,
                            max(
                                self.row.weighted_border[i], self.col.weighted_border[i]
                            ).value,
                        )
                    )
            return WeightedBorderLineStyle(*values)

        return self._weighted_border_cache.get(
            (
                self._border,
                self.row.weighted_border,
                self.col.weighted_border,
                self.colspan,
                self.rowspan,
            ),
            _get_weighted_border,
        )

    @property
    def border(self) -> "BorderLineStyle":
        """The cell's border."""
        return cast("BorderLineStyle", self.weighted_border.border_line_style)

    @border.setter
    def border(self, border: "Optional[Union[LineStyle, BorderLineStyle]]") -> "None":
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
            cell_text = cell_text[:4] + "…"
        return f'Cell("{cell_text}")'


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
        align: "Optional[FormattedTextAlign]" = None,
        padding: "Optional[Union[Padding, int]]" = None,
        border: "Optional[Union[LineStyle, BorderLineStyle]]" = None,
        style: "str" = "",
        width: "Optional[int]" = None,
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
            align: How the text in the cell should be aligned
            padding: The padding around the contents of the cell
            border: The type of border line to apply to the cell
            style: The style to apply to the cell's contents
            width: The desired width of the cell

        """
        self.expands = expands
        self.span_index = span_index
        super().__init__(
            text="",
            row=row,
            col=col,
            colspan=1,
            rowspan=1,
            align=align,
            padding=0,
            border=expands._border,
            style=expands.style,
            width=0,
        )

    @property
    def weighted_border(self) -> "WeightedBorderLineStyle":
        """The cell's borders with inheritance weights."""
        values = [
            WeightedLineStyle(
                2
                if x
                else max(
                    self.expands.row.weighted_border[i],
                    self.expands.col.weighted_border[i],
                ).weight,
                x
                or max(
                    self.expands.row.weighted_border[i],
                    self.expands.col.weighted_border[i],
                ).value,
            )
            for i, x in enumerate(self.expands._border)
        ]
        if self.expands.colspan > 1:
            # Set left border to invisible in colspan
            values[3] = WeightedLineStyle(3, Invisible)
        if self.expands.rowspan > 1:
            # Set top border to invisible in rowspan
            values[0] = WeightedLineStyle(3, Invisible)
        return WeightedBorderLineStyle(*values)


class RowCol:
    """Base class for table rows and columns."""

    type_: "str"
    span_type: "str"

    def _set_padding(self, padding: "Optional[Union[Padding, int]]") -> "None":
        """The default padding for cells in the row/column."""
        if padding is None:
            padding = Padding(None, None, None, None)
        if isinstance(padding, int):
            padding = Padding(padding, padding, padding, padding)
        if len(padding) == 2:
            padding = Padding(padding[0], padding[1], padding[0], padding[1])
        self._padding = padding

    def _set_border(
        self, border: "Optional[Union[LineStyle, BorderLineStyle]]"
    ) -> "None":
        """Set the default border style for cells in the row/column."""
        if border is None:
            _border = BorderLineStyle(None, None, None, None)
        elif isinstance(border, LineStyle):
            _border = BorderLineStyle(border, border, border, border)
        elif isinstance(border, tuple) and len(border) == 2:
            _border = BorderLineStyle(border[0], border[1], border[0], border[1])
        else:
            _border = border
        self._border = _border

    def __init__(
        self,
        table: "Optional[Table]" = None,
        cells: "Optional[Sequence[Cell]]" = None,
        align: "Optional[FormattedTextAlign]" = None,
        padding: "Optional[Union[Padding, int]]" = None,
        border: "Optional[Union[LineStyle, BorderLineStyle]]" = None,
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

        self._weighted_border_cache: "SimpleCache[Hashable, WeightedBorderLineStyle]" = (
            SimpleCache()
        )
        self._weighted_padding_cache: "SimpleCache[Hashable, WeightedPadding]" = (
            SimpleCache()
        )

    @property
    def cells(self) -> "list[Cell]":
        """Lists the cells in the row/column."""
        # return [self._cells[i] for i in range(len(self._cells))]
        cells = []
        for i in range(len(self._cells)):
            cell = self._cells[i]
            cells.append(cell)
        return cells

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

    @property
    def widths(self) -> "list[int]":
        """A list of the widths of cell (excluding horizontal padding)."""
        return [cell.width for cell in self.cells]

    @property
    def max_width(self) -> "int":
        """The maximum cell width (excluding horizontal padding)."""
        if self.widths:
            return max(self.widths)
        else:
            return 0

    @property
    def total_widths(self) -> "list[int]":
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
    def weighted_padding(self) -> "WeightedPadding":
        """The default padding for cells in the row/column with inheritance weights."""

        def _get_weighted_padding() -> "WeightedPadding":
            return WeightedPadding(
                *(
                    WeightedInt(
                        1 if x is not None else 0,
                        x if x is not None else self.table.padding[i] or 0,
                    )
                    for i, x in enumerate(self._padding)
                )
            )

        return self._weighted_padding_cache.get(
            (self._padding, self.table.padding), _get_weighted_padding
        )

    @property
    def padding(self) -> "Padding":
        """The default padding for cells in the row/column."""
        return cast("Padding", self.weighted_padding.padding)

    @padding.setter
    def padding(self, padding: "Optional[Union[Padding, int]]") -> "None":
        """The default padding for cells in the row/column."""
        self._set_padding(padding)

    @property
    def weighted_border(self) -> "WeightedBorderLineStyle":
        """The cell's borders with inheritance weights."""

        def _get_weighted_border() -> "WeightedBorderLineStyle":
            return WeightedBorderLineStyle(
                *(
                    WeightedLineStyle(
                        1 if x is not None else 0,
                        x if x is not None else self.table.border[i] or Thin,
                    )
                    for i, x in enumerate(self._border)
                )
            )

        return self._weighted_border_cache.get(
            (self._border, self.table.border), _get_weighted_border
        )

    @property
    def border(self) -> "BorderLineStyle":
        """The default border style for cells in the row/column."""
        return cast("BorderLineStyle", self.weighted_border.border_line_style)

    @border.setter
    def border(self, border: "Optional[Union[LineStyle, BorderLineStyle]]") -> "None":
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
    span_type = "colspan"


class Col(RowCol):
    """A column in a table."""

    type_ = "col"
    span_type = "rowspan"


class DummyCell(Cell):
    """A dummy cell with not content, padding or borders."""

    def __repr__(self) -> "str":
        return f"{self.__class__.__name__}()"


class Table:
    """A table."""

    def _set_border(
        self, border: "Optional[Union[LineStyle, BorderLineStyle]]"
    ) -> "None":
        """Set the default border style for cells in the table."""
        if border is None:
            border = Thin
        if isinstance(border, LineStyle):
            border = BorderLineStyle(border, border, border, border)
        if len(border) == 2:
            border = BorderLineStyle(border[0], border[1], border[0], border[1])
        # None is not a permitted value here - replace with default
        self._border = BorderLineStyle(
            border[0] or Thin,
            border[1] or Thin,
            border[2] or Thin,
            border[3] or Thin,
        )

    def _set_padding(self, padding: "Optional[Union[Padding, int]]") -> "None":
        """Set the default padding for cells in the table."""
        if padding is None:
            padding = Padding(0, 1, 0, 1)
        if isinstance(padding, int):
            padding = Padding(padding, padding, padding, padding)
        if len(padding) == 2:
            padding = Padding(padding[0], padding[1], padding[0], padding[1])
        # `None` is not permitted for padding here, as there is nothing to inherit from
        self._padding = Padding(
            padding[0] or 0, padding[1] or 0, padding[2] or 0, padding[3] or 0
        )

    def __init__(
        self,
        rows: "Optional[Sequence[Row]]" = None,
        cols: "Optional[Sequence[Col]]" = None,
        width: "Optional[int]" = None,
        expand: "bool" = False,
        align: "FormattedTextAlign" = FormattedTextAlign.LEFT,
        padding: "Optional[Union[Padding, int]]" = None,
        border: "Optional[Union[BorderLineStyle, LineStyle]]" = Thin,
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
        self.border_style = f"class:border {border_style}"
        self._border_collapse = border_collapse
        self.style = style

        self._border_collapse_cache: "SimpleCache[Hashable, bool]" = SimpleCache()

    @property
    def border_collapse(self) -> "bool":
        """Turn off border-collapse if any cells have a border."""

        def _get_border_collapse() -> "bool":
            for row in self._rows.values():
                for cell in row._cells.values():
                    if any(x != Invisible for x in cell.border):
                        return False
            return self._border_collapse

        return self._border_collapse_cache.get(tuple(self.rows), _get_border_collapse)

    @property
    def border(self) -> "BorderLineStyle":
        """The default border style for cells in the table."""
        return self._border

    @border.setter
    def border(self, border: "Optional[Union[LineStyle, BorderLineStyle]]") -> "None":
        self._set_border(border)

    @property
    def padding(self) -> "Padding":
        """The default padding for cells in the table."""
        return self._padding

    @padding.setter
    def padding(self, padding: "Optional[Union[Padding, int]]") -> "None":
        self._set_padding(padding)

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
        self, width: "int", min_col_width: "int" = 10
    ) -> "list[int]":
        """Calculate column widths given the available space.

        Reduce the widest column until we fit in available width, or expand cells to
        to fill the available witdth.

        Args:
            width: The desired width of the table
            min_col_width: The minimum width allowed for a column

        Returns:
            List of new column widths

        """
        # TODO - this function is too slow
        col_widths = [col.max_total_width for col in self.cols]

        def total_width(col_widths: "list[int]") -> "int":
            return sum(col_widths) + len(self.cols) + 1

        if self.expand:
            while total_width(col_widths) < max(
                width, len(col_widths) * min_col_width + 2
            ):
                idxmin = min(enumerate(col_widths), key=lambda x: x[1])[0]
                col_widths[idxmin] += 1
        else:
            while total_width(col_widths) > max(
                width, len(col_widths) * min_col_width + 2
            ):
                idxmax = max(enumerate(col_widths), key=lambda x: x[1])[0]
                col_widths[idxmax] -= 1

        return col_widths

    @staticmethod
    @lru_cache
    def get_node(
        nw_wb: "WeightedBorderLineStyle",
        ne_wb: "WeightedBorderLineStyle",
        se_wb: "WeightedBorderLineStyle",
        sw_wb: "WeightedBorderLineStyle",
    ) -> "str":
        """Calculate which character to use at the intersection of four cells."""
        return grid_char(
            GridChar(
                max(nw_wb.right, ne_wb.left).value,
                max(ne_wb.bottom, se_wb.top).value,
                max(se_wb.left, sw_wb.right).value,
                max(sw_wb.top, nw_wb.bottom).value,
            )
        )

    @staticmethod
    @lru_cache
    def get_horizontal_edge(
        n_wb: "WeightedBorderLineStyle", s_wb: "WeightedBorderLineStyle"
    ) -> "str":
        """Calculate which character to use to divide horizontally adjacent cells."""
        line_style = max(n_wb.bottom, s_wb.top).value
        return grid_char(GridChar(Invisible, line_style, Invisible, line_style))

    @staticmethod
    @lru_cache
    def get_vertical_edge(
        e_wb: "WeightedBorderLineStyle", w_wb: "WeightedBorderLineStyle"
    ) -> "str":
        """Calculate which character to use to divide vertically adjacent cells."""
        line_style = max(e_wb.right, w_wb.left).value
        return grid_char(GridChar(line_style, Invisible, line_style, Invisible))

    def draw_border_row(
        self,
        row_above: "Optional[Row]",
        row_below: "Optional[Row]",
        col_widths: "list[int]",
        border_collapse: "bool",
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
            output += [
                (
                    self.border_style,
                    self.get_node(
                        nw.weighted_border,
                        ne_wb := ne.weighted_border,
                        se_wb := se.weighted_border,
                        sw.weighted_border,
                    ),
                )
            ]
            if i < len(col_widths):
                edge = self.get_horizontal_edge(ne_wb, se_wb)
                edges += edge
                style = self.border_style
                # Use cell style for borders in colspans
                if isinstance(se, SpacerCell) and se.expands.rowspan > 1:
                    style = se.expands.style
                output += [(style, edge * (col_widths[i]))]
        # Do not draw border row if border collapse is on and all parts are invisible
        if border_collapse and not edges.strip():
            return []
        output += [("", "\n")]
        return output

    def draw_table_row(
        self,
        row: "Optional[RowCol]",
        col_widths: "list[int]",
        border_collapse: "bool",
    ) -> "StyleAndTextTuples":
        """Draws a row in the table."""
        output: "StyleAndTextTuples" = []
        if row:
            # Calculate borders
            borders = []
            for e, w in zip([DummyCell(), *row.cells], [*row.cells, DummyCell()]):
                borders += [
                    (
                        self.border_style,
                        self.get_vertical_edge(e.weighted_border, w.weighted_border),
                    )
                ]
            if self.border_collapse and not "".join([x[1] for x in borders]).strip():
                borders = [("", "")] * len(borders)

            def _calc_cell_width(
                cell: "Cell", col: "int", col_widths: "list[int]"
            ) -> "int":
                """Calculate a cell's width."""
                if isinstance(cell, SpacerCell) and cell.expands.colspan > 1:
                    return 0
                width = col_widths[col]
                # Remove padding
                padding = cell.padding
                width -= (padding.left or 0) + (padding.right or 0)

                # Expand if colspan
                for i in range(col + 1, col + cell.colspan):
                    width += col_widths[i]
                    if not border_collapse:
                        if borders[col]:
                            width += 1

                return width

            # Draw row contents line by line
            row_lines = zip_longest(
                *(
                    cell.lines(width=_calc_cell_width(cell, col, col_widths))
                    for col, cell in enumerate(row.cells)
                )
            )

            for row_line in row_lines:
                for i, (line, cell) in enumerate(zip(row_line, row.cells)):
                    # Skip spacer cells
                    if isinstance(cell, SpacerCell) and cell.expands.colspan > 1:
                        continue
                    output += [borders[i]]
                    if line is not None:
                        padding_style = f"{cell.style} nounderline"
                        padding = cell.padding
                        output += [
                            (padding_style, " " * (padding.left or 0)),
                            *line,
                            (padding_style, " " * (padding.right or 0)),
                        ]
                    # Ensure last line of a cell is fill with spaces
                    else:
                        width = sum(col_widths[i : i + cell.colspan])
                        if line:
                            width -= fragment_list_width(line)
                        output.append((cell.style, " " * width))

                output += [borders[i + 1]]
                output += [("", "\n")]

        return output

    def render(self, width: "Optional[int]" = None) -> "StyleAndTextTuples":
        """Draws the table, optionally at a given character width."""
        width = width or self.width
        col_widths = self.calculate_col_widths(width)
        output = []

        if self.rows:
            border_collapse = self.border_collapse
            for row_above, row_below in zip([None, *self.rows], [*self.rows, None]):
                output += self.draw_border_row(
                    row_above, row_below, col_widths, border_collapse
                )
                output += self.draw_table_row(row_below, col_widths, border_collapse)
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
