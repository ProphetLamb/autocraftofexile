from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Self

import keyboard
from rich import print

from .tabs.currency_general_tab import CurrencyGeneralTab
from .tabs.gui_tab import GuiTab

_logger = logging.getLogger(__name__)


def prompt_hotkey(name: str) -> str:
    _logger.debug("begin prompting %s hotkey", name)
    time.sleep(0.1)
    print(f"\nPress the [bright_white]{name}[/bright_white] hotkey.")
    hotkey = keyboard.read_hotkey(suppress=False)
    print(f"[bright_white]{name}[/bright_white] hotkey: [cyan]{hotkey}[/cyan]")
    _logger.debug("done prompting %s hotkey", name)
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
        _logger.debug("adding tab %s", tab.name())
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
            start_hotkey=data.get("start_hotkey") or "",
            stop_hotkey=data.get("stop_hotkey") or "",
        )
        for raw_tab in data.get("tabs") or list[Any]():
            name = tuple(x for x in raw_tab.get("name"))
            tab_class = WellknownTabs.tab_types.get(name)
            if tab_class:
                config.add_tab(tab_class.from_dict(raw_tab))
            else:
                _logger.error("Unknown tab name %s", name)
        return config

    def prompt_missing_config(self) -> bool:
        _logger.debug("begin prompt missing config")
        changed = False
        if not self.start_hotkey:
            print("Missing [cyan]start[/cyan] hotkey")
            self.start_hotkey = prompt_hotkey("start")
            changed = True
        if not self.stop_hotkey:
            print("Missing [cyan]stop[/cyan] hotkey")
            self.stop_hotkey = prompt_hotkey("stop")
            changed = True
        for tab in self.tabs.values():
            if not tab.tab_header:
                print(
                    f"Invalid [cyan]{tab.name()!r}[/cyan] tab configuration\n"
                    "Missing tab header"
                )
            missing_items = tab.missing_items
            if missing_items:
                print(
                    f"Invalid [cyan]{tab.name()!r}[/cyan] tab configuration\n"
                    f"Missing items: {', '.join(f'[bright_white]{x}[/bright_white]' for x in missing_items)}"
                )
            if not tab.tab_header or missing_items:
                tab.detect(
                    preserve_items=not missing_items,
                    preserve_tab_header=bool(tab.tab_header),
                )
                changed = True
        if not WellknownTabs.currency_general in self.tabs:
            tab = CurrencyGeneralTab()
            tab.detect()
            self.add_tab(tab)
            changed = True
        _logger.debug("done prompt missing config, changed=%s", changed)
        return changed
