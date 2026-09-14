"""NCKU adapter, reading NCKU HUB. Parsing runs against a frozen sample."""

import httpx
import pytest

from adapters.ncku import (
    NckuAdapter,
    next_semester,
    parse_teachers,
    parse_time,
)
from conformance import conforms
from search import search


class TestParseTime:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("[5]3~4", ["F3", "F4"]),
            ("[2]2 [5]3~4 ", ["T2", "F3", "F4"]),
            ("[1]N [2]N [5]N ", ["MN", "TN", "FN"]),
            ("[6]A~C", ["SA", "SB", "SC"]),
            ("[4]9~A", ["R9", "RA"]),
            ("", []),
            ("[1] ", []),
        ],
        ids=[
            "range",
            "two days",
            "noon",
            "letters",
            "digit to letter",
            "empty",
            "day without periods",
        ],
    )
    def test_expands_days_and_periods(self, raw, expected):
        assert parse_time(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("[3]3~N", ["W3", "W4", "WN"]),
            ("[4]N~6", ["RN", "R5", "R6"]),
            ("[2]4~5", ["T4", "TN", "T5"]),
        ],
    )
    def test_noon_sits_between_four_and_five(self, raw, expected):
        """The data carries 3~N, 4~N, N~5 and N~6, so N is ordered, not a flag."""
        assert parse_time(raw) == expected

    def test_ignores_the_flex_time_widget(self):
        """Some rows have raw HTML appended inside the 時間 field."""
        raw = "[5]5~7<div class='flex_time'><i class='fas fa-bell'></i>上課時間</div>"
        assert parse_time(raw) == ["F5", "F6", "F7"]

    def test_weekdays_use_the_same_letters_as_other_schools(self):
        """NCKU numbers its days; the schema speaks in letters."""
        assert parse_time("[1]1 [7]1") == ["M1", "U1"]


class TestParseTeachers:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("林君昱", ["林君昱"]),
            ("麥愛堂*,李亞夫,邱慈暉", ["麥愛堂", "李亞夫", "邱慈暉"]),
            ("", []),
            ("  ", []),
        ],
        ids=["one", "coordinator starred", "empty", "blank"],
    )
    def test_splits_and_drops_the_coordinator_marker(self, raw, expected):
        assert parse_teachers(raw) == expected


class TestNextSemester:
    @pytest.mark.parametrize(
        "current,following",
        [("114-1", "114-2"), ("114-2", "115-1"), ("99-2", "100-1")],
    )
    def test_rolls_over_the_academic_year(self, current, following):
        assert next_semester(current) == following


class TestFieldMapping:
    def test_id_carries_the_semester(self, ncku):
        assert all(c.id.startswith("115-1_") for c in ncku.courses("115-1"))

    def test_ids_are_unique(self, ncku):
        ids = [c.id for c in ncku.courses("115-1")]
        assert len(ids) == len(set(ids))

    def test_seats_are_never_reported(self, ncku):
        """Seat counts live on the per-course endpoint and carry mixed ages."""
        assert all(
            c.capacity is None and c.enrolled is None for c in ncku.courses("115-1")
        )

    def test_course_without_teacher_is_kept(self, ncku):
        assert any(c.teachers == [] for c in ncku.courses("115-1"))

    def test_zero_credit_course_is_kept(self, ncku):
        assert any(c.credits == 0 for c in ncku.courses("115-1"))


class TestContract:
    def test_sample_conforms(self, ncku):
        conforms(ncku.courses("115-1"))

    def test_sample_is_searchable(self, ncku):
        assert search(ncku.courses("115-1"), "工程數學")


@pytest.fixture(scope="module")
def live() -> NckuAdapter:
    adapter = NckuAdapter()
    try:
        adapter.current_semester()
    except httpx.HTTPError as exc:
        pytest.skip(f"NCKU HUB unreachable: {exc}")
    yield adapter
    adapter.close()


@pytest.mark.integration
class TestLiveSource:
    def test_current_term_is_ahead_of_the_archive(self, live):
        semesters = live.semesters()
        assert semesters[0] == next_semester(semesters[1])

    def test_whole_term_conforms(self, live):
        courses = live.courses(live.current_semester())
        assert len(courses) > 3000, f"only {len(courses)} courses"
        conforms(courses)

    def test_every_scheduled_course_yields_slots(self, live):
        """A drop here means the 時間 grammar gained a token we do not expand."""
        courses = live.courses(live.current_semester())
        scheduled = [c for c in courses if c.times]
        assert len(scheduled) / len(courses) > 0.80
