from __future__ import annotations

import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

import keyboard
import pyautogui
import pyperclip

from .item_matcher import ItemMatcher, ItemMatchResult
from .item_parser import parse_item
from .models.gui_config import Coordinates, GuiConfig
from .models.item import Item
from .models.poecd import PoeCd
from .models.recipe import Recipe


class CraftingWorker:
    stop_event: threading.Event
    thread: threading.Thread | None
    config: GuiConfig
    recipe: Recipe
    poecd: PoeCd

    def __init__(self, config: GuiConfig, recipe: Recipe, poecd: PoeCd):
        self.stop_event = threading.Event()
        self.thread = None
        self.config = config
        self.recipe = recipe
        self.poecd = poecd

    def run(self):
        keyboard.add_hotkey(
            self.config.start_hotkey,
            self._start
        )

        keyboard.add_hotkey(
            self.config.stop_hotkey,
            self._stop
        )

        self._get_thread().join()

    def _is_stopped(self) -> bool:
        return self.stop_event.is_set()

    def _start(self):
        if self._is_stopped():
            return
        self._get_thread().start()

    def _stop(self):
        t = self.thread
        if t and t.is_alive():
            self.stop_event.set()

    def _get_thread(self):
        t = self.thread
        if t and t.is_alive():
            return t
        t = threading.Thread(
            target=self._main,
            daemon=True
        )
        self.thread = t
        return t

    def _main(self):
        try:
            crafter = Crafter(self.config, self.recipe, self.poecd, 0)
            while not self._is_stopped():
                logging.info(f"Crafting step {crafter.step_index}")
                crafter.invoke_step()
                item = crafter.get_item()
                result = crafter.evaluate_step(item)
                if result.done:
                    self._stop()
                    return
        finally:
            self.thread = None
            self.stop_event.clear()


@dataclass(slots=True, frozen=True)
class CraftStepResult:
    match: ItemMatchResult
    done: bool


@dataclass(slots=True, frozen=True)
class CurrencyMethodDefinition:
    method: tuple[str, ...]
    coord_field: str


CURRENCY_METHODS: tuple[CurrencyMethodDefinition, ...] = (
    CurrencyMethodDefinition(
        method=("currency", "transmute"),
        coord_field="transmute",
    ),
    CurrencyMethodDefinition(
        method=("currency", "augmentation", "augmentation_normal"),
        coord_field="augment",
    ),
    CurrencyMethodDefinition(
        method=("currency", "alteration"),
        coord_field="alteration",
    ),
    CurrencyMethodDefinition(
        method=("currency", "regal", "regal_normal"),
        coord_field="regal",
    ),
    CurrencyMethodDefinition(
        method=("currency", "alchemy"),
        coord_field="alchemy",
    ),
    CurrencyMethodDefinition(
        method=("currency", "chaos"),
        coord_field="chaos",
    ),
    CurrencyMethodDefinition(
        method=("currency", "exalted", "exalted_normal"),
        coord_field="exalt",
    ),
    CurrencyMethodDefinition(
        method=("currency", "scour"),
        coord_field="scour",
    ),
    CurrencyMethodDefinition(
        method=("currency", "annul"),
        coord_field="annul",
    ),
)

CURRENCY_METHOD_BY_SIGNATURE: dict[
    tuple[str, ...], CurrencyMethodDefinition
] = {
    definition.method: definition
    for definition in CURRENCY_METHODS
}


class CrafterMethod(ABC):
    method: tuple[str, ...]

    @abstractmethod
    def invoke(self, crafter: Crafter):
        pass


class CrafterMethodCheck(CrafterMethod):
    method = tuple("check")

    def invoke(self, crafter: Crafter):
        del crafter
        pass


class CrafterMethodCurrency(CrafterMethod):
    definition: CurrencyMethodDefinition

    def __init__(self, definition: CurrencyMethodDefinition) -> None:
        super().__init__()
        self.definition = definition
        self.method = _normalize_method(
            definition.method)

    def invoke(self, crafter: Crafter):
        coords = self._get_currency_coordinates(crafter.config)
        showcase = crafter.config.showcase
        pyautogui.moveTo(coords.x, coords.y,
                         duration=crafter.duration(0.14))
        pyautogui.rightClick(duration=crafter.duration(0.015))
        pyautogui.moveTo(showcase.x, showcase.y,
                         duration=crafter.duration(0.14))
        pyautogui.leftClick(duration=crafter.duration(0.015))

    def _get_currency_coordinates(
        self,
        config: GuiConfig,
    ) -> Coordinates:
        definition = CURRENCY_METHOD_BY_SIGNATURE.get(self.method)

        if definition is None:
            raise ValueError(f"Unsupported currency method: {self.method!r}")

        coordinate = getattr(config, definition.coord_field, None)
        if coordinate is None:
            raise ValueError(
                f"GuiConfig has no {definition.coord_field!r} coordinate "
                f"for method {self.method!r}"
            )

        return coordinate


CRAFTER_METHODS: tuple[CrafterMethod, ...] = (
    CrafterMethodCheck(),
    *[CrafterMethodCurrency(method) for method in CURRENCY_METHODS]
)


class Crafter:
    config: GuiConfig
    recipe: Recipe
    poecd: PoeCd
    step_index: int = 0

    def __init__(self, config: GuiConfig, recipe: Recipe, poecd: PoeCd, step_index: int):
        self.config = config
        self.recipe = recipe
        self.poecd = poecd
        self.step_index = step_index

    def duration(self, duration: float) -> float:
        return random.uniform(duration*0.85, duration*1.15)

    def get_item(self) -> Item:
        showcase = self.config.showcase

        pyautogui.moveTo(
            showcase.x,
            showcase.y,
            duration=self.duration(0.13),
        )
        pyautogui.hotkey("ctrl", "alt", "c")

        time.sleep(self.duration(0.07))

        text = pyperclip.paste()

        if not text.strip():
            raise ValueError(
                "The clipboard is empty after copying the showcase item"
            )

        return parse_item(text)

    def invoke_step(self) -> None:
        logging.debug("begin invoke step %d", self.step_index)

        if not 0 <= self.step_index < len(self.recipe.config):
            raise IndexError(
                f"Recipe step index out of range: {self.step_index}"
            )

        step = self.recipe.config[self.step_index]
        method_signature = _normalize_method(step.method)

        crafter_method = next(
            (
                candidate
                for candidate in CRAFTER_METHODS
                if candidate.method == method_signature
            ),
            None,
        )

        if crafter_method is None:
            raise ValueError(
                f"Unsupported crafting method at step {self.step_index}: "
                f"{step.method!r}"
            )

        crafter_method.invoke(self)

        logging.debug(
            "done invoke step %d using method %r",
            self.step_index,
            method_signature,
        )

    def evaluate_step(self, item: Item) -> CraftStepResult:
        logging.debug("begin evaluating step")
        step = self.recipe.config[self.step_index]
        if step.autopass:
            logging.debug("done evaluating step autopass")
            return self._goto(ItemMatchResult(True), step.actions.win, step.actions.win_route)
        matcher = ItemMatcher(step, self.recipe.data, self.poecd)
        result = matcher.evaluate(item)
        logging.debug("done evaluating step")
        if result.success:
            return self._goto(result, step.actions.win, step.actions.win_route)
        else:
            return self._goto(result, step.actions.fail, step.actions.fail_route)

    def _goto(self, match: ItemMatchResult, action: str, route: str | None) -> CraftStepResult:
        action = action.casefold()
        if action == 'loop':
            pass
        elif action == 'restart':
            self.step_index = 0
        elif action == 'next':
            self.step_index += 1
        elif action == 'step':
            if route == None:
                raise ValueError(
                    "Recipe step with the `step` action must specify a route")
            self.step_index = int(route) - 1
        done = self.step_index >= len(self.recipe.config)
        return CraftStepResult(match, done)


def _normalize_method(method: Iterable[str]) -> tuple[str, ...]:
    return tuple(part.casefold() for part in method)
