"""Live check against NTHU's open data. Skipped when offline."""

import httpx
import pytest

from adapters.nthu import NthuAdapter, _rows, _to_course
from tests.test_conformance import conforms


def test_rows_unpacks_tabs_and_newlines():
    packed = "BMES醫環618\tM3M4\nBMES醫環501\tF3F4\n"
    assert _rows(packed) == [["BMES醫環618", "M3M4"], ["BMES醫環501", "F3F4"]]
    assert _rows("") == []


def test_html_entities_are_unescaped():
    c = _to_course({
        "科號": "11510CS  555100", "課程中文名稱": "測試", "課程英文名稱": "Test",
        "學分數": "2", "人限": "50", "授課教師": "鄭兆&#29641;\tCHENG\n",
        "教室與上課時間": "台達106\tF5F6\n", "停開註記": "",
    })
    assert c.teachers == ["鄭兆珉"]
    assert c.times == ["F5", "F6"]
    assert c.department == "CS"
    assert c.semester == "11510"
    assert c.capacity == 50


def test_missing_capacity_is_none():
    c = _to_course({
        "科號": "11510GE  100000", "課程中文名稱": "x", "課程英文名稱": "x",
        "學分數": "0.5", "人限": "  ", "授課教師": "", "教室與上課時間": "", "停開註記": "",
    })
    assert c.capacity is None and c.enrolled is None
    assert c.credits == 0.5


@pytest.fixture(scope="module")
def live():
    adapter = NthuAdapter()
    try:
        adapter.semesters()
    except httpx.HTTPError as exc:
        pytest.skip(f"NTHU open data unreachable: {exc}")
    return adapter


def test_live_feed_conforms(live):
    courses = live.courses(live.semesters()[0])
    assert len(courses) > 2000, f"only {len(courses)} courses — feed may have changed"
    conforms(courses)
    assert all(c.school == "nthu" for c in courses)
