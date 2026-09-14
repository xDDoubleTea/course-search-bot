"""The contract every adapter must satisfy. Contributors import this.

Kept out of tests/ so an adapter in another repo can check itself:

    from conformance import conforms
    conforms(MyAdapter().courses("11510"))
"""

from schema import Course


def conforms(courses: list[Course]) -> None:
    """Raise AssertionError naming the first violation, or return None."""
    assert courses, "adapter returned no courses"

    for c in courses:
        assert isinstance(c, Course), f"not a Course: {type(c).__name__}"
        assert c.id, "course has no id"
        assert c.school, f"{c.id}: no school"
        assert c.semester, f"{c.id}: no semester"
        assert c.name_zh or c.name_en, f"{c.id}: needs at least one name"
        assert isinstance(c.teachers, list), f"{c.id}: teachers must be a list"
        assert isinstance(c.times, list), f"{c.id}: times must be a list"
        assert isinstance(c.venues, list), f"{c.id}: venues must be a list"
        assert c.credits >= 0, f"{c.id}: negative credits"
        assert c.capacity is None or c.capacity >= 0, f"{c.id}: negative capacity"
        assert c.enrolled is None or c.enrolled >= 0, f"{c.id}: negative enrolled"

    ids = [c.id for c in courses]
    duplicates = (
        {i for i in ids if ids.count(i) > 1} if len(ids) != len(set(ids)) else set()
    )
    assert not duplicates, f"duplicate course ids: {sorted(duplicates)[:5]}"

    schools = {c.school for c in courses}
    assert len(schools) == 1, f"adapter mixed schools: {sorted(schools)}"
