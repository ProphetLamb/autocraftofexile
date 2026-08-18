from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar

from .gui_tab import GuiTab
from .tab_overlay_selector import TabOverlaySelector


@dataclass(slots=True)
class CurrencyGeneralTab(GuiTab):
    """The General subtab of the currency stash tab."""

    NAME: ClassVar[tuple[str, ...]] = ("currency", "general")
    OVERLAY_DEFINITION_PACKAGE: ClassVar[str] = "autocraftofexile.models.tabs"
    OVERLAY_DEFINITION_RESOURCE: ClassVar[str] = "currency_general_tab.json"

    @classmethod
    def name(cls) -> tuple[str, ...]:
        return cls.NAME

    @classmethod
    def selector(cls) -> TabOverlaySelector:
        return TabOverlaySelector.from_resource(
            cls.OVERLAY_DEFINITION_PACKAGE,
            cls.OVERLAY_DEFINITION_RESOURCE,
        )

    @property
    def missing_items(self) -> Iterable[str]:
        required = self.selector().definition.items
        return [
            item.name
            for item in required
            if item.name and not (item.name in self.items)
        ]

    @property
    def scroll_of_wisdom(self):
        return self.items["scroll_of_wisdom"]

    @property
    def portal_scroll(self):
        return self.items["portal_scroll"]

    @property
    def blacksmiths_whetstone(self):
        return self.items["blacksmiths_whetstone"]

    @property
    def armourers_scrap(self):
        return self.items["armourers_scrap"]

    @property
    def glassblowers_bauble(self):
        return self.items["glassblowers_bauble"]

    @property
    def gemcutters_prism(self):
        return self.items["gemcutters_prism"]

    @property
    def cartographers_chisel(self):
        return self.items["cartographers_chisel"]

    @property
    def orb_of_transmutation(self):
        return self.items["orb_of_transmutation"]

    @property
    def orb_of_alteration(self):
        return self.items["orb_of_alteration"]

    @property
    def orb_of_annulment(self):
        return self.items["orb_of_annulment"]

    @property
    def orb_of_chance(self):
        return self.items["orb_of_chance"]

    @property
    def exalted_orb(self):
        return self.items["exalted_orb"]

    @property
    def mirror_of_kalandra(self):
        return self.items["mirror_of_kalandra"]

    @property
    def regal_orb(self):
        return self.items["regal_orb"]

    @property
    def orb_of_alchemy(self):
        return self.items["orb_of_alchemy"]

    @property
    def chaos_orb(self):
        return self.items["chaos_orb"]

    @property
    def veiled_chaos_orb(self):
        return self.items["veiled_chaos_orb"]

    @property
    def orb_of_augmentation(self):
        return self.items["orb_of_augmentation"]

    @property
    def divine_orb(self):
        return self.items["divine_orb"]

    @property
    def jewellers_orb(self):
        return self.items["jewellers_orb"]

    @property
    def orb_of_fusing(self):
        return self.items["orb_of_fusing"]

    @property
    def chromatic_orb(self):
        return self.items["chromatic_orb"]

    @property
    def enkindling_orb(self):
        return self.items["enkindling_orb"]

    @property
    def ancient_orb(self):
        return self.items["ancient_orb"]

    @property
    def orb_of_binding(self):
        return self.items["orb_of_binding"]

    @property
    def orb_of_regret(self):
        return self.items["orb_of_regret"]

    @property
    def orb_of_unmaking(self):
        return self.items["orb_of_unmaking"]

    @property
    def instilling_orb(self):
        return self.items["instilling_orb"]

    @property
    def orb_of_scouring(self):
        return self.items["orb_of_scouring"]

    @property
    def sacred_orb(self):
        return self.items["sacred_orb"]

    @property
    def blessed_orb(self):
        return self.items["blessed_orb"]

    @property
    def vaal_orb(self):
        return self.items["vaal_orb"]

    @property
    def showcase(self):
        return self.items["showcase"]
