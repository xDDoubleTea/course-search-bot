"""NCKU adapter. Port the mapping from public course-query.acad.ncku.edu.tw — no login."""

from schema import Course


class NckuAdapter:
    school = "ncku"

    def semesters(self) -> list[str]:
        raise NotImplementedError("step 3")

    def courses(self, semester: str) -> list[Course]:
        raise NotImplementedError("step 3")
