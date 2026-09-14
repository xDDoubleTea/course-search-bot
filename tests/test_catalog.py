"""catalog.py caches to disk and isolates a failing school. No network here."""

import dataclasses
import json
import time

import pytest

import catalog
from conformance import conforms
from schema import Course


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"


@pytest.fixture
def one_school(monkeypatch, catalog_stub):
    monkeypatch.setattr(catalog, "ADAPTERS", {"nthu": object})
    monkeypatch.setattr(catalog, "fetch", catalog_stub)
    return catalog_stub


@pytest.fixture
def catalog_stub(course):
    calls = []

    def fetch(school):
        calls.append(school)
        return [dataclasses.replace(course, school=school)]

    fetch.calls = calls
    return fetch


def test_fetches_then_serves_from_cache(one_school, cache_dir):
    first = catalog.load(cache_dir=cache_dir)
    second = catalog.load(cache_dir=cache_dir)
    assert first == second
    assert one_school.calls == ["nthu"], "second load should not re-fetch"


def test_refresh_bypasses_the_cache(one_school, cache_dir):
    catalog.load(cache_dir=cache_dir)
    catalog.load(cache_dir=cache_dir, refresh=True)
    assert one_school.calls == ["nthu", "nthu"]


def test_stale_cache_is_refetched(one_school, cache_dir):
    catalog.load(cache_dir=cache_dir)
    path = cache_dir / "nthu.json"
    old = time.time() - 10_000
    import os

    os.utime(path, (old, old))
    catalog.load(cache_dir=cache_dir, max_age=1)
    assert one_school.calls == ["nthu", "nthu"]


def test_corrupt_cache_is_discarded_not_raised(one_school, cache_dir):
    catalog.load(cache_dir=cache_dir)
    (cache_dir / "nthu.json").write_text("{not json")
    assert catalog.load(cache_dir=cache_dir)


def test_cached_courses_survive_the_round_trip(one_school, cache_dir, course):
    catalog.load(cache_dir=cache_dir)
    rows = json.loads((cache_dir / "nthu.json").read_text())
    assert Course(**rows[0]) == dataclasses.replace(course, school="nthu")


def test_a_failing_school_is_skipped(monkeypatch, cache_dir, course):
    def fetch(school):
        if school == "broken":
            raise RuntimeError("university is down")
        return [dataclasses.replace(course, school=school)]

    monkeypatch.setattr(catalog, "ADAPTERS", {"broken": object, "nthu": object})
    monkeypatch.setattr(catalog, "fetch", fetch)
    loaded = catalog.load(cache_dir=cache_dir)
    assert [c.school for c in loaded] == ["nthu"]
    conforms(loaded)


def test_every_adapter_is_registered():
    """A new adapter is only reachable once catalog knows about it."""

    registered = set(catalog.ADAPTERS)
    assert registered == {"nthu", "ncku", "nycu"}
    for school, factory in catalog.ADAPTERS.items():
        assert factory.school == school
