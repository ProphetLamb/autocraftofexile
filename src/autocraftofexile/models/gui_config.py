from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self


@dataclass(slots=True)
class Coordinates:
    x: int
    y: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> Self | None:
        if not data or not "x" in data or not "y" in data:
            return None
        return cls(x=data["x"], y=data["y"])


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
    jeweller: Coordinates
    fusing: Coordinates

    start_hotkey: str
    stop_hotkey: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            showcase=Coordinates.from_dict(data.get("showcase")),  # type: ignore
            transmute=Coordinates.from_dict(data.get("transmute")),  # type: ignore
            augment=Coordinates.from_dict(data.get("augment")),  # type: ignore
            alteration=Coordinates.from_dict(data.get("alteration")),  # type: ignore
            regal=Coordinates.from_dict(data.get("regal")),  # type: ignore
            alchemy=Coordinates.from_dict(data.get("alchemy")),  # type: ignore
            chaos=Coordinates.from_dict(data.get("chaos")),  # type: ignore
            exalt=Coordinates.from_dict(data.get("exalt")),  # type: ignore
            scour=Coordinates.from_dict(data.get("scour")),  # type: ignore
            annul=Coordinates.from_dict(data.get("annul")),  # type: ignore
            jeweller=Coordinates.from_dict(data.get("jeweller")),  # type: ignore
            fusing=Coordinates.from_dict(data.get("fusing")),  # type: ignore
            start_hotkey=data.get("start_hotkey"),  # type: ignore
            stop_hotkey=data.get("stop_hotkey"),  # type: ignore
        )
