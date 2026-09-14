"""Loads every school's courses once and caches them on disk.

A full crawl is slow -- NYCU alone is ~257 requests, about three minutes -- so
the bot must not repeat it on every restart, and must never run it inside a
command handler. Courses are fetched on a schedule, cached as JSON, and
searched locally. That is the same shape as issue #856 upstream.

A school that fails to load is skipped rather than taking the bot down with it,
because these are unattended university servers and one being unreachable is
normal.
"""

import json
import logging
import time
from pathlib import Path

from adapters.ncku import NckuAdapter
from adapters.nthu import NthuAdapter
from adapters.nycu import NycuAdapter
from schema import Course

logger = logging.getLogger(__name__)

ADAPTERS = {"nthu": NthuAdapter, "ncku": NckuAdapter, "nycu": NycuAdapter}

CACHE_DIR = Path(".cache")
MAX_AGE_SECONDS = 24 * 60 * 60


def _cache_path(school: str, cache_dir: Path) -> Path:
    return cache_dir / f"{school}.json"


def _read_cache(path: Path, max_age: float) -> list[Course] | None:
    if not path.exists() or time.time() - path.stat().st_mtime > max_age:
        return None
    try:
        return [Course(**row) for row in json.loads(path.read_text())]
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("discarding unreadable cache %s: %s", path, exc)
        return None


def _write_cache(path: Path, courses: list[Course]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([c.to_dict() for c in courses], ensure_ascii=False))


def fetch(school: str) -> list[Course]:
    """The newest semester the school publishes."""
    adapter = ADAPTERS[school]()
    try:
        semester = adapter.semesters()[0]
        return adapter.courses(semester)
    finally:
        close = getattr(adapter, "close", None)
        if close is not None:
            close()


def load(
    schools: list[str] | None = None,
    cache_dir: Path = CACHE_DIR,
    max_age: float = MAX_AGE_SECONDS,
    refresh: bool = False,
) -> list[Course]:
    courses: list[Course] = []
    for school in schools or list(ADAPTERS):
        path = _cache_path(school, cache_dir)
        cached = None if refresh else _read_cache(path, max_age)
        if cached is not None:
            logger.info("%s: %d courses from cache", school, len(cached))
            courses.extend(cached)
            continue
        try:
            fetched = fetch(school)
        except Exception as exc:
            logger.warning("%s: load failed, skipping (%s)", school, exc)
            continue
        logger.info("%s: %d courses fetched", school, len(fetched))
        _write_cache(path, fetched)
        courses.extend(fetched)
    return courses
