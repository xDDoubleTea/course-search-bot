"""The one shape every adapter must produce. Owned here, not by contributors."""

from dataclasses import asdict, dataclass, field
from typing import Literal

School = Literal["nthu", "ncku"]


@dataclass(frozen=True, slots=True)
class Course:
    id: str
    school: School
    semester: str
    name_zh: str
    name_en: str
    teachers: list[str]
    department: str
    credits: float
    times: list[str]
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
