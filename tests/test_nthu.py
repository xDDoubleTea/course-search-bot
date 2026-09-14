"""NTHU adapter. Parsing is checked against a frozen sample of the real feed;
only the test marked `integration` touches the network.
"""

import httpx
import pytest

from adapters.nthu import NthuAdapter, _rows
from conformance import conforms
from search import search


class TestRowUnpacking:
    @pytest.mark.parametrize(
        "packed,expected",
        [
            ("台達106\tF5F6\n", [["台達106", "F5F6"]]),
            (
                "醫環618\tM3M4\n醫環501\tF3F4\n",
                [["醫環618", "M3M4"], ["醫環501", "F3F4"]],
            ),
            ("", []),
            ("\n\n", []),
        ],
        ids=["one row", "two rows", "empty", "blank lines only"],
    )
    def test_splits_on_tabs_and_newlines(self, packed, expected):
        assert _rows(packed) == expected


class TestFieldMapping:
    """Each case is a quirk observed in the live feed."""

    def test_unescapes_html_entities(self, nthu):
        """The JSON carries raw entities: 鄭兆&#29641; must become 鄭兆珉."""
        courses = nthu.courses("11510")
        assert not any("&#" in t for c in courses for t in c.teachers)

    def test_splits_multiple_teachers(self, nthu):
        c = self._by_id(nthu, "11510BME 100100")
        assert len(c.teachers) >= 4
        assert all(t and "\t" not in t for t in c.teachers)

    def test_collects_both_venues(self, nthu):
        c = self._by_id(nthu, "11510AES 520300")
        assert len(c.venues) == 2

    def test_parses_period_d(self, nthu):
        """Periods run 1-9 then n a b c d; 'd' is rare and easy to drop."""
        c = self._by_id(nthu, "11510KECN601100")
        assert "d" in {slot[1] for slot in c.times}

    def test_four_character_department(self, nthu):
        """科號 position 8 is not always a space — AIIM fills all four columns."""
        assert self._by_id(nthu, "11510AIIM600000").department == "AIIM"

    def test_missing_capacity_is_none_not_zero(self, nthu):
        assert self._by_id(nthu, "11510AES 450100").capacity is None

    def test_course_without_times_is_kept(self, nthu):
        c = self._by_id(nthu, "11510AES 510100")
        assert c.times == [] and c.venues == []

    def test_fractional_credits(self, nthu):
        assert self._by_id(nthu, "11510COS 500400").credits % 1 != 0

    def test_enrolled_is_always_none(self, nthu):
        """The open feed publishes 人限 but no current enrollment."""
        assert all(c.enrolled is None for c in nthu.courses("11510"))

    @staticmethod
    def _by_id(adapter: NthuAdapter, course_id: str):
        found = [c for c in adapter.courses("11510") if c.id == course_id]
        assert found, f"{course_id} missing from the sample"
        return found[0]


class TestFiltering:
    def test_drops_cancelled_courses(self, nthu, nthu_raw):
        """停開 courses are in the feed; a search bot should not offer them."""
        cancelled = {r["科號"] for r in nthu_raw if r["停開註記"].strip()}
        assert cancelled, "sample lost its 停開 record"
        assert cancelled.isdisjoint({c.id for c in nthu.courses("11510")})

    def test_unknown_semester_returns_empty(self, nthu):
        assert nthu.courses("10000") == []

    def test_semesters_derived_from_feed(self, nthu):
        assert nthu.semesters() == ["11510"]


class TestContract:
    def test_sample_conforms(self, nthu):
        conforms(nthu.courses("11510"))

    def test_sample_is_searchable(self, nthu):
        courses = nthu.courses("11510")
        assert search(courses, "環境微生物")[0].id == "11510AES 450100"


@pytest.fixture(scope="module")
def live() -> NthuAdapter:
    """Real feed, fetched once per module. Skips rather than fails when offline."""
    adapter = NthuAdapter()
    try:
        adapter.semesters()
    except httpx.HTTPError as exc:
        pytest.skip(f"NTHU open data unreachable: {exc}")
    return adapter


@pytest.mark.integration
class TestLiveFeed:
    def test_whole_semester_conforms(self, live):
        courses = live.courses(live.semesters()[0])
        assert len(courses) > 2000, (
            f"only {len(courses)} courses — feed may have changed"
        )
        conforms(courses)

    def test_expected_fields_are_populated(self, live):
        """Guards against a silent feed schema change renaming a column."""
        courses = live.courses(live.semesters()[0])
        assert sum(1 for c in courses if c.teachers) / len(courses) > 0.95
        assert sum(1 for c in courses if c.times) / len(courses) > 0.80
        assert len({c.department for c in courses}) > 100
