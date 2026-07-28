from dataclasses import dataclass


@dataclass(slots=True)
class ItemIdentifier:
    item_class: str  # Staves
    rarity: str  # Rare
    name: str  # Foe Call
    base_item: str  # Lathi


@dataclass(slots=True)
class ItemRequirements:
    level: int  # 62
    str: int  # 113
    dex: int  # 0
    int: int  # 113


@dataclass(slots=True)
class SocketLinks:
    sockets: list[str]


@dataclass(slots=True)
class ItemModifier:
    name: str  # The Elder's
    slot: str  # Implicit, Prefix, Suffix
    tier: int  # 3
    attributes: list[str]  # Chaos, Attack, Ailment
    text: list[str]  # % increased Spell Damage per 10 Strength


@dataclass(slots=True)
class Item:
    ident: ItemIdentifier
    base: str  # Staff
    requirements: ItemRequirements
    sockets: list[SocketLinks]  # W-W-W, W
    item_level: int
    modifiers: list[ItemModifier]
    status: list[str]  # Elder Item, Corrupted
