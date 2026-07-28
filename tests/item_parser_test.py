from pathlib import Path

from autocraftofexile.item_parser import parse_item
from autocraftofexile.models.item import (
    ItemIdentifier,
    ItemModifier,
    ItemRequirements,
    SocketLinks,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLIPBOARD_EXAMPLE = PROJECT_ROOT / "data" / "clipboard_example.txt"


def test_parse_clipboard_example() -> None:
    item = parse_item(CLIPBOARD_EXAMPLE.read_text(encoding="utf-8"))

    assert item.ident == ItemIdentifier(
        item_class="Staves",
        rarity="Rare",
        name="Foe Call",
        base_item="Lathi",
    )
    assert item.base == "Staff"
    assert item.requirements == ItemRequirements(
        level=62,
        str=113,
        dex=0,
        int=113,
    )
    assert item.sockets == [
        SocketLinks(sockets=["W", "W", "W"]),
        SocketLinks(sockets=["W"]),
    ]
    assert item.item_level == 85
    assert item.modifiers == [
        ItemModifier(
            name="",
            slot="Implicit",
            tier=0,
            attributes=[],
            text=[]
        ),
        ItemModifier(
            name="The Elder's",
            slot="Prefix",
            tier=3,
            attributes=["Chaos", "Attack", "Ailment"],
            text=[
                "+37(37-42)% to Damage over Time Multiplier for Poison inflicted with this Weapon"]
        ),
        ItemModifier(
            name="Combatant's",
            slot="Prefix",
            tier=2,
            attributes=["Attack", "Gem"],
            text=["+1 to Level of Socketed Melee Gems"]
        ),
        ItemModifier(
            name="of Disaster",
            slot="Suffix",
            tier=4,
            attributes=["Caster", "Critical"],
            text=["95(90-104)% increased Spell Critical Strike Chance"]
        ),
        ItemModifier(
            name="of the Elder",
            slot="Suffix",
            tier=2,
            attributes=["Damage", "Attack", "Critical"],
            text=[
                "25(22-25)% increased Critical Strike Chance",
                "+50% to Critical Strike Multiplier if you haven't dealt a Critical Strike Recently",
                "(Recently refers to the past 4 seconds)",
            ]
        ),
        ItemModifier(
            name="of the Bear",
            slot="Suffix",
            tier=7,
            attributes=["Attribute"],
            text=["+19(18-22) to Strength"]
        ),
    ]
    assert item.status == ["Elder Item"]
