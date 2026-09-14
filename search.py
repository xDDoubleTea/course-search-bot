"""Generic search over Course[]. School-agnostic — this is the reusable core."""

from rapidfuzz import fuzz, process

from schema import Course

SEARCHABLE = ("name_zh", "name_en", "department", "id")

# Fullwidth ASCII sits 0xFEE0 above its halfwidth twin. Same three ranges
# NTHUMods folds in packages/shared/src/utils/characters.ts: digits, A-Z, a-z.
# Punctuation (：（）／) is deliberately left alone — folding it changes no match.
_FULLWIDTH_OFFSET = 0xFEE0
_FULLWIDTH_RANGES = ((0xFF10, 0xFF19), (0xFF21, 0xFF3A), (0xFF41, 0xFF5A))
_FOLD = {
    cp: chr(cp - _FULLWIDTH_OFFSET)
    for low, high in _FULLWIDTH_RANGES
    for cp in range(low, high + 1)
}


def fold(text: str) -> str:
    """Fullwidth ASCII to halfwidth, then casefold.

    Applied to the data as well as the query: 微積分Ａ一 carries a fullwidth Ａ, so
    folding only user input would still miss it.
    """
    return text.translate(_FOLD).lower()


def haystack(c: Course) -> str:
    parts = [getattr(c, f) for f in SEARCHABLE]
    parts.extend(c.teachers)
    return fold(" ".join(parts))


def build_index(courses: list[Course]) -> list[str]:
    """Fold every course once. Building this is ~90% of a cold search, so callers
    that search the same list repeatedly should build it at load time."""
    return [haystack(c) for c in courses]


def search(
    courses: list[Course],
    query: str,
    limit: int = 10,
    cutoff: float = 70.0,
    index: list[str] | None = None,
) -> list[Course]:
    """Fuzzy match, so one typo still finds the course.

    partial_ratio scores the best-matching window of the haystack, which keeps a
    short query from being penalised by everything else concatenated after it.
    """
    q = fold(query.strip())
    if not q:
        return []
    hits = process.extract(
        q,
        build_index(courses) if index is None else index,
        scorer=fuzz.partial_ratio,
        limit=limit * 4,
        score_cutoff=cutoff,
    )
    # Best score first; ties broken by shorter title, where the query fills more of it.
    ranked = sorted(hits, key=lambda hit: (-hit[1], len(courses[hit[2]].name_zh)))
    return [courses[index] for _, _, index in ranked[:limit]]
