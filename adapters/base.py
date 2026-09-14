"""Contributors implement this. Nothing else."""

from typing import Protocol

from schema import Course


class Adapter(Protocol):
    school: str

    def semesters(self) -> list[str]:
        """Newest first. e.g. ['11510', '11420']"""
        ...

    def courses(self, semester: str) -> list[Course]:
        """Every course for one semester. Public data only, no login."""
        ...
