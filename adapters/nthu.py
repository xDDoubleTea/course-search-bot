"""NTHU adapter, reading the university's own open course data.

https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/OPENDATA/open_course_data.json
Published daily by 教務處課務組, ~3.4 MB, current semester only, no login.

The published page says the Chinese is "UTF-16", but the file is ASCII with
\\uXXXX escapes — ordinary JSON string escaping. Any JSON parser handles it.
Some values do carry raw HTML entities (鄭兆&#29641;), so every string is
unescaped on the way in.

Enrollment counts are not in this feed; `enrolled` is always None. Seat
tracking needs JH84201.php, which is captcha-gated.
"""

import html
import re
import ssl

import httpx

from schema import Course

URL = "https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/OPENDATA/open_course_data.json"


def _ssl_context() -> ssl.SSLContext:
    """ccxp's certificate has no Subject Key Identifier, which OpenSSL 3.x rejects
    under VERIFY_X509_STRICT. Drop that one RFC 5280 check; chain verification and
    hostname checking stay on."""
    context = ssl.create_default_context()
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


# 科號 is fixed-width: 11510 AES_ 450100  ->  semester, department, number
_SEMESTER = slice(0, 5)
_DEPARTMENT = slice(5, 9)

# A time string is repeated day-letter + period, e.g. "W2W3W4", "TbTcTd".
_SLOT = re.compile(r"[MTWRFSU][0-9nabcd]")


def _clean(value: str) -> str:
    return html.unescape(value or "").strip()


def _rows(packed: str) -> list[list[str]]:
    """'venue\\ttime\\nvenue\\ttime\\n' -> [[venue, time], [venue, time]]"""
    return [
        [_clean(cell) for cell in line.split("\t")]
        for line in (packed or "").split("\n")
        if line.strip()
    ]


def _to_course(raw: dict) -> Course:
    code = raw["科號"]
    schedule = _rows(raw.get("教室與上課時間", ""))

    times: list[str] = []
    venues: list[str] = []
    for row in schedule:
        if row and row[0]:
            venues.append(row[0])
        if len(row) > 1:
            times.extend(_SLOT.findall(row[1]))

    capacity = _clean(raw.get("人限", ""))

    return Course(
        id=code,
        school="nthu",
        semester=code[_SEMESTER],
        name_zh=_clean(raw.get("課程中文名稱", "")),
        name_en=_clean(raw.get("課程英文名稱", "")),
        teachers=[row[0] for row in _rows(raw.get("授課教師", "")) if row and row[0]],
        department=code[_DEPARTMENT].strip(),
        credits=float(_clean(raw.get("學分數", "")) or 0),
        times=times,
        venues=venues,
        capacity=int(capacity) if capacity.isdigit() else None,
        enrolled=None,
    )


class NthuAdapter:
    school = "nthu"

    def __init__(self, url: str = URL) -> None:
        self._url = url
        self._raw: list[dict] | None = None

    def _fetch(self) -> list[dict]:
        if self._raw is None:
            response = httpx.get(self._url, timeout=60, verify=_ssl_context())
            response.raise_for_status()
            self._raw = response.json()
        return self._raw if self._raw is not None else []

    def semesters(self) -> list[str]:
        return sorted({r["科號"][_SEMESTER] for r in self._fetch()}, reverse=True)

    def courses(self, semester: str) -> list[Course]:
        """Cancelled courses (停開註記) are dropped — a search bot should not offer them."""
        return [
            _to_course(raw)
            for raw in self._fetch()
            if raw["科號"][_SEMESTER] == semester
            and not _clean(raw.get("停開註記", ""))
        ]
