"""NYCU adapter. Parsing runs against a frozen sample; only `integration` hits the site."""

import httpx
import pytest

from adapters.nycu import NycuAdapter, parse_cos_time
from conformance import conforms
from search import search


class TestParseCosTime:
    @pytest.mark.parametrize(
        "raw,times,venues",
        [
            ("M34W2-ED201[GF]", ["M3", "M4", "W2"], ["ED201"]),
            ("R56-SA320[GF]", ["R5", "R6"], ["SA320"]),
            ("M56-", ["M5", "M6"], []),
            ("Mbcd-", ["Mb", "Mc", "Md"], []),
            ("T34F34-", ["T3", "T4", "F3", "F4"], []),
            ("", [], []),
            ("   ", [], []),
        ],
        ids=[
            "venue+flag",
            "single day",
            "no venue",
            "letter periods",
            "two days",
            "empty",
            "blank",
        ],
    )
    def test_unpacks_days_periods_and_venue(self, raw, times, venues):
        assert parse_cos_time(raw) == (times, venues)

    def test_one_slot_two_rooms_keeps_both_venues_once(self):
        """F78-CS100[GF],F78-YX216[YM] is one class taught in two rooms."""
        assert parse_cos_time("F78-CS100[GF],F78-YX216[YM]") == (
            ["F7", "F8"],
            ["CS100", "YX216"],
        )


class TestFieldMapping:
    def test_id_carries_semester(self, nycu):
        """cos_id alone repeats across departments for cross-listed courses."""
        for c in nycu.courses("1151"):
            assert c.id.startswith("1151_")

    def test_ids_are_unique(self, nycu):
        ids = [c.id for c in nycu.courses("1151")]
        assert len(ids) == len(set(ids))

    def test_teachers_split_on_ideographic_comma(self, nycu):
        assert all("、" not in t for c in nycu.courses("1151") for t in c.teachers)

    def test_department_is_the_chinese_name(self, nycu):
        assert all(c.department for c in nycu.courses("1151"))

    def test_no_cap_sentinel_becomes_none(self, nycu):
        """num_limit 9999 means no cap, not a cap of 9999."""
        assert all(c.capacity != 9999 for c in nycu.courses("1151"))

    def test_unpublished_enrolment_becomes_none(self, nycu):
        """reg_num is -999 outside the enrolment window."""
        assert all(c.enrolled is None or c.enrolled >= 0 for c in nycu.courses("1151"))


class TestContract:
    def test_sample_conforms(self, nycu):
        conforms(nycu.courses("1151"))

    def test_sample_is_searchable(self, nycu):
        assert search(nycu.courses("1151"), "微積分")


@pytest.fixture(scope="module")
def live() -> NycuAdapter:
    adapter = NycuAdapter()
    try:
        adapter.semesters()
    except httpx.HTTPError as exc:
        pytest.skip(f"NYCU timetable unreachable: {exc}")
    yield adapter
    adapter.close()


@pytest.mark.integration
class TestLiveSite:
    def test_semesters_are_listed_newest_first(self, live):
        """Academic years run from two to three digits (87 to 115), so they only
        order correctly as integers."""
        years = [int(s[:-1]) for s in live.semesters()]
        assert len(years) > 10
        assert years == sorted(years, reverse=True)

    def test_department_walk_finds_the_whole_university(self, live):
        """A drop here means the type/category/college chain changed shape."""
        assert len(live.departments(live.semesters()[0])) > 200
