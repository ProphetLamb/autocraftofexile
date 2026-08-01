from __future__ import annotations

import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from asyncio import CancelledError
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

import keyboard
import pyautogui
import pyperclip
import pytweening
import pywinctl as pwc
from rich import print

from .cancellation_token import CancellationToken, CancellationTokenSource
from .item_match_context import repr_condition
from .item_matcher import ItemMatcher, ItemMatchResult
from .item_parser import parse_item
from .models.gui_config import Coordinates, GuiConfig
from .models.item import Item
from .models.poecd import PoeCd
from .models.recipe import Recipe


@dataclass
class CraftingOptions:
    speed: int


class CraftingWorker:
    _stop: CancellationTokenSource
    _exit: CancellationTokenSource
    _thread: threading.Thread | None
    config: GuiConfig
    recipe: Recipe
    poecd: PoeCd
    options: CraftingOptions
    is_exit_requested: bool
    is_running: bool

    def __init__(
        self, config: GuiConfig, recipe: Recipe, poecd: PoeCd, options: CraftingOptions
    ) -> None:
        self._stop = CancellationTokenSource()
        self._exit = CancellationTokenSource()
        self._thread_lock = threading.Lock()
        self._thread = None
        self.config = config
        self.recipe = recipe
        self.poecd = poecd
        self.options = options
        self.is_exit_requested = False
        self.is_running = False

    def run(self) -> None:
        start_hotkey = keyboard.add_hotkey(
            self.config.start_hotkey,
            self.start,
        )
        stop_hotkey = keyboard.add_hotkey(
            self.config.stop_hotkey,
            self.stop,
        )

        try:
            self._exit.wait()
        finally:
            keyboard.remove_hotkey(start_hotkey)
            keyboard.remove_hotkey(stop_hotkey)

            self.stop()

            with self._thread_lock:
                thread = self._thread
                try:
                    if thread is not None and thread.is_alive():
                        thread.join()
                finally:
                    self._exit.reset()

    def start(self) -> None:
        with self._thread_lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._stop.reset()

            self._thread = threading.Thread(
                target=self._main,
                name="crafting-worker",
                daemon=True,
            )
            self._thread.start()
            self.is_running = True

    def exit(self) -> None:
        self.is_exit_requested = True
        self.stop()
        if self.is_running:
            self._exit.wait()

    def stop(self) -> None:
        with self._thread_lock:
            thread = self._thread

            if thread is not None and thread.is_alive():
                self._stop.cancel()

    def _main(self) -> None:
        current_thread = threading.current_thread()

        try:
            crafter = Crafter(
                self.config, self.recipe, self.poecd, self._stop.token, self.options
            )

            while not self._stop.is_cancelled:
                result = crafter.execute()

                if result.done:
                    return
        except CancelledError:
            message = "Crafter stopped"
            logging.exception(message)
            print(f"[red]{message}[/red]")
        except Exception:
            message = "Crafter terminated unexpectedly"
            logging.exception(message)
            print(f"[red]{message}[/red]")

        finally:
            with self._thread_lock:
                self.is_running = False
                # Avoid an old worker clearing a newer thread reference.
                if self._thread is current_thread:
                    self._thread = None

                self._stop.reset()
                if self.is_exit_requested:
                    self._exit.cancel()

        if not self.is_exit_requested:
            print(
                f"Press [cyan]{self.config.start_hotkey}[/cyan] to start crafting again"
            )


@dataclass(slots=True, frozen=True)
class CraftStepResult:
    match: ItemMatchResult
    done: bool


@dataclass(slots=True, frozen=True)
class CurrencyMethodDefinition:
    method: tuple[str | None, ...]
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
        method=("currency", "augmentation", None),
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
        method=("currency", "regal", None),
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
        method=("currency", "exalted", None),
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

CURRENCY_METHOD_BY_SIGNATURE: Mapping[
    tuple[str | None, ...], CurrencyMethodDefinition
] = MappingProxyType({definition.method: definition for definition in CURRENCY_METHODS})


class CrafterMethod(ABC):
    method: tuple[str | None, ...]

    @abstractmethod
    def invoke(self, crafter: Crafter) -> bool:
        """Applies the crafting method to the item

        Returns:
            bool: `True` if the item changed, otherwise; `False`
        """


class CrafterMethodCheck(CrafterMethod):
    method = ("check",)

    def invoke(self, crafter: Crafter) -> bool:
        del crafter
        return False


def _normalize_method(method: Iterable[str | None]) -> tuple[str | None, ...]:
    return tuple(part.casefold() if part else None for part in method)


def _find_method(methods: Iterable[CrafterMethod], method: Iterable[str | None]):
    method_signature = _normalize_method(method)
    return next(
        (candidate for candidate in methods if candidate.method == method_signature),
        None,
    )


class CrafterMethodCurrency(CrafterMethod):
    definition: CurrencyMethodDefinition

    def __init__(self, definition: CurrencyMethodDefinition) -> None:
        super().__init__()
        self.definition = definition
        self.method = _normalize_method(definition.method)

    def invoke(self, crafter: Crafter):
        coords = self._get_currency_coordinates(crafter.config)
        showcase = crafter.config.showcase
        crafter.move_to(coords)
        crafter.right_click()
        crafter.move_to(showcase)
        crafter.left_click()
        return True

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


DEFAULT_CRAFTER_METHODS: tuple[CrafterMethod, ...] = (
    CrafterMethodCheck(),
    *[CrafterMethodCurrency(method) for method in CURRENCY_METHODS],
)


class Crafter:
    config: GuiConfig
    recipe: Recipe
    poecd: PoeCd
    options: CraftingOptions
    step_index: int = 0
    crafter_methods: tuple[CrafterMethod, ...]
    _current_item: Item | None
    _cached_text: str | None
    _cached_item: Item | None
    _cached_coords: Coordinates | None
    _stopping_token: CancellationToken

    def __init__(
        self,
        config: GuiConfig,
        recipe: Recipe,
        poecd: PoeCd,
        stopping_token: CancellationToken,
        options: CraftingOptions,
        *,
        step_index: int = 0,
        crafter_methods: tuple[CrafterMethod, ...] | None = None,
    ):
        self.config = config
        self.recipe = recipe
        self.poecd = poecd
        self.options = options
        self.step_index = step_index
        self.crafter_methods = crafter_methods or DEFAULT_CRAFTER_METHODS
        self._current_item = None
        self._cached_text = None
        self._cached_item = None
        self._cached_coords = None
        self._stopping_token = stopping_token

    def execute(self):
        try:
            self._ensure_window_focus()
        except:
            print("[red]Failed to focus Path of Exile[/red]")
            raise
        try:
            self._invoke_step()
        except:
            print(f"[red]Failed to invoke crafting step {self.step_index + 1}[/red]")
            raise
        item: Item
        try:
            item = self._get_item()
        except:
            print("[red]Invalid item copied by CTRL+ALT+C[/red]")
            raise
        result: CraftStepResult
        try:
            result = self.evaluate_item(item)
        except:
            print(f"[red]Failed to evaluate crafting step {self.step_index + 1}[/red]")
            raise
        return result

    def _get_item(self) -> Item:
        logging.debug("begin get item")
        self._stopping_token.throw_if_cancelled()
        if self._current_item:
            logging.debug("end get item using cached item")
            return self._current_item

        showcase = self.config.showcase

        self.move_to(showcase)
        self.hotkey("ctrl", "alt", "c")
        time.sleep(self._duration(1 / self.options.speed))

        text = pyperclip.paste()

        if not text.strip():
            raise ValueError("The clipboard is empty after copying the showcase item")
        pyperclip.copy("")

        item = self._cached_item
        if item and self._cached_text == text:
            logging.debug(
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
        logging.debug("done get item")
        return item

    def _invoke_step(self):
        logging.debug("begin invoke step %d", self.step_index)
        self._stopping_token.throw_if_cancelled()

        if not 0 <= self.step_index < len(self.recipe.config):
            raise IndexError(f"Recipe step index out of range: {self.step_index}")
        step = self.recipe.config[self.step_index]
        print(
            f"[bright_white]Step {self.step_index + 1}[/bright_white]: {', '.join(x for x in step.method if x)}"
        )

        crafter_method = _find_method(self.crafter_methods, step.method)
        if crafter_method is None:
            raise ValueError(
                f"Unsupported crafting method at step {self.step_index}: "
                f"{step.method!r}"
            )

        item_changed = crafter_method.invoke(self)
        if item_changed:
            self._ensure_item_changed()

        logging.debug(
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
            logging.warning(message)
            print(f"[orange]{message}[/orange]")
            raise ValueError(message)
        return item

    def evaluate_item(self, item: Item) -> CraftStepResult:
        logging.debug("begin evaluating item %s", repr(item))
        self._stopping_token.throw_if_cancelled()

        step = self.recipe.config[self.step_index]
        if step.autopass:
            logging.debug("done evaluating step autopass")
            return self._goto_step(
                ItemMatchResult(True), step.actions.win, step.actions.win_route
            )
        matcher = ItemMatcher(step, self.recipe.data, self.poecd)
        result = matcher.evaluate(item)

        logging.debug("done evaluating item %s", result)
        if result.success:
            return self._goto_step(result, step.actions.win, step.actions.win_route)
        else:
            return self._goto_step(result, step.actions.fail, step.actions.fail_route)

    def _goto_step(
        self, match: ItemMatchResult, action: str, route: str | None
    ) -> CraftStepResult:
        logging.debug("begin goto step action=%s route=%s", action, route)

        action = action.casefold()
        if action == "loop":
            pass
        elif action == "restart":
            self.step_index = 0
        elif action == "next":
            self.step_index += 1
        elif action == "end":
            self.step_index = len(self.recipe.config)
        elif action == "step":
            if route == None:
                raise ValueError(
                    "Recipe step with the `step` action must specify a route"
                )
            self.step_index = int(route) - 1
        else:
            raise ValueError(f"Unknown action {action}")

        done = self.step_index >= len(self.recipe.config)
        if done:
            print(":sparkles: [green]Done[/green]")
        else:
            print(
                f"{'[green]Success[/green]' if match.success else '[red]Failed[/red]'}"
                f" [reset]{', '.join(repr_condition(x, self.poecd) for x in match.failed if not match.success)}[/reset]"
            )
        logging.debug("done goto step")
        return CraftStepResult(match, done)

    def _ensure_window_focus(self):
        poe = pwc.getWindowsWithTitle("Path of Exile").pop()
        if poe == None:
            raise ValueError("Path of Exile is not running")
        if poe != pwc.getActiveWindow():
            logging.info("Path of Exile is not focussed")
            poe.activate(wait=True)
            self.move_to(self.config.showcase)
            self.right_click()

    def _duration(self, duration: float) -> float:
        return random.uniform(duration * 0.85, duration * 1.15)

    def _position(self, pos: int) -> int:
        return int(random.uniform(pos - 4, pos + 4))

    def move_to(self, coords: Coordinates):
        self._stopping_token.throw_if_cancelled()
        if self._cached_coords == coords:
            return
        self._cached_coords = coords
        weight = random.uniform(4, 6)
        pyautogui.moveTo(
            self._position(coords.x),
            self._position(coords.y),
            duration=self._duration(weight / self.options.speed),
            tween=pytweening.easeInOutElastic,
        )

    def left_click(self):
        self._stopping_token.throw_if_cancelled()
        pyautogui.leftClick(duration=self._duration(1 / self.options.speed))

    def right_click(self):
        self._stopping_token.throw_if_cancelled()
        pyautogui.rightClick(duration=self._duration(1 / self.options.speed))

    def hotkey(self, *keys: str):
        self._stopping_token.throw_if_cancelled()
        pyautogui.hotkey(
            *keys, interval=self._duration(1 / len(keys) / self.options.speed)
        )
