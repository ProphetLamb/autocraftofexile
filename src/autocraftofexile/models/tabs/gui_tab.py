from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Self

import cv2
import numpy as np
from rich import print
from rich.prompt import Prompt

from ..coordinates import Coordinates
from .tab_overlay_selector import TabOverlaySelector


@dataclass(slots=True)
class GuiTab(ABC):
    """One addressable Path of Exile stash-tab layout."""

    items: dict[str, Coordinates] = field(default_factory=dict[str, Coordinates])

    @classmethod
    @abstractmethod
    def name(cls) -> tuple[str, ...]:
        """The name of the tab"""

    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """The loaded or detected configuration contains all required currencies"""

    @classmethod
    @abstractmethod
    def selector(cls) -> TabOverlaySelector:
        """Instantiate the overlay selector for tab detection"""

    def detect(self) -> None:
        """Interactively detect and store currency coordinates."""
        Prompt.ask(
            f"[bright_white]Open the {self.name()} stash tab.[/bright_white] "
            "Press ENTER when ready"
        )

        # Imported lazily so importing the package does not require a graphical
        # session, which is useful for uv build, tests, and documentation jobs.
        import pyautogui

        screenshot_rgb = np.asarray(pyautogui.screenshot())
        screenshot = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2BGR)
        print(
            "[bright_white]Move and resize the mask until the generated slot "
            "outlines fit the tab.[/bright_white]"
        )
        detected = self.selector().detect(screenshot)
        if detected is None:
            raise ValueError("Selection aborted")
        self.items.clear()
        self.items.update(detected)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        name = tuple[str](part for part in (data.get("name") or list[str]()))
        if name != cls.name():
            raise ValueError(f"Invalid tab name {name!r}, expected {cls.name()!r}")
        return cls(
            items={
                name: Coordinates(**coordinates_data)
                for name, coordinates_data in (
                    data.get("items") or dict[str, Any]()
                ).items()
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name(),
            "items": {name: asdict(coords) for name, coords in self.items.items()},
        }
