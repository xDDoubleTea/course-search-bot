"""Every adapter's output must pass this. Contributors run it to know they're done."""

import pytest
from schema import Course
from search import search
from tests.fixtures import FIXTURES


def conforms(courses: list[Course]) -> None:
    assert courses, "adapter returned no courses"
    for c in courses:
        assert isinstance(c, Course), f"not a Course: {type(c)}"
        assert c.id and c.school and c.semester
        assert c.name_zh or c.name_en, f"{c.id}: needs at least one name"
        assert isinstance(c.teachers, list)
        assert isinstance(c.times, list)
        assert c.credits >= 0
        if c.capacity is not None and c.enrolled is not None:
            assert c.enrolled >= 0 and c.capacity >= 0
    ids = [c.id for c in courses]
    assert len(ids) == len(set(ids)), "duplicate course ids"


def test_fixtures_conform():
    conforms(FIXTURES)


@pytest.mark.parametrize("query,expect_id", [
    ("微積分", "11510-CS132000"),
    ("thermo", "11510-EE203001"),
    ("吳貞興", "11510-CS132000"),
    ("A9", "1131-A901000"),
])
def test_search_finds(query, expect_id):
    hits = search(FIXTURES, query)
    assert expect_id in [c.id for c in hits], f"{query!r} missed {expect_id}"


def test_search_empty_query():
    assert search(FIXTURES, "   ") == []


def test_seats_left():
    assert FIXTURES[0].seats_left == 2
    assert FIXTURES[1].seats_left == 0


@pytest.mark.parametrize("query", ["微積分Ａ一", "微積分A一", "ｃａｌｃｕｌｕｓ", "CALCULUS"])
def test_fullwidth_folds_both_sides(query):
    """The data carries fullwidth Ａ too, so folding only the query would still miss."""
    from schema import Course
    course = Course(
        id="11510MATH101002", school="nthu", semester="11510",
        name_zh="微積分Ａ一", name_en="Calculus A(I)", teachers=["李華倫"],
        department="MATH", credits=4.0, times=["T1"], venues=["DELTA台達109"],
    )
    assert search([course], query), f"{query!r} found nothing"


def test_tolerates_one_typo():
    assert search(FIXTURES, "thermodinamics")


def test_prebuilt_index_matches_inline():
    from search import build_index
    idx = build_index(FIXTURES)
    assert search(FIXTURES, "微積分", index=idx) == search(FIXTURES, "微積分")
