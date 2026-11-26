from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Self

from .tabs.currency_atlas_tab import CurrencyAtlasTab
from .tabs.currency_general_tab import CurrencyGeneralTab
from .tabs.gui_tab import GuiTab

_logger = logging.getLogger(__name__)

class WellknownTabs:
    currency_general = ("currency", "general")
    currency_atlas = ("currency", "atlas")

    tab_types: Mapping[tuple[str, ...], type[GuiTab]] = {
        currency_general: CurrencyGeneralTab,
        currency_atlas: CurrencyAtlasTab,
    }


@dataclass(slots=True)
class GuiConfig:
    start_hotkey: str
    stop_hotkey: str
    tabs: dict[tuple[str, ...], GuiTab] = field(
        default_factory=dict[tuple[str, ...], GuiTab]
    )

    def add_tab(self, tab: GuiTab, replace=False) -> None:
        _logger.debug("adding tab %s", tab.name())
        if not replace and tab.name in self.tabs:
            raise ValueError(f"GUI tab {tab.name!r} is already configured")
        self.tabs[tab.name()] = tab

    @property
    def currency_general(self) -> CurrencyGeneralTab:
        return self.tabs[WellknownTabs.currency_general]  # pyright: ignore[reportReturnType]

    @property
    def currency_atlas(self) -> CurrencyAtlasTab:
        return self.tabs[WellknownTabs.currency_atlas]  # pyright: ignore[reportReturnType]

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
