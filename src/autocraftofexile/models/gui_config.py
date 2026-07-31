from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self


@dataclass(slots=True)
class Coordinates:
    x: int
    y: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            x=data["x"],
            y=data["y"],
        )


@dataclass(slots=True)
class GuiConfig:
    showcase: Coordinates

    transmute: Coordinates
    augment: Coordinates
    alteration: Coordinates
    regal: Coordinates
    alchemy: Coordinates
    chaos: Coordinates
    exalt: Coordinates
    scour: Coordinates
    annul: Coordinates

    start_hotkey: str
    stop_hotkey: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            showcase=Coordinates.from_dict(data["showcase"]),
            transmute=Coordinates.from_dict(data["transmute"]),
            augment=Coordinates.from_dict(data["augment"]),
            alteration=Coordinates.from_dict(data["alteration"]),
            regal=Coordinates.from_dict(data["regal"]),
            alchemy=Coordinates.from_dict(data["alchemy"]),
            chaos=Coordinates.from_dict(data["chaos"]),
            exalt=Coordinates.from_dict(data["exalt"]),
            scour=Coordinates.from_dict(data["scour"]),
            annul=Coordinates.from_dict(data["annul"]),
            start_hotkey=data["start_hotkey"],
            stop_hotkey=data["stop_hotkey"],
        )
