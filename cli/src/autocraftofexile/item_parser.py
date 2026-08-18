from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import replace
from types import MappingProxyType

from .models.item import (
    Item,
    ItemIdentifier,
    ItemModifier,
    ItemProperties,
    ItemRequirements,
    SocketLinks,
)
from .models.recipe import AffixGroups

_SEPARATOR_RE = re.compile(r"^-{4,}$")
_FIELD_RE = re.compile(r"^(?P<name>[^:]+):\s*(?P<value>.*)$")
_MODIFIER_RE = re.compile(
    r"^\{\s*"
    r"(?P<slot>Implicit|Prefix|Suffix)\s+Modifier"
    r'(?:\s+"(?P<name>[^"]+)")?'
    r"(?:\s+\(Tier:\s*(?P<tier>\d+)\))?"
    r"(?:\s+[—-]\s+(?P<attributes>.*?))?"
    r"\s*\}$",
    re.IGNORECASE,
)
_PROPERTY_NAMES = {
    "Physical Damage": "physical_damage",
    "Elemental Damage": "elemental_damage",
    "Chaos Damage": "chaos_damage",
    "Critical Strike Chance": "critical_strike_chance",
    "Attacks per Second": "attacks_per_second",
    "Weapon Range": "weapon_range",
}

_logger = logging.getLogger(__name__)


class RarityItemDetails(ABC):
    rarity: str
    max_affix: AffixGroups | None = None

    @abstractmethod
    def parse_identifier(
        self, item_class: str, identity_lines: list[str]
    ) -> ItemIdentifier:
        pass


class NormalItemDetails(RarityItemDetails):
    rarity = "Normal"
    max_affix = AffixGroups(0, 0)

    def parse_identifier(self, item_class: str, identity_lines: list[str]):
        if len(identity_lines) < 1:
            raise ValueError("Expected item name after Rarity")
        return ItemIdentifier(
            item_class=item_class,
            rarity="Normal",
            name=identity_lines[0],
            base_item=identity_lines[0],
        )


class MagicItemDetails(RarityItemDetails):
    rarity = "Magic"
    max_affix = AffixGroups(1, 1)

    def parse_identifier(self, item_class: str, identity_lines: list[str]):
        if len(identity_lines) < 1:
            raise ValueError("Expected item name after Rarity")
        return ItemIdentifier(
            item_class=item_class,
            rarity="Magic",
            name=identity_lines[0],
            # Unleashed Lathi of Steadiness, Lathi of Steadiness, Unleashed Lathi
            base_item=(
                identity_lines[0][:suffix_index]
                if (suffix_index := identity_lines[0].find(" of ")) == -1
                else identity_lines[0]
            )
            .split(" ", 2)
            .pop(),
        )


class RareItemDetails(RarityItemDetails):
    rarity = "Rare"

    def parse_identifier(self, item_class: str, identity_lines: list[str]):
        if len(identity_lines) < 2:
            raise ValueError("Expected item name and base item after Rarity")
        return ItemIdentifier(
            item_class=item_class,
            rarity="Rare",
            name=identity_lines[0],
            base_item=identity_lines[1],
        )


class UniqueItemDetails(RareItemDetails):
    rarity = "Unique"

    def parse_identifier(self, item_class: str, identity_lines: list[str]):
        if len(identity_lines) < 2:
            raise ValueError("Expected item name and base item after Rarity")
        return ItemIdentifier(
            item_class=item_class,
            rarity="Unique",
            name=identity_lines[0],
            base_item=identity_lines[1],
        )


ITEM_DETAILS: tuple[RarityItemDetails, ...] = (
    NormalItemDetails(),
    MagicItemDetails(),
    RareItemDetails(),
    UniqueItemDetails(),
)
ITEM_DETAIL_BY_RARITY = MappingProxyType(
    {parser.rarity.casefold(): parser for parser in ITEM_DETAILS}
)


def parse_item(text: str) -> Item:
    _logger.debug("begin parse item text=%s", text)
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        raise ValueError("Item text is empty")

    rarity_index = _field_index(lines, "Rarity")
    identity_end = _next_separator(lines, rarity_index + 1)
    rarity = _required_field(lines, "Rarity")
    item_class = _required_field(lines, "Item Class")
    identity_lines = [
        line
        for line in lines[rarity_index + 1 : identity_end]
        if not _FIELD_RE.match(line)
    ]
    identifier_parser = ITEM_DETAIL_BY_RARITY.get(rarity.casefold())
    if identifier_parser == None:
        raise ValueError(f"Unknown rarity {rarity}")
    ident = identifier_parser.parse_identifier(item_class, identity_lines)

    base_index = identity_end + 1
    if base_index >= len(lines) or _SEPARATOR_RE.fullmatch(lines[base_index]):
        raise ValueError("Expected base category after item identifier")
    base = lines[base_index]
    properties_end = _next_separator(lines, base_index + 1)
    properties = _parse_item_properties(lines[base_index + 1 : properties_end])

    requirements = ItemRequirements(
        level=_optional_int_field(lines, "Level"),
        str=_optional_int_field(lines, "Str"),
        dex=_optional_int_field(lines, "Dex"),
        int=_optional_int_field(lines, "Int"),
    )

    sockets_text = _optional_field(lines, "Sockets")
    sockets = tuple(
        [
            SocketLinks(tuple(socket for socket in group.split("-") if socket))
            for group in sockets_text.split()
            if group
        ]
        if sockets_text
        else []
    )

    item_level = int(_required_field(lines, "Item Level"))
    modifiers = _parse_item_modifiers(lines)
    last_separator = max(
        (i for i, line in enumerate(lines) if _SEPARATOR_RE.fullmatch(line)),
        default=-1,
    )
    status = tuple(lines[last_separator + 1 :])

    item = Item(
        ident=ident,
        base=base,
        properties=properties,
        requirements=requirements,
        sockets=sockets,
        item_level=item_level,
        modifiers=modifiers,
        status=status,
    )
    _logger.debug("done parse item item=%s", repr(item))
    return item


def _parse_item_properties(lines: Iterable[str]) -> ItemProperties:
    values: dict[str, str | None] = {
        field_name: None for field_name in _PROPERTY_NAMES.values()
    }
    additional: list[str] = []
    for line in lines:
        match = _FIELD_RE.fullmatch(line)
        if match and match.group("name") in _PROPERTY_NAMES:
            values[_PROPERTY_NAMES[match.group("name")]] = match.group("value")
        else:
            additional.append(line)
    return ItemProperties(**values, additional=tuple(additional))


def _parse_item_modifiers(
    lines: Iterable[str],
) -> tuple[ItemModifier, ...]:
    modifiers: list[ItemModifier] = []
    current: ItemModifier | None = None
    current_text: list[str] = []

    def finish_current() -> None:
        nonlocal current, current_text

        if current is None:
            return

        modifiers.append(replace(current, text=tuple(current_text)))
        current = None
        current_text = []

    for line in lines:
        if _MODIFIER_RE.fullmatch(line):
            finish_current()
            current = parse_item_modifier_header(line)
        elif _SEPARATOR_RE.fullmatch(line):
            finish_current()
        elif current is not None:
            current_text.append(line)

    finish_current()
    return tuple(modifiers)


def parse_item_modifier_header(text: str) -> ItemModifier:
    match = _MODIFIER_RE.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"Invalid item modifier header: {text!r}")
    attributes_text = match.group("attributes")
    return ItemModifier(
        name=match.group("name") or "",
        slot=match.group("slot").title(),
        tier=int(match.group("tier") or 0),
        attributes=tuple(
            [value.strip() for value in attributes_text.split(",") if value.strip()]
            if attributes_text
            else []
        ),
        text=(),
    )


def _field_index(lines: Iterable[str], name: str) -> int:
    prefix = f"{name}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            return index
    raise ValueError(f"Missing required field: {name}")


def _required_field(lines: Iterable[str], name: str) -> str:
    value = _optional_field(lines, name)
    if not value:
        raise ValueError(f"Missing required field: {name}")
    return value


def _optional_field(lines: Iterable[str], name: str) -> str | None:
    prefix = f"{name}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _optional_int_field(lines: Iterable[str], name: str) -> int:
    value = _optional_field(lines, name)
    if value is None:
        return 0
    match = re.search(r"-?\d+", value)
    if match is None:
        raise ValueError(f"Invalid integer for {name}: {value!r}")
    return int(match.group())


def _next_separator(lines: list[str], start: int) -> int:
    for index in range(start, len(lines)):
        if _SEPARATOR_RE.fullmatch(lines[index]):
            return index
    raise ValueError("Missing item section separator")
