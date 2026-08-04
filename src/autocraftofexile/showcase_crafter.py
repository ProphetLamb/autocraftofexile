from __future__ import annotations

import logging
import time

import pyperclip

from .cancellation_token import CancellationToken
from .crafting import (
    DEFAULT_CRAFTER_METHODS,
    Crafter,
    CrafterMethod,
    CraftingOptions,
    CraftStepResult,
    find_crafter_method,
)
from .item_matcher import ItemMatcher, ItemMatchResult
from .item_parser import parse_item
from .models.gui_config import Coordinates
from .models.item import Item
from .rich_recipe import StepStatus

_logger = logging.getLogger(__name__)


class ShowcaseCrafter(Crafter):
    step_index: int = 0
    crafter_methods: tuple[CrafterMethod, ...]
    _current_item: Item | None
    _cached_text: str | None
    _cached_item: Item | None
    _cached_coords: Coordinates | None

    def __init__(
        self,
        options: CraftingOptions,
        stopping_token: CancellationToken,
        *,
        step_index: int = 0,
        crafter_methods: tuple[CrafterMethod, ...] | None = None,
    ):
        self.options = options
        self.step_index = step_index
        self.dragged_currency = None
        self.crafter_methods = crafter_methods or DEFAULT_CRAFTER_METHODS
        self._current_item = None
        self._cached_text = None
        self._cached_item = None
        self._cached_coords = None
        self.stopping_token = stopping_token
        self._stats = {}

    @property
    def crafting_target(self) -> Coordinates:
        return self.options.config.showcase

    def execute(self):
        _logger.debug("begin executing step %d", self.step_index)
        try:
            self._ensure_window_focus()
        except:
            self.options.rich_recipe.update("[red]Failed to focus Path of Exile[/red]")
            raise
        try:
            item_changed = self._invoke_step()
            if item_changed:
                self._ensure_item_changed()
        except:
            self.options.rich_recipe.update(
                f"[red]Failed to invoke crafting step {self.step_index + 1}[/red]"
            )
            raise
        item: Item
        try:
            item = self._get_item()
        except:
            self.options.rich_recipe.update(
                "[red]Invalid item copied by CTRL+ALT+C[/red]"
            )
            raise
        result: CraftStepResult
        try:
            result = self._evaluate_item(item)
        except:
            self.options.rich_recipe.update(
                f"[red]Failed to evaluate crafting step {self.step_index + 1}[/red]"
            )
            raise
        _logger.debug("done executing step")
        return result

    def _get_item(self) -> Item:
        _logger.debug("begin get item")
        self.stopping_token.throw_if_cancelled()
        if self._current_item:
            _logger.debug("end get item using cached item")
            return self._current_item

        showcase = self.options.config.showcase

        self.move_to(showcase)
        self.hotkey("ctrl", "alt", "c")
        time.sleep(self._duration(1 / self.options.speed))

        text = pyperclip.paste()

        if not text.strip():
            raise ValueError("The clipboard is empty after copying the showcase item")
        pyperclip.copy("")

        item = self._cached_item
        if item and self._cached_text == text:
            _logger.debug(
                "item remain unchanged by the crafting method texts are equal %s\n\n%s",
                self._cached_text,
                text,
            )
            self._current_item = item
            return item
        item = parse_item(text)
        self._cached_text = text
        self._cached_item = item
        self._current_item = item
        _logger.debug("done get item")
        return item

    def _invoke_step(self):
        _logger.debug("begin invoke step %d", self.step_index)
        if not 0 <= self.step_index < len(self.options.recipe.config):
            raise IndexError(f"Recipe step index out of range: {self.step_index}")
        step = self.options.recipe.config[self.step_index]
        self.stopping_token.throw_if_cancelled()
        self.options.rich_recipe.status[step] = StepStatus(
            active=True,
        )

        crafter_method = find_crafter_method(self.crafter_methods, step.method)
        if crafter_method is None:
            raise ValueError(
                f"Unsupported crafting method at step {self.step_index}: "
                f"{step.method!r}"
            )

        item_changed = crafter_method.invoke(self)
        self.options.rich_recipe.inc_stat(step.method)

        _logger.debug(
            "done invoke step %d using method %r",
            self.step_index,
            repr(step.method),
        )
        return item_changed

    def _ensure_item_changed(self):
        self._current_item = None
        cached_item = self._cached_item
        item = self._get_item()
        if cached_item == item:
            message = "Crafting method unexpectedly left the item unchanged "
            _logger.warning(message)
            self.options.rich_recipe.update(append=f"[orange]{message}[/orange]")
            raise ValueError(message)
        return item

    def _evaluate_item(self, item: Item) -> CraftStepResult:
        _logger.debug("begin evaluating item %s", repr(item))
        self.stopping_token.throw_if_cancelled()

        step = self._current_step
        if step.autopass:
            _logger.debug("done evaluating step autopass")
            return self._goto_step(
                ItemMatchResult(True), step.actions.win, step.actions.win_route
            )
        matcher = ItemMatcher(step, self.options.recipe.data, self.options.poecd)
        result = matcher.evaluate(item)

        _logger.debug("done evaluating item %s", repr(result))
        if result.success:
            return self._goto_step(result, step.actions.win, step.actions.win_route)
        else:
            return self._goto_step(result, step.actions.fail, step.actions.fail_route)

    @property
    def _current_step(self):
        return self.options.recipe.config[self.step_index]

    def _goto_step(
        self, match: ItemMatchResult, action: str, route: str | None
    ) -> CraftStepResult:
        _logger.debug("begin goto step action=%s route=%s", action, route)
        self.options.rich_recipe.status[self._current_step] = StepStatus(
            active=False,
            result=match,
            status_info=f"[cyan]Goto {action} {route or ''}[/cyan]",
        )

        action = action.casefold()
        if action == "loop":
            pass
        elif action == "restart":
            self.step_index = 0
        elif action == "next":
            self.step_index += 1
        elif action == "end":
            self.step_index = len(self.options.recipe.config)
        elif action == "step":
            if route == None:
                raise ValueError(
                    "Recipe step with the `step` action must specify a route"
                )
            self.step_index = int(route) - 1
        else:
            raise ValueError(f"Unknown action {action}")

        done = self.step_index >= len(self.options.recipe.config)
        if not done:
            self.options.rich_recipe.status[self._current_step] = StepStatus(
                active=True,
            )
        self.options.rich_recipe.update(
            append=":sparkles: [green]Done[/green]" if done else None
        )
        _logger.debug("done goto step")
        return CraftStepResult(match, done)
