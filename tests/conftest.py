"""Shared fixtures. No test here touches the network unless marked `integration`."""

import json
from pathlib import Path

import pytest

from adapters.nthu import NthuAdapter
from schema import Course

DATA = Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def nthu_raw() -> list[dict]:
    """Ten real records from NTHU's feed, each chosen for a quirk it carries:
    HTML entities, fullwidth Ａ, 停開, missing 人限, no times, two venues,
    six teachers, a four-character department, fractional credits, period 'd'.
    """
    return json.loads((DATA / "nthu_sample.json").read_text())


@pytest.fixture
def nthu(nthu_raw, monkeypatch) -> NthuAdapter:
    """NthuAdapter with the network replaced by the frozen sample."""
    adapter = NthuAdapter()
    monkeypatch.setattr(adapter, "_fetch", lambda: nthu_raw)
    return adapter


@pytest.fixture
def course() -> Course:
    """One fully-populated course. Mutate a copy via dataclasses.replace."""
    return Course(
        id="11510MATH101002",
        school="nthu",
        semester="11510",
        name_zh="微積分Ａ一",
        name_en="Calculus A(I)",
        teachers=["李華倫"],
        department="MATH",
        credits=4.0,
        times=["T1", "T2", "F1", "F2"],
        venues=["DELTA台達109"],
        capacity=116,
        enrolled=None,
    )


@pytest.fixture
def catalog() -> list[Course]:
    """A tiny multi-school catalog for search tests."""
    return [
        Course(
            id="11510MATH101002",
            school="nthu",
            semester="11510",
            name_zh="微積分Ａ一",
            name_en="Calculus A(I)",
            teachers=["李華倫"],
            department="MATH",
            credits=4.0,
            times=["T1", "T2"],
            venues=["DELTA台達109"],
            capacity=116,
            enrolled=58,
        ),
        Course(
            id="11510ESS 240001",
            school="nthu",
            semester="11510",
            name_zh="熱力學",
            name_en="Thermodynamics",
            teachers=["林洸銓"],
            department="ESS",
            credits=3.0,
            times=["M3", "M4"],
            venues=["ESS工科NE69"],
            capacity=55,
            enrolled=55,
        ),
        Course(
            id="11510CS  555100",
            school="nthu",
            semester="11510",
            name_zh="醫學資訊簡介",
            name_en="Introduction to Medical Informatics",
            teachers=["葉肩宇", "唐傳義"],
            department="CS",
            credits=2.0,
            times=["F5", "F6"],
            venues=["DELTA台達106"],
            capacity=50,
            enrolled=31,
        ),
    ]
