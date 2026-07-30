from __future__ import annotations

from dataclasses import dataclass, field

_SEPARATOR = "--------"


@dataclass(slots=True, frozen=True)
class ItemIdentifier:
    item_class: str
    rarity: str
    name: str
    base_item: str

    def __repr__(self) -> str:
        return "\n".join((
            f"Item Class: {self.item_class}",
            f"Rarity: {self.rarity}",
            self.name,
            self.base_item,
        ))


@dataclass(slots=True, frozen=True)
class ItemProperties:
    physical_damage: str | None = None
    elemental_damage: str | None = None
    chaos_damage: str | None = None
    critical_strike_chance: str | None = None
    attacks_per_second: str | None = None
    weapon_range: str | None = None
    additional: tuple[str, ...] = tuple()

    def __repr__(self) -> str:
        lines: list[str] = []
        if self.physical_damage is not None:
            lines.append(f"Physical Damage: {self.physical_damage}")
        if self.elemental_damage is not None:
            lines.append(f"Elemental Damage: {self.elemental_damage}")
        if self.chaos_damage is not None:
            lines.append(f"Chaos Damage: {self.chaos_damage}")
        if self.critical_strike_chance is not None:
            lines.append(
                f"Critical Strike Chance: {self.critical_strike_chance}")
        if self.attacks_per_second is not None:
            lines.append(f"Attacks per Second: {self.attacks_per_second}")
        if self.weapon_range is not None:
            lines.append(f"Weapon Range: {self.weapon_range}")
        lines.extend(self.additional)
        return "\n".join(lines)


@dataclass(slots=True, frozen=True)
class ItemRequirements:
    level: int
    str: int
    dex: int
    int: int

    def __repr__(self) -> str:
        lines = ["Requirements:"]
        if self.level:
            lines.append(f"Level: {self.level}")
        if self.str:
            lines.append(f"Str: {self.str}")
        if self.dex:
            lines.append(f"Dex: {self.dex}")
        if self.int:
            lines.append(f"Int: {self.int}")
        return "\n".join(lines)


@dataclass(slots=True, frozen=True)
class SocketLinks:
    sockets: tuple[str, ...] = tuple()

    def __repr__(self) -> str:
        return "-".join(self.sockets)


@dataclass(slots=True, frozen=True)
class ItemModifier:
    name: str
    slot: str
    tier: int
    attributes: tuple[str, ...]
    text: tuple[str, ...]

    def __repr__(self) -> str:
        parts = [f"{{ {self.slot} Modifier"]
        if self.name:
            parts.append(f' "{self.name}"')
        if self.tier > 0:
            parts.append(f" (Tier: {self.tier})")
        if self.attributes:
            parts.append(f" — {', '.join(self.attributes)}")
        parts.append(" }")
        header = "".join(parts)
        return "\n".join((header, *self.text)) if self.text else header


@dataclass(slots=True, frozen=True)
class Item:
    ident: ItemIdentifier
    base: str
    properties: ItemProperties
    requirements: ItemRequirements
    sockets: tuple[SocketLinks, ...]
    item_level: int
    modifiers: tuple[ItemModifier, ...]
    status: tuple[str, ...]

    def __repr__(self) -> str:
        property_section = "\n".join(
            part for part in (self.base, repr(self.properties)) if part
        )
        sections = [
            repr(self.ident),
            property_section,
            repr(self.requirements),
        ]

        if self.sockets:
            sections.append(
                f"Sockets: {' '.join(map(repr, self.sockets))}"
            )

        sections.append(f"Item Level: {self.item_level}")

        implicit = [
            modifier for modifier in self.modifiers
            if modifier.slot.casefold() == "implicit"
        ]
        explicit = [
            modifier for modifier in self.modifiers
            if modifier.slot.casefold() != "implicit"
        ]
        if implicit:
            sections.append("\n".join(map(repr, implicit)))
        if explicit:
            sections.append("\n".join(map(repr, explicit)))
        if self.status:
            sections.append("\n".join(self.status))

        return f"\n{_SEPARATOR}\n".join(filter(None, sections))
