"""Course is a value object: frozen, comparable, and honest about missing data."""

import dataclasses

import pytest

from schema import Course


def test_course_is_frozen(course):
    with pytest.raises(dataclasses.FrozenInstanceError):
        course.name_zh = "something else"


def test_to_dict_round_trips(course):
    assert Course(**course.to_dict()) == course


@pytest.mark.parametrize(
    "capacity,enrolled,expected",
    [
        (116, 58, 58),
        (55, 55, 0),
        (None, 58, None),
        (116, None, None),
        (None, None, None),
    ],
    ids=["has room", "full", "no capacity", "no enrolled", "neither"],
)
def test_seats_left(course, capacity, enrolled, expected):
    """Unknown on either side means unknown overall, never a misleading zero."""
    c = dataclasses.replace(course, capacity=capacity, enrolled=enrolled)
    assert c.seats_left == expected
