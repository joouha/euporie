"""Test layout container functionality."""

from euporie.apptk.layout.containers import DimensionTuple, distribute_dimensions


def test_distribute_dimensions_empty() -> None:
    """Test distributing dimensions with empty input."""
    assert distribute_dimensions(10, ()) == []


def test_distribute_dimensions_insufficient_space() -> None:
    """Test when there isn't enough space for minimum dimensions."""
    dims = (
        DimensionTuple(min=5, max=10, preferred=7),
        DimensionTuple(min=6, max=12, preferred=8),
    )
    assert distribute_dimensions(10, dims) is None


def test_distribute_dimensions_exact_min_space() -> None:
    """Test when space exactly matches minimum requirements."""
    dims = (
        DimensionTuple(min=3, max=10, preferred=5),
        DimensionTuple(min=4, max=12, preferred=6),
    )
    assert distribute_dimensions(7, dims) == [3, 4]


def test_distribute_dimensions_preferred() -> None:
    """Test distribution up to preferred sizes."""
    dims = (
        DimensionTuple(min=2, max=10, preferred=5),
        DimensionTuple(min=3, max=12, preferred=6),
    )
    assert distribute_dimensions(11, dims) == [5, 6]


def test_distribute_dimensions_weights() -> None:
    """Test distribution considering weights."""
    dims = (
        DimensionTuple(min=2, max=10, preferred=4, weight=1),
        DimensionTuple(min=2, max=10, preferred=4, weight=2),
    )
    # Extra space is distributed proportionally according to weights
    assert distribute_dimensions(12, dims) == [5, 7]


def test_distribute_dimensions_max_limit() -> None:
    """Test distribution respecting maximum limits."""
    dims = (
        DimensionTuple(min=2, max=5, preferred=4),
        DimensionTuple(min=2, max=6, preferred=4),
    )
    # Even with more space available, should not exceed max values
    assert distribute_dimensions(15, dims) == [5, 6]


def test_distribute_dimensions_with_fixed_and_flexible() -> None:
    """Test distribution with one fixed size and two flexible dimensions."""
    dims = (
        # Fixed size dimension
        DimensionTuple(min=5, max=5, preferred=5),
        # Two flexible dimensions with no constraints
        DimensionTuple(min=0, max=999, preferred=0),
        DimensionTuple(min=0, max=999, preferred=0),
    )
    # Total space is 15, with 5 taken by fixed dimension,
    # remaining 10 should be split evenly between the two flexible dimensions
    assert distribute_dimensions(15, dims) == [5, 5, 5]


def test_distribute_dimensions_uneven_distribution() -> None:
    """Test distribution with uneven dimension requirements."""
    dims = (
        DimensionTuple(min=1, max=3, preferred=2),
        DimensionTuple(min=2, max=8, preferred=4),
        DimensionTuple(min=1, max=4, preferred=3),
    )
    assert distribute_dimensions(9, dims) == [2, 4, 3]


def test_distribute_dimensions_custom_distribution() -> None:
    """Test distribution with uneven dimension requirements."""
    dims = (
        DimensionTuple(min=0, max=9999, preferred=0),
        DimensionTuple(min=0, max=1, preferred=0),
        DimensionTuple(min=0, max=1, preferred=0),
        DimensionTuple(min=1, max=20, preferred=20),
        DimensionTuple(min=0, max=1, preferred=0),
        DimensionTuple(min=0, max=1, preferred=0),
        DimensionTuple(min=0, max=9999, preferred=0),
    )
    assert distribute_dimensions(30, dims) == [3, 1, 1, 20, 1, 1, 3]
