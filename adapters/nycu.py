"""NYCU adapter, reading the public course timetable.

https://timetable.nycu.edu.tw/?r=main/<action>

Plain jQuery endpoints returning JSON. No login, no captcha, no signed
parameters. Unset parameters must be the string "**"; sending "" gets a bare
400 with an empty body and no explanation.

There is no bulk endpoint, so a full semester means one request per department
(~257 of them, about three minutes). That suits a scheduled crawl, not a
per-query lookup.
"""

import re
import ssl

import httpx

from schema import Course

BASE = "https://timetable.nycu.edu.tw/"

QUERY_KEYS = [
    "m_acy",
    "m_sem",
    "m_acyend",
    "m_semend",
    "m_dep_uid",
    "m_group",
    "m_grade",
    "m_class",
    "m_option",
    "m_crsname",
    "m_teaname",
    "m_cos_id",
    "m_cos_code",
    "m_crstime",
    "m_crsoutline",
    "m_costype",
    "m_selcampus",
]

UNSET = "**"

# "M34W2-ED201[GF]" or "F78-CS100[GF],F78-YX216[YM]": comma-separated segments,
# each "<day+periods>-<venue>[<campus>]". Validated against 450 live rows.
_SLOT = re.compile(r"([MTWRFSU])([0-9a-z]+)")

# num_limit uses 9999 for "no cap" and reg_num uses -999 for "not published".
_NO_CAP = "9999"
_NO_COUNT = "-999"


def _ssl_context() -> ssl.SSLContext:
    """NYCU's certificate omits the Subject Key Identifier that OpenSSL 3.x
    requires under VERIFY_X509_STRICT. Chain and hostname checks stay on."""
    context = ssl.create_default_context()
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def _split_semester(semester: str) -> tuple[str, str]:
    """ "1151" -> ("115", "1"), "99X" -> ("99", "X").

    The academic year is two or three digits depending on how far back the
    semester goes, so only the trailing term character has a fixed position.
    """
    return semester[:-1], semester[-1]


def parse_cos_time(raw: str) -> tuple[list[str], list[str]]:
    """A slot repeated across segments is one class in two rooms, so the times
    are deduplicated while the venues are both kept."""
    times: dict[str, None] = {}
    venues: list[str] = []
    for segment in (raw or "").split(","):
        if not segment.strip():
            continue
        slots, _, place = segment.partition("-")
        for day, periods in _SLOT.findall(slots):
            times.update(dict.fromkeys(day + period for period in periods))
        venue = place.split("[")[0].strip()
        if venue and venue not in venues:
            venues.append(venue)
    return list(times), venues


def _to_course(raw: dict, department: str) -> Course:
    times, venues = parse_cos_time(raw.get("cos_time", ""))
    capacity = raw.get("num_limit", "")
    enrolled = raw.get("reg_num", "")

    return Course(
        id=f"{raw['acy']}{raw['sem']}_{raw['cos_id']}",
        school="nycu",
        semester=f"{raw['acy']}{raw['sem']}",
        name_zh=(raw.get("cos_cname") or "").strip(),
        name_en=(raw.get("cos_ename") or "").strip(),
        teachers=[t for t in (raw.get("teacher") or "").split("、") if t.strip()],
        department=department,
        credits=float(raw.get("cos_credit") or 0),
        times=times,
        venues=venues,
        capacity=None if capacity in ("", _NO_CAP) else int(capacity),
        enrolled=None if enrolled in ("", _NO_COUNT) else int(enrolled),
    )


def flatten(payload: dict) -> list[Course]:
    """get_cos_list nests courses under department, then a numeric group key."""
    courses = []
    for department in payload.values():
        name = department.get("dep_cname") or department.get("dep_ename") or ""
        for group, entries in department.items():
            if isinstance(entries, dict) and group.isdigit():
                courses.extend(_to_course(raw, name) for raw in entries.values())
    return courses


class NycuAdapter:
    school = "nycu"

    def __init__(self, base: str = BASE) -> None:
        self._base = base
        self._client: httpx.Client | None = None

    def _post(self, action: str, **data: str) -> dict | list:
        if self._client is None:
            self._client = httpx.Client(
                verify=_ssl_context(),
                timeout=120,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            self._client.get(self._base)
        response = self._client.post(f"{self._base}?r=main/{action}", data=data)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def semesters(self) -> list[str]:
        return [row["T"] for row in self._post("get_acysem")]

    def departments(self, semester: str) -> set[str]:
        """Every department uid, found by walking type -> category -> college."""
        base = {"flang": "zh-tw", "acysem": semester, "acysemend": semester}
        found: set[str] = set()
        for course_type in self._post("get_type", **base):
            scope = {**base, "ftype": course_type["uid"]}
            for category in self._post("get_category", **scope):
                narrowed = {**scope, "fcategory": category}
                for college in self._post("get_college", **narrowed):
                    found.update(self._post("get_dep", **narrowed, fcollege=college))
        return found

    def courses(self, semester: str) -> list[Course]:
        """One request per department, deduplicated: a cross-listed course is
        returned once per department that lists it."""
        acy, term = _split_semester(semester)
        seen: dict[str, Course] = {}
        for uid in sorted(self.departments(semester)):
            query = dict.fromkeys(QUERY_KEYS, UNSET)
            query.update(
                m_acy=acy, m_sem=term, m_acyend=acy, m_semend=term, m_dep_uid=uid
            )
            payload = self._post("get_cos_list", **query)
            if isinstance(payload, dict):
                for course in flatten(payload):
                    seen.setdefault(course.id, course)
        return list(seen.values())
