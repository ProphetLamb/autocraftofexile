from __future__ import annotations

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
    def is_valid(self) -> bool:
        required = self.selector().definition.entries
        return all(name in self.entries for name in required)

    @property
    def scroll_of_wisdom(self):
        return self.entries["scroll_of_wisdom"]

    @property
    def portal_scroll(self):
        return self.entries["portal_scroll"]

    @property
    def blacksmiths_whetstone(self):
        return self.entries["blacksmiths_whetstone"]

    @property
    def armourers_scrap(self):
        return self.entries["armourers_scrap"]

    @property
    def glassblowers_bauble(self):
        return self.entries["glassblowers_bauble"]

    @property
    def gemcutters_prism(self):
        return self.entries["gemcutters_prism"]

    @property
    def cartographers_chisel(self):
        return self.entries["cartographers_chisel"]

    @property
    def orb_of_transmutation(self):
        return self.entries["orb_of_transmutation"]

    @property
    def orb_of_alteration(self):
        return self.entries["orb_of_alteration"]

    @property
    def orb_of_annulment(self):
        return self.entries["orb_of_annulment"]

    @property
    def orb_of_chance(self):
        return self.entries["orb_of_chance"]

    @property
    def exalted_orb(self):
        return self.entries["exalted_orb"]

    @property
    def mirror_of_kalandra(self):
        return self.entries["mirror_of_kalandra"]

    @property
    def regal_orb(self):
        return self.entries["regal_orb"]

    @property
    def orb_of_alchemy(self):
        return self.entries["orb_of_alchemy"]

    @property
    def chaos_orb(self):
        return self.entries["chaos_orb"]

    @property
    def veiled_chaos_orb(self):
        return self.entries["veiled_chaos_orb"]

    @property
    def orb_of_augmentation(self):
        return self.entries["orb_of_augmentation"]

    @property
    def divine_orb(self):
        return self.entries["divine_orb"]

    @property
    def jewellers_orb(self):
        return self.entries["jewellers_orb"]

    @property
    def orb_of_fusing(self):
        return self.entries["orb_of_fusing"]

    @property
    def chromatic_orb(self):
        return self.entries["chromatic_orb"]

    @property
    def enkindling_orb(self):
        return self.entries["enkindling_orb"]

    @property
    def ancient_orb(self):
        return self.entries["ancient_orb"]

    @property
    def orb_of_binding(self):
        return self.entries["orb_of_binding"]

    @property
    def orb_of_regret(self):
        return self.entries["orb_of_regret"]

    @property
    def orb_of_unmaking(self):
        return self.entries["orb_of_unmaking"]

    @property
    def instilling_orb(self):
        return self.entries["instilling_orb"]

    @property
    def orb_of_scouring(self):
        return self.entries["orb_of_scouring"]

    @property
    def sacred_orb(self):
        return self.entries["sacred_orb"]

    @property
    def blessed_orb(self):
        return self.entries["blessed_orb"]

    @property
    def vaal_orb(self):
        return self.entries["vaal_orb"]

    @property
    def showcase(self):
        return self.entries["showcase"]
