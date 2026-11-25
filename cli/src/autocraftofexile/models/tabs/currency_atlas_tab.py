from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar

from ..coordinates import Coordinates
from .gui_tab import GuiTab
from .tab_overlay_selector import TabOverlaySelector


@dataclass(slots=True)
class CurrencyAtlasTab(GuiTab):
    """The Atlas subtab of the currency stash tab."""

    NAME: ClassVar[tuple[str, ...]] = ("currency", "atlas")
    OVERLAY_DEFINITION_PACKAGE: ClassVar[str] = (
        "autocraftofexile.models.tabs"
    )
    OVERLAY_DEFINITION_RESOURCE: ClassVar[str] = "currency_atlas_tab.json"

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
        return [
            item.name
            for item in self.selector().definition.items
            if not item.is_placeholder and item.name not in self.items
        ]

    def _item(self, name: str) -> Coordinates:
        return self.items[name]

    @property
    def wild_lifeforce(self) -> Coordinates:
        return self._item("wild_lifeforce")

    @property
    def vivid_lifeforce(self) -> Coordinates:
        return self._item("vivid_lifeforce")

    @property
    def primal_lifeforce(self) -> Coordinates:
        return self._item("primal_lifeforce")

    @property
    def sacred_lifeforce(self) -> Coordinates:
        return self._item("sacred_lifeforce")

    @property
    def mavens_chisel_of_procurement(self) -> Coordinates:
        return self._item("mavens_chisel_of_procurement")

    @property
    def mavens_chisel_of_proliferation(self) -> Coordinates:
        return self._item("mavens_chisel_of_proliferation")

    @property
    def hunters_exalted_orb(self) -> Coordinates:
        return self._item("hunters_exalted_orb")

    @property
    def crusaders_exalted_orb(self) -> Coordinates:
        return self._item("crusaders_exalted_orb")

    @property
    def shapers_exalted_orb(self) -> Coordinates:
        return self._item("shapers_exalted_orb")

    @property
    def orb_of_remembrance(self) -> Coordinates:
        return self._item("orb_of_remembrance")

    @property
    def orb_of_intention(self) -> Coordinates:
        return self._item("orb_of_intention")

    @property
    def orb_of_unravelling(self) -> Coordinates:
        return self._item("orb_of_unravelling")

    @property
    def mavens_chisel_of_threads(self) -> Coordinates:
        return self._item("mavens_chisel_of_threads")

    @property
    def mavens_chisel_of_divination(self) -> Coordinates:
        return self._item("mavens_chisel_of_divination")

    @property
    def redeemers_exalted_orb(self) -> Coordinates:
        return self._item("redeemers_exalted_orb")

    @property
    def warlords_exalted_orb(self) -> Coordinates:
        return self._item("warlords_exalted_orb")

    @property
    def elders_exalted_orb(self) -> Coordinates:
        return self._item("elders_exalted_orb")

    @property
    def divine_vessel(self) -> Coordinates:
        return self._item("divine_vessel")

    @property
    def mavens_chisel_of_avarice(self) -> Coordinates:
        return self._item("mavens_chisel_of_avarice")

    @property
    def orb_of_dominance(self) -> Coordinates:
        return self._item("orb_of_dominance")

    @property
    def awakeners_orb(self) -> Coordinates:
        return self._item("awakeners_orb")

    @property
    def eldritch_chaos_orb(self) -> Coordinates:
        return self._item("eldritch_chaos_orb")

    @property
    def eldritch_exalted_orb(self) -> Coordinates:
        return self._item("eldritch_exalted_orb")

    @property
    def eldritch_orb_of_annulment(self) -> Coordinates:
        return self._item("eldritch_orb_of_annulment")

    @property
    def orb_of_conflict(self) -> Coordinates:
        return self._item("orb_of_conflict")

    @property
    def lesser_eldritch_ember(self) -> Coordinates:
        return self._item("lesser_eldritch_ember")

    @property
    def greater_eldritch_ember(self) -> Coordinates:
        return self._item("greater_eldritch_ember")

    @property
    def grand_eldritch_ember(self) -> Coordinates:
        return self._item("grand_eldritch_ember")

    @property
    def exceptional_eldritch_ember(self) -> Coordinates:
        return self._item("exceptional_eldritch_ember")

    @property
    def lesser_eldritch_ichor(self) -> Coordinates:
        return self._item("lesser_eldritch_ichor")

    @property
    def greater_eldritch_ichor(self) -> Coordinates:
        return self._item("greater_eldritch_ichor")

    @property
    def grand_eldritch_ichor(self) -> Coordinates:
        return self._item("grand_eldritch_ichor")

    @property
    def exceptional_eldritch_ichor(self) -> Coordinates:
        return self._item("exceptional_eldritch_ichor")

    @property
    def showcase(self) -> Coordinates:
        return self._item("showcase")
