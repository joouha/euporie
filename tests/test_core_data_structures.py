"""Data structure unit tests."""

from __future__ import annotations

from typing import cast

from euporie.apptk.data_structures import (
    DiBool,
    DiInt,
    DiStr,
    WeightedDiInt,
    WeightedInt,
)


def test_DiBool() -> None:
    """Test the DiBool data structure."""
    d = DiBool(top=True, right=True, bottom=False, left=False)
    assert d.top is True
    assert d.right is True
    assert d.bottom is False
    assert d.left is False

    d2 = DiBool.from_value(True)
    assert d2.top is True
    assert d2.right is True
    assert d2.bottom is True
    assert d2.left is True


def test_DiInt() -> None:
    """Test the DiInt data structure."""
    d = DiInt(top=1, right=2, bottom=3, left=4)
    assert d.top == 1
    assert d.right == 2
    assert d.bottom == 3
    assert d.left == 4

    d2 = DiInt.from_value(5)
    assert d2.top == 5
    assert d2.right == 5
    assert d2.bottom == 5
    assert d2.left == 5


def test_DiStr() -> None:
    """Test the DiStr data structure."""
    d = DiStr(top="a", right="b", bottom="c", left="d")
    assert d.top == "a"
    assert d.right == "b"
    assert d.bottom == "c"
    assert d.left == "d"

    d2 = DiStr.from_value("e")
    assert d2.top == "e"
    assert d2.right == "e"
    assert d2.bottom == "e"
    assert d2.left == "e"


def test_WeightedInt() -> None:
    """Test the WeightedInt data structure."""
    w = WeightedInt(weight=2, value=3)
    assert w.weight == 2
    assert w.value == 3


def test_WeightedDiInt() -> None:
    """Test the WeightedDiInt data structure."""
    d = WeightedDiInt(
        top=WeightedInt(weight=2, value=3),
        right=WeightedInt(weight=3, value=4),
        bottom=WeightedInt(weight=4, value=5),
        left=WeightedInt(weight=5, value=6),
    )
    assert d.top.weight == 2
    assert d.right.value == 4
    assert d.bottom.weight == 4
    assert d.left.value == 6

    assert cast("DiInt", d.unweighted).top == 3
    assert cast("DiInt", d.unweighted).right == 4
    assert cast("DiInt", d.unweighted).bottom == 5
    assert cast("DiInt", d.unweighted).left == 6
