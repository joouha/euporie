"""Test module for euporie.core.utils."""

from __future__ import annotations

from euporie.apptk.data_structures import Point
from euporie.apptk.mouse_events import MouseButton, MouseEvent, MouseEventType
from euporie.core.utils import ChainedList, dict_merge, on_click


def test_ChainedList() -> None:
    """Test ChainedList."""
    cl = ChainedList([1, 2, 3], [4, 5, 6])
    assert len(cl) == 6
    assert cl[3] == 4
    assert cl[1:4] == [2, 3, 4]


def test_dict_merge() -> None:
    """Test dict_merge."""
    target_dict = {"a": 1, "b": {"c": 2, "d": 3}, "e": [1, 2]}
    input_dict = {"b": {"c": 4}, "e": [3, 4], "f": 5}

    dict_merge(target_dict, input_dict)
    assert target_dict == {"a": 1, "b": {"c": 4, "d": 3}, "e": [1, 2, 3, 4], "f": 5}


def test_on_click() -> None:
    """Test on_click."""
    result = ""

    def click_handler() -> None:
        nonlocal result
        result = "Clicked!"

    handler = on_click(click_handler)

    # Test when button is not left
    assert (
        handler(
            MouseEvent(
                position=Point(0, 0),
                button=MouseButton.RIGHT,
                event_type=MouseEventType.MOUSE_UP,
                modifiers=frozenset(),
            )
        )
        is NotImplemented
    )
    assert result == ""

    # Test when button is left but not mouse up
    assert (
        handler(
            MouseEvent(
                position=Point(0, 0),
                button=MouseButton.LEFT,
                event_type=MouseEventType.MOUSE_DOWN,
                modifiers=frozenset(),
            )
        )
        is NotImplemented
    )
    assert result == ""

    # Test when we have actual click
    assert (
        handler(
            MouseEvent(
                position=Point(0, 0),
                button=MouseButton.LEFT,
                event_type=MouseEventType.MOUSE_UP,
                modifiers=frozenset(),
            )
        )
        is None
    )
    assert result == "Clicked!"
