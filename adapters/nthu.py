"""NTHU adapter. Port the mapping from courseweb tools/data-sync/src/scrapers.ts."""

from schema import Course


class NthuAdapter:
    school = "nthu"

    def semesters(self) -> list[str]:
        raise NotImplementedError("step 2")

    def courses(self, semester: str) -> list[Course]:
        raise NotImplementedError("step 2")
