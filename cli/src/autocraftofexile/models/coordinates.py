from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self


@dataclass(slots=True, frozen=True)
class Coordinates:
    x: int
    y: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> Self | None:
        if not data:
            return None
        x, y = (int(data.get("x") or 0), int(data.get("y") or 0))
        if not x or not y:
            return None
        return cls(x, y)
