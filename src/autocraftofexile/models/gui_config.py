from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Self

import keyboard
import pyautogui
from rich import print

from .coordinates import Coordinates
from .tabs.currency_general_tab import CurrencyGeneralTab
from .tabs.gui_tab import GuiTab

_logger = logging.getLogger(__name__)


def prompt_coordinates(name: str) -> Coordinates:
    time.sleep(0.1)
    input(f"Move mouse to the {name} and press ENTER")
    x, y = pyautogui.position()
    print(f"[bright_white]{name}[/bright_white]: {x}, {y}")
    return Coordinates(x, y)


def prompt_hotkey(name: str) -> str:
    time.sleep(0.1)
    print(f"\nPress the [bright_white]{name}[/bright_white] hotkey.")
    hotkey = keyboard.read_hotkey(suppress=False)
    print(f"[bright_white]{name}[/bright_white] hotkey: [cyan]{hotkey}[/cyan]")
    return hotkey


class WellknownTabs:
    currency_general = ("currency", "general")
    currency_exotic = ("currency", "exotic")

    tab_types: Mapping[tuple[str, ...], type[GuiTab]] = {
        currency_general: CurrencyGeneralTab
    }


@dataclass(slots=True)
class GuiConfig:
    start_hotkey: str
    stop_hotkey: str
    tabs: dict[tuple[str, ...], GuiTab] = field(
        default_factory=dict[tuple[str, ...], GuiTab]
    )

    def add_tab(self, tab: GuiTab) -> None:
        if tab.name in self.tabs:
            raise ValueError(f"GUI tab {tab.name!r} is already configured")
        self.tabs[tab.name()] = tab

    @property
    def currency_general(self) -> CurrencyGeneralTab:
        return self.tabs[WellknownTabs.currency_general]  # pyright: ignore[reportReturnType]

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_hotkey": self.start_hotkey,
            "stop_hotkey": self.stop_hotkey,
            "tabs": [tab.to_dict() for tab in self.tabs.values()],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        config = cls(
            start_hotkey=data.get("start_hotkey"),  # pyright: ignore[reportArgumentType]
            stop_hotkey=data.get("stop_hotkey"),  # pyright: ignore[reportArgumentType]
        )
        for raw_tab in data.get("tabs") or list[Any]():
            name = raw_tab.get("name")
            tab_class = WellknownTabs.tab_types.get(name)
            if tab_class:
                config.add_tab(tab_class.from_dict(raw_tab))
            else:
                _logger.error("Unknown tab name %s", name)
        return config

    def prompt_missing_config(self):
        if not self.start_hotkey:
            self.start_hotkey = prompt_hotkey("start")
        if not self.stop_hotkey:
            self.stop_hotkey = prompt_hotkey("stop")
        for tab in self.tabs.values():
            if not tab.is_valid:
                tab.detect()
        if not WellknownTabs.currency_general in self.tabs:
            tab = CurrencyGeneralTab()
            tab.detect()
            self.add_tab(tab)
