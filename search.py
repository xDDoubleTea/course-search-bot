"""Generic search over Course[]. School-agnostic — this is the reusable core."""

from schema import Course

SEARCHABLE = ("name_zh", "name_en", "department", "id")


def _haystack(c: Course) -> str:
    parts = [getattr(c, f) for f in SEARCHABLE]
    parts.extend(c.teachers)
    return " ".join(parts).lower()


def search(courses: list[Course], query: str, limit: int = 10) -> list[Course]:
    """Substring scan. Fast enough for one semester held in memory."""
    q = query.strip().lower()
    if not q:
        return []
    hits = [c for c in courses if q in _haystack(c)]
    # exact name match first, then shorter names (less padding = closer match)
    hits.sort(key=lambda c: (q not in c.name_zh.lower(), len(c.name_zh)))
    return hits[:limit]
