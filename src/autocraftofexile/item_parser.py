from __future__ import annotations

import re

from .models.item import (
    Item,
    ItemIdentifier,
    ItemModifier,
    ItemRequirements,
    SocketLinks,
)

_SEPARATOR_RE = re.compile(r"^-{4,}$")
_FIELD_RE = re.compile(r"^(?P<name>[^:]+):\s*(?P<value>.*)$")
_MODIFIER_RE = re.compile(
    r'^\{\s*'
    r'(?P<slot>Implicit|Prefix|Suffix)\s+Modifier'
    r'(?:\s+"(?P<name>[^"]+)")?'
    r'(?:\s+\(Tier:\s*(?P<tier>\d+)\))?'
    r'(?:\s+[—-]\s+(?P<attributes>.*?))?'
    r'\s*\}$',
    re.IGNORECASE,
)


def parse_item(text: str) -> Item:
    """Parse Path of Exile clipboard item text."""
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    lines = [line for line in lines if line]

    if not lines:
        raise ValueError("Item text is empty")

    item_class = _required_field(lines, "Item Class")
    rarity = _required_field(lines, "Rarity")

    rarity_index = _field_index(lines, "Rarity")
    separator_index = _next_separator(lines, rarity_index + 1)
    identity_lines = [
        line
        for line in lines[rarity_index + 1: separator_index]
        if not _FIELD_RE.match(line)
    ]
    if len(identity_lines) < 2:
        raise ValueError("Expected item name and base item after Rarity")

    ident = ItemIdentifier(
        item_class=item_class,
        rarity=rarity,
        name=identity_lines[0],
        base_item=identity_lines[1],
    )

    base_index = separator_index + 1
    if base_index >= len(lines) or _SEPARATOR_RE.fullmatch(lines[base_index]):
        raise ValueError("Expected base category after item identifier")
    base = lines[base_index]

    requirements = ItemRequirements(
        level=_optional_int_field(lines, "Level"),
        str=_optional_int_field(lines, "Str"),
        dex=_optional_int_field(lines, "Dex"),
        int=_optional_int_field(lines, "Int"),
    )

    sockets_text = _optional_field(lines, "Sockets")
    sockets = []
    if sockets_text:
        sockets = [
            SocketLinks(
                sockets=[socket for socket in group.split("-") if socket])
            for group in sockets_text.split()
            if group
        ]

    item_level = int(_required_field(lines, "Item Level"))
    modifiers = _parse_item_modifiers(lines)

    last_separator = max(
        (
            index
            for index, line in enumerate(lines)
            if _SEPARATOR_RE.fullmatch(line)
        ),
        default=-1,
    )
    status = [
        line
        for line in lines[last_separator + 1:]
        if not _SEPARATOR_RE.fullmatch(line)
    ]

    return Item(
        ident=ident,
        base=base,
        requirements=requirements,
        sockets=sockets,
        item_level=item_level,
        modifiers=modifiers,
        status=status,
    )


def _parse_item_modifiers(lines: list[str]) -> list[ItemModifier]:
    """Parse modifier headers and associate their following value lines.

    A modifier's text starts immediately after its ``{ ... Modifier ... }``
    header and ends before the next modifier header or section separator.
    """
    modifiers: list[ItemModifier] = []
    current: ItemModifier | None = None

    for line in lines:
        if _MODIFIER_RE.fullmatch(line):
            current = parse_item_modifier_header(line)
            modifiers.append(current)
            continue

        if _SEPARATOR_RE.fullmatch(line):
            current = None
            continue

        if current is not None:
            current.text.append(line)

    return modifiers


def parse_item_modifier_header(text: str) -> ItemModifier:
    """Parse one modifier header, including its surrounding braces."""
    match = _MODIFIER_RE.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"Invalid item modifier header: {text!r}")

    slot = match.group("slot").title()
    name = match.group("name") or ""
    tier = int(match.group("tier") or 0)
    attributes_text = match.group("attributes")
    attributes = (
        [value.strip() for value in attributes_text.split(",") if value.strip()]
        if attributes_text
        else []
    )

    return ItemModifier(
        name=name,
        slot=slot,
        tier=tier,
        attributes=attributes,
        text=[],
    )


def _field_index(lines: list[str], name: str) -> int:
    prefix = f"{name}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            return index
    raise ValueError(f"Missing required field: {name}")


def _required_field(lines: list[str], name: str) -> str:
    value = _optional_field(lines, name)
    if value is None or not value:
        raise ValueError(f"Missing required field: {name}")
    return value


def _optional_field(lines: list[str], name: str) -> str | None:
    prefix = f"{name}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def _optional_int_field(lines: list[str], name: str) -> int:
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
