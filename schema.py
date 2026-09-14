"""The one shape every adapter must produce. Owned here, not by contributors."""

from dataclasses import dataclass, field, asdict
from typing import Literal

School = Literal["nthu", "ncku"]


@dataclass(frozen=True, slots=True)
class Course:
    id: str  # school-unique, opaque
    school: School
    semester: str  # "11510"
    name_zh: str
    name_en: str
    teachers: list[str]
    department: str
    credits: float
    times: list[str]  # normalized "W3-4", never the school's raw format
    venues: list[str]
    capacity: int | None = None
    enrolled: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def seats_left(self) -> int | None:
        if self.capacity is None or self.enrolled is None:
            return None
        return self.capacity - self.enrolled
