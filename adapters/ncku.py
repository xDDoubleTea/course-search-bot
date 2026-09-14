"""NCKU adapter, reading NCKU HUB rather than the university.

https://nckuhub.com/course/            current semester, 4821 courses, one GET
https://nckuhub.com/course/allCoursePrev  19 semesters of history, 10.8 MB
https://nckuhub.com/course/allDpmt     182 department codes

NCKU's own catalogue is not usable: every filter value is a per-session
encrypted token, the query JavaScript is obfuscated, and a captcha gate fires
under load. NCKU HUB scrapes it server-side and republishes the result as
public JSON, so that is what this adapter reads.

Two caveats worth knowing. NCKU HUB's own code has not been touched since 2020
and its maintainers have left, so this source is unattended even though it is
still running. And the live list carries no semester label: the current term is
derived from the newest semester in the archive.

Seat counts are deliberately not exposed. They live on the per-course endpoint,
cost one request each, and carry mixed ages -- roughly two thirds were last
written months ago -- so reporting them as current would mislead.
"""

import re
import ssl

import httpx

from schema import Course

BASE = "https://nckuhub.com/"

# 時間 looks like "[2]2 [5]3~4", and some rows have a flex-time widget appended
# as raw HTML inside the field.
_TAG = re.compile(r"<[^>]*>")
_GROUP = re.compile(r"\[(\d+)\]([^\[]*)")

# Periods continue past 9 into letters, and N is the noon slot sitting between
# 4 and 5 -- the data carries "3~N", "4~N", "N~5" and "N~6", so the ordering
# below is what makes those ranges expand correctly.
_PERIODS = "01234N56789ABCDE"

# Stripping the flex-time widget's tags leaves its label behind, so periods are
# extracted by pattern rather than by splitting on whitespace.
_TOKEN = re.compile(r"[0-9A-EN](?:~[0-9A-EN])?")

# NCKU numbers its weekdays. Mapping them onto the letters NTHU and NYCU use
# keeps one time vocabulary across every school in the schema.
_DAYS = {"1": "M", "2": "T", "3": "W", "4": "R", "5": "F", "6": "S", "7": "U"}


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def _expand(token: str) -> list[str]:
    start, _, end = token.partition("~")
    if not end:
        return [start] if start else []
    try:
        low, high = _PERIODS.index(start), _PERIODS.index(end)
    except ValueError:
        return [start, end]
    return list(_PERIODS[low : high + 1])


def parse_time(raw: str) -> list[str]:
    """ "[2]2 [5]3~4" -> ["T2", "F3", "F4"]."""
    slots: list[str] = []
    for day, periods in _GROUP.findall(_TAG.sub("", raw or "")):
        letter = _DAYS.get(day, day)
        for token in _TOKEN.findall(periods):
            slots.extend(letter + period for period in _expand(token))
    return slots


def parse_teachers(raw: str) -> list[str]:
    """The course coordinator is flagged with a trailing asterisk."""
    return [name.strip(" *") for name in (raw or "").split(",") if name.strip(" *")]


def next_semester(semester: str) -> str:
    """ "114-2" -> "115-1". NCKU runs two terms per academic year."""
    year, _, term = semester.partition("-")
    return f"{year}-2" if term == "1" else f"{int(year) + 1}-1"


def _to_course(raw: dict, semester: str) -> Course:
    return Course(
        id=f"{semester}_{raw['id']}",
        school="ncku",
        semester=semester,
        name_zh=(raw.get("課程名稱") or "").strip(),
        name_en="",
        teachers=parse_teachers(raw.get("老師", "")),
        department=(raw.get("系號") or "").strip(),
        credits=float(raw.get("學分") or 0),
        times=parse_time(raw.get("時間", "")),
        venues=[],
        capacity=None,
        enrolled=None,
    )


class NckuAdapter:
    school = "ncku"

    def __init__(self, base: str = BASE) -> None:
        self._base = base
        self._client: httpx.Client | None = None
        self._archive: list[dict] | None = None

    def _get(self, path: str):
        if self._client is None:
            self._client = httpx.Client(
                verify=_ssl_context(),
                timeout=180,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
        response = self._client.get(self._base + path)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _history(self) -> list[dict]:
        if self._archive is None:
            self._archive = self._get("course/allCoursePrev")
        return self._archive

    def current_semester(self) -> str:
        """The archive lags one term behind the live list, so the newest label
        it holds is the semester before the one being taught."""
        archived = {row["semester"] for row in self._history() if row.get("semester")}
        return next_semester(
            max(archived, key=lambda s: [int(p) for p in s.split("-")])
        )

    def semesters(self) -> list[str]:
        archived = {row["semester"] for row in self._history() if row.get("semester")}
        ordered = sorted(
            archived, key=lambda s: [int(p) for p in s.split("-")], reverse=True
        )
        return [self.current_semester(), *ordered]

    def departments(self) -> dict[str, str]:
        return {
            d["DepPrefix"].strip(): d["DepName"].strip()
            for d in self._get("course/allDpmt")
        }

    def courses(self, semester: str) -> list[Course]:
        """The current term comes from the live list, which carries times and
        credits. Earlier terms come from the archive, which carries neither."""
        if semester == self.current_semester():
            return [
                _to_course(raw, semester) for raw in self._get("course/")["courses"]
            ]
        return [
            _to_course(raw, semester)
            for raw in self._history()
            if raw.get("semester") == semester
        ]
