from __future__ import annotations

import json
import logging
import time
from os import PathLike

import keyboard
from rich import print

from .models.gui_config import GuiConfig, WellknownTabs
from .models.tabs.currency_atlas_tab import CurrencyAtlasTab
from .models.tabs.currency_general_tab import CurrencyGeneralTab
from .models.tabs.gui_tab import GuiTab
from .models.tabs.tab_overlay_selector import (
    OverlaySelection,
    TabOverlayDefinition,
)

_logger = logging.getLogger(__name__)


def prompt_hotkey(name: str) -> str:
    _logger.debug("begin prompting %s hotkey", name)
    time.sleep(0.1)
    print(f"\nPress the [bright_white]{name}[/bright_white] hotkey.")
    hotkey = keyboard.read_hotkey(suppress=False)
    print(f"[bright_white]{name}[/bright_white] hotkey: [cyan]{hotkey}[/cyan]")
    _logger.debug("done prompting %s hotkey", name)
    return hotkey


def _prompt_missing_config(config: GuiConfig) -> bool:
    _logger.debug("begin prompt missing config")
    changed = False
    if not config.start_hotkey:
        print("Missing [cyan]start[/cyan] hotkey")
        config.start_hotkey = prompt_hotkey("start")
        changed = True
    if not config.stop_hotkey:
        print("Missing [cyan]stop[/cyan] hotkey")
        config.stop_hotkey = prompt_hotkey("stop")
        changed = True
    for tab in config.tabs.values():
        if not tab.tab_header:
            print(
                f"Invalid [cyan]{tab.name()!r}[/cyan] tab configuration\n"
                "Missing tab header"
            )
        missing_items = tab.missing_items
        if missing_items:
            print(
                f"Invalid [cyan]{tab.name()!r}[/cyan] tab configuration\n"
                f"Missing items: {', '.join(f'[bright_white]{x}[/bright_white]' for x in missing_items)}"
            )
        if not tab.tab_header or missing_items:
            tab.detect(
                preserve_items=not missing_items,
                preserve_tab_header=bool(tab.tab_header),
            )
            changed = True
    if not WellknownTabs.currency_general in config.tabs:
        tab = CurrencyGeneralTab()
        tab.detect()
        config.add_tab(tab)
        changed = True
    _logger.debug("done prompt missing config, changed=%s", changed)
    return changed


def _fit_axis(values: list[tuple[float, int]]) -> tuple[float, float]:
    """Fit ``screen = offset + normalized * extent`` for one axis.

    A least-squares fit over all configured entries absorbs the one-pixel
    rounding errors introduced when the original overlay selection was mapped.
    """
    if len(values) < 2:
        raise ValueError("At least two coordinates are required to infer an axis")

    count = len(values)
    normalized_mean = sum(normalized for normalized, _ in values) / count
    screen_mean = sum(screen for _, screen in values) / count
    variance = sum((normalized - normalized_mean) ** 2 for normalized, _ in values)
    if variance <= 1e-12:
        raise ValueError("Cannot infer an axis from collinear overlay entries")

    extent = (
        sum(
            (normalized - normalized_mean) * (screen - screen_mean)
            for normalized, screen in values
        )
        / variance
    )
    offset = screen_mean - extent * normalized_mean
    return offset, extent


def _infer_selection(
    tab: GuiTab,
    definition: TabOverlayDefinition,
) -> OverlaySelection:
    """Reconstruct the overlay rectangle used to configure ``tab``."""
    samples = [
        (item.center, tab.items[item.name])
        for item in definition.items
        if not item.is_placeholder and item.name in tab.items
    ]
    if len(samples) < 2:
        raise ValueError(
            f"Cannot infer the selection for {tab.name()!r}: "
            "fewer than two configured overlay entries are available"
        )

    left, width = _fit_axis(
        [(center[0], coordinates.x) for center, coordinates in samples]
    )
    top, height = _fit_axis(
        [(center[1], coordinates.y) for center, coordinates in samples]
    )
    if width <= 0 or height <= 0:
        raise ValueError(
            f"Invalid inferred selection for {tab.name()!r}: {width:.2f} x {height:.2f}"
        )

    rounded_left = round(left)
    rounded_top = round(top)
    return OverlaySelection(
        left=rounded_left,
        top=rounded_top,
        right=rounded_left + round(width),
        bottom=rounded_top + round(height),
    )


def _configure_atlas_from_general(config: GuiConfig) -> bool:
    """Map the General overlay selection to Atlas without another prompt.

    Returns ``True`` only when the Atlas configuration was added or changed.
    """
    general_tab = config.tabs.get(WellknownTabs.currency_general)
    if general_tab is None:
        return False
    if not isinstance(general_tab, CurrencyGeneralTab):
        raise TypeError(
            f"Expected CurrencyGeneralTab, got {type(general_tab).__name__}"
        )

    general_definition = general_tab.selector().definition
    atlas_definition = CurrencyAtlasTab.selector().definition
    selection = _infer_selection(general_tab, general_definition)

    atlas_tab = CurrencyAtlasTab(
        items=atlas_definition.map_selection(selection),
    )
    atlas_tab.tab_header = atlas_tab.items.get("atlas_tab_header")
    if atlas_tab.tab_header is None:
        raise ValueError("The Atlas overlay definition has no 'atlas_tab_header' entry")

    existing = config.tabs.get(WellknownTabs.currency_atlas)
    if (
        existing is not None
        and existing.items == atlas_tab.items
        and existing.tab_header == atlas_tab.tab_header
    ):
        return False
    config.add_tab(atlas_tab, replace=True)
    _logger.info(
        "Configured %s from the %s overlay selection",
        CurrencyAtlasTab.name(),
        CurrencyGeneralTab.name(),
    )
    return True


def _write_gui_config(
    file: PathLike[str] | str,
    config: GuiConfig,
) -> None:
    with open(file, "w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2)


def load_gui_config(file: PathLike[str] | str) -> GuiConfig:
    data: object = None
    try:
        with open(file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        _logger.debug("GUI config does not exist yet: %s", file)
    except Exception:
        # A malformed or unreadable file falls back to interactive recovery,
        # while retaining the original exception in the log.
        _logger.exception("Failed to load gui config from %s", file)

    config = GuiConfig.from_dict(data if isinstance(data, dict) else {})

    changed = _prompt_missing_config(config)
    try:
        changed = _configure_atlas_from_general(config) or changed
    except Exception:
        _logger.exception(
            "Failed to derive the Atlas tab from the General tab selection"
        )
        raise

    if changed:
        _write_gui_config(file, config)
        _logger.debug("wrote GUI config to %s", file)

    print(
        "Successfully loaded gui config\n"
        f" Start hotkey [cyan]{config.start_hotkey}[/cyan]\n"
        f" Stop hotkey [cyan]{config.stop_hotkey}[/cyan]\n"
    )
    return config
