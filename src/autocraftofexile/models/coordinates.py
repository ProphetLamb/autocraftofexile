from dataclasses import dataclass


@dataclass(slots=True)
class Coordinates:
    x: int
    y: int
