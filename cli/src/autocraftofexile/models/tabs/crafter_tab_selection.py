from __future__ import annotations

import time

from .gui_tab import GuiTab


class CrafterTabSelectionMixin:
    """Selects currency subtabs and caches the tab selected by the crafter."""

    _selected_tab: tuple[str, ...] | None

    def ensure_tab_selected(self, tab: GuiTab) -> None:
        tab_name = tab.name()
        if self._selected_tab == tab_name:
            return

        header = tab.tab_header
        if header is None:
            raise ValueError(
                f"Tab {tab_name!r} has no detected tab-header coordinate"
            )

        # Currency acquisition may keep Shift held for repeated application.
        # Release it before clicking UI chrome, otherwise the header click can
        # be interpreted as part of the currency interaction.
        if self.dragged_currency is not None:  # type: ignore[attr-defined]
            self.key_up("shift")  # type: ignore[attr-defined]
            self.dragged_currency = None  # type: ignore[attr-defined]

        self.move_to(header)  # type: ignore[attr-defined]
        self.left_click()  # type: ignore[attr-defined]

        # Give Path of Exile a short frame-independent UI settling period before
        # moving to a slot in the newly selected tab.
        time.sleep(self._duration(0.12))  # type: ignore[attr-defined]
        self._selected_tab = tab_name

    def forget_selected_tab(self) -> None:
        """Invalidate the cache when external input may have switched tabs."""
        self._selected_tab = None
