from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar

from ..coordinates import Coordinates
from .gui_tab import GuiTab
from .tab_overlay_selector import TabOverlaySelector


@dataclass(slots=True)
class CurrencyGeneralTab(GuiTab):
    """The General subtab of the currency stash tab."""

    NAME: ClassVar[tuple[str, ...]] = ("currency", "general")
    OVERLAY_DEFINITION_PACKAGE: ClassVar[str] = (
        "autocraftofexile.models.tabs"
    )
    OVERLAY_DEFINITION_RESOURCE: ClassVar[str] = (
        "currency_general_tab.json"
    )

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
        """Configured currency entries that are currently missing.

        Visual placeholders are alignment aids and are not configuration
        requirements.
        """
        required = self.selector().definition.items
        return [
            item.name
            for item in required
            if not item.is_placeholder and item.name not in self.items
        ]

    def _item(self, name: str) -> Coordinates:
        return self.items[name]

    @property
    def scroll_of_wisdom(self) -> Coordinates:
        return self._item("scroll_of_wisdom")

    @property
    def portal_scroll(self) -> Coordinates:
        return self._item("portal_scroll")

    @property
    def hinekora_lock(self) -> Coordinates:
        return self._item("hinekora_lock")

    @property
    def mirror_of_kalandra(self) -> Coordinates:
        return self._item("mirror_of_kalandra")

    @property
    def blacksmiths_whetstone(self) -> Coordinates:
        return self._item("blacksmiths_whetstone")

    @property
    def armourers_scrap(self) -> Coordinates:
        return self._item("armourers_scrap")

    @property
    def glassblowers_bauble(self) -> Coordinates:
        return self._item("glassblowers_bauble")

    @property
    def gemcutters_prism(self) -> Coordinates:
        return self._item("gemcutters_prism")

    @property
    def orb_of_transmutation(self) -> Coordinates:
        return self._item("orb_of_transmutation")

    @property
    def orb_of_alteration(self) -> Coordinates:
        return self._item("orb_of_alteration")

    @property
    def orb_of_augmentation(self) -> Coordinates:
        return self._item("orb_of_augmentation")

    @property
    def divine_orb(self) -> Coordinates:
        return self._item("divine_orb")

    @property
    def mirror_shard(self) -> Coordinates:
        return self._item("mirror_shard")

    @property
    def orb_of_alchemy(self) -> Coordinates:
        return self._item("orb_of_alchemy")

    @property
    def chaos_orb(self) -> Coordinates:
        return self._item("chaos_orb")

    @property
    def blessed_orb(self) -> Coordinates:
        return self._item("blessed_orb")

    @property
    def sacred_orb(self) -> Coordinates:
        return self._item("sacred_orb")

    @property
    def regal_orb(self) -> Coordinates:
        return self._item("regal_orb")

    @property
    def orb_of_annulment(self) -> Coordinates:
        return self._item("orb_of_annulment")

    @property
    def exalted_orb(self) -> Coordinates:
        return self._item("exalted_orb")

    @property
    def jewellers_orb(self) -> Coordinates:
        return self._item("jewellers_orb")

    @property
    def orb_of_fusing(self) -> Coordinates:
        return self._item("orb_of_fusing")

    @property
    def chromatic_orb(self) -> Coordinates:
        return self._item("chromatic_orb")

    @property
    def fracturing_orb(self) -> Coordinates:
        return self._item("fracturing_orb")

    @property
    def instilling_orb(self) -> Coordinates:
        return self._item("instilling_orb")

    @property
    def enkindling_orb(self) -> Coordinates:
        return self._item("enkindling_orb")

    @property
    def orb_of_scouring(self) -> Coordinates:
        return self._item("orb_of_scouring")

    @property
    def orb_of_regret(self) -> Coordinates:
        return self._item("orb_of_regret")

    @property
    def orb_of_unmaking(self) -> Coordinates:
        return self._item("orb_of_unmaking")

    @property
    def fracturing_shard(self) -> Coordinates:
        return self._item("fracturing_shard")

    @property
    def ancient_orb(self) -> Coordinates:
        return self._item("ancient_orb")

    @property
    def orb_of_chance(self) -> Coordinates:
        return self._item("orb_of_chance")

    @property
    def stacked_deck(self) -> Coordinates:
        return self._item("stacked_deck")

    @property
    def vaal_orb(self) -> Coordinates:
        return self._item("vaal_orb")

    @property
    def mist(self) -> Coordinates:
        return self._item("mist")

    @property
    def showcase(self) -> Coordinates:
        return self._item("showcase")
