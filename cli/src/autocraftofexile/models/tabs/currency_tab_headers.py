from __future__ import annotations

from collections.abc import Mapping

from ..coordinates import Coordinates

GENERAL_TAB_HEADER = "general_tab_header"
ATLAS_TAB_HEADER = "atlas_tab_header"
LEAGUE_TAB_HEADER = "league_tab_header"

TAB_HEADER_ENTRY: Mapping[tuple[str, ...], str] = {
    ("currency", "general"): GENERAL_TAB_HEADER,
    ("currency", "atlas"): ATLAS_TAB_HEADER,
    ("currency", "league"): LEAGUE_TAB_HEADER,
}


def tab_header_entry(tab_name: tuple[str, ...]) -> str:
    """Return the overlay entry used to activate a currency subtab."""
    try:
        return TAB_HEADER_ENTRY[tab_name]
    except KeyError as error:
        raise ValueError(
            f"No currency-tab header is registered for {tab_name!r}"
        ) from error


def own_tab_header(
    tab_name: tuple[str, ...],
    items: Mapping[str, Coordinates],
) -> Coordinates:
    """Resolve the activation button for a configured currency subtab."""
    entry = tab_header_entry(tab_name)
    try:
        return items[entry]
    except KeyError as error:
        raise ValueError(
            f"Currency tab {tab_name!r} is missing required header entry {entry!r}"
        ) from error
