from __future__ import annotations

import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from asyncio import CancelledError
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType, TracebackType

import keyboard
import pyautogui
import pyperclip
import pytweening
import pywinctl as pwc

from .cancellation_token import CancellationToken, CancellationTokenSource
from .item_matcher import ItemMatcher, ItemMatchResult
from .item_parser import parse_item
from .models.gui_config import Coordinates, GuiConfig
from .models.item import Item
from .models.poecd import PoeCd
from .models.recipe import Recipe
from .rich_recipe import RichRecipe, StepStatus


@dataclass
class CraftingOptions:
    speed: int
    rich_recipe: RichRecipe
    config: GuiConfig
    recipe: Recipe
    poecd: PoeCd


class CraftingWorker:
    _stop: CancellationTokenSource
    _exit: CancellationTokenSource
    _thread: threading.Thread | None
    options: CraftingOptions
    is_exit_requested: bool
    is_running: bool

    def __init__(self, options: CraftingOptions) -> None:
        self._stop = CancellationTokenSource()
        self._exit = CancellationTokenSource()
        self._thread_lock = threading.Lock()
        self._thread = None
        self.options = options
        self.is_exit_requested = False
        self.is_running = False

    def run(self) -> None:
        hotkeys = [
            keyboard.add_hotkey(self.options.config.start_hotkey, self.start),
            keyboard.add_hotkey(self.options.config.stop_hotkey, self.stop),
        ]
        try:
            self._exit.wait()
        finally:
            for h in hotkeys:
                keyboard.remove_hotkey(h)

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

    def _clean_rich_recipe(self):
        rr = self.options.rich_recipe
        rr.appendix = []
        rr.status = {}
        rr.update()

    def _main(self) -> None:
        current_thread = threading.current_thread()

        try:
            self._clean_rich_recipe()
            crafter = Crafter(self._stop.token, self.options)
            with crafter:
                while not self._stop.is_cancelled:
                    result = crafter.execute()

                    if result.done:
                        return
        except CancelledError:
            message = "Crafter stopped"
            logging.exception(message)
            self.options.rich_recipe.update(append=f"[red]{message}[/red]")
        except Exception:
            message = "Crafter terminated unexpectedly"
            logging.exception(message)
            self.options.rich_recipe.update(append=f"[red]{message}[/red]")

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
            self.options.rich_recipe.update(
                append=f"Press [cyan]{self.options.config.start_hotkey}[/cyan] to start crafting again"
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
    CurrencyMethodDefinition(
        method=("currency", "fusing", "fusing_normal"),
        coord_field="fusing",
    ),
    CurrencyMethodDefinition(
        method=("currency", "fusing", None),
        coord_field="fusing",
    ),
    CurrencyMethodDefinition(
        method=("currency", "jeweller", "jeweller_normal"),
        coord_field="jeweller",
    ),
    CurrencyMethodDefinition(
        method=("currency", "jeweller", None),
        coord_field="jeweller",
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


class CrafterMethodDragCurrency(CrafterMethod, ABC):
    def invoke(self, crafter: Crafter) -> bool:
        if crafter.dragged_currency == self.method:
            crafter.left_click()
            return True
        if crafter.dragged_currency:
            crafter.key_up("shift")
            crafter.dragged_currency = None
        self.acquire(crafter)
        crafter.dragged_currency = self.method
        crafter.move_to(crafter.options.config.showcase)
        crafter.key_down("shift")
        crafter.left_click()
        return True

    @abstractmethod
    def acquire(self, crafter: Crafter) -> None:
        raise NotImplementedError()


class CrafterMethodLeftClick(CrafterMethodDragCurrency):
    method = ("click", "left_click_drag")

    def acquire(self, crafter: Crafter) -> None:
        pass


def _normalize_method(method: Iterable[str | None]) -> tuple[str | None, ...]:
    return tuple(part.casefold() if part else None for part in method)


def find_crafter_method(methods: Iterable[CrafterMethod], method: Iterable[str | None]):
    method_signature = _normalize_method(method)
    return next(
        (candidate for candidate in methods if candidate.method == method_signature),
        None,
    )


def _get_currency_coordinates(
    method: tuple[str | None, ...],
    config: GuiConfig,
) -> Coordinates:
    definition = CURRENCY_METHOD_BY_SIGNATURE.get(method)

    if definition is None:
        raise ValueError(f"Unsupported currency method: {method!r}")

    coordinate = getattr(config, definition.coord_field, None)
    if coordinate is None:
        raise ValueError(
            f"GuiConfig has no {definition.coord_field!r} coordinate "
            f"for method {method!r}"
        )

    return coordinate


class CrafterMethodCurrency(CrafterMethodDragCurrency):
    definition: CurrencyMethodDefinition

    def __init__(self, definition: CurrencyMethodDefinition) -> None:
        super().__init__()
        self.definition = definition
        self.method = _normalize_method(definition.method)

    def acquire(self, crafter: Crafter) -> None:
        coords = _get_currency_coordinates(self.method, crafter.options.config)
        showcase = crafter.options.config.showcase
        crafter.move_to(coords)
        crafter.right_click()
        crafter.move_to(showcase)


DEFAULT_CRAFTER_METHODS: tuple[CrafterMethod, ...] = (
    CrafterMethodCheck(),
    CrafterMethodLeftClick(),
    *[CrafterMethodCurrency(method) for method in CURRENCY_METHODS],
)


class Crafter:
    options: CraftingOptions
    step_index: int = 0
    crafter_methods: tuple[CrafterMethod, ...]
    dragged_currency: tuple[str | None, ...] | None
    _current_item: Item | None
    _cached_text: str | None
    _cached_item: Item | None
    _cached_coords: Coordinates | None
    _stopping_token: CancellationToken

    def __init__(
        self,
        stopping_token: CancellationToken,
        options: CraftingOptions,
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
        self._stopping_token = stopping_token
        self._stats = {}

    def __enter__(self):
        pass

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ):
        del exception_type, exception_value, exception_traceback
        if self.dragged_currency:
            self.dragged_currency = None
            pyautogui.keyUp("shift")

    def execute(self):
        logging.debug("begin executing step %d", self.step_index)
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
            result = self.evaluate_item(item)
        except:
            self.options.rich_recipe.update(
                f"[red]Failed to evaluate crafting step {self.step_index + 1}[/red]"
            )
            raise
        logging.debug("done executing step")
        return result

    def _get_item(self) -> Item:
        logging.debug("begin get item")
        self._stopping_token.throw_if_cancelled()
        if self._current_item:
            logging.debug("end get item using cached item")
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
        if not 0 <= self.step_index < len(self.options.recipe.config):
            raise IndexError(f"Recipe step index out of range: {self.step_index}")
        step = self.options.recipe.config[self.step_index]
        self._stopping_token.throw_if_cancelled()
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
            self.options.rich_recipe.update(append=f"[orange]{message}[/orange]")
            raise ValueError(message)
        return item

    def evaluate_item(self, item: Item) -> CraftStepResult:
        logging.debug("begin evaluating item %s", repr(item))
        self._stopping_token.throw_if_cancelled()

        step = self._current_step
        if step.autopass:
            logging.debug("done evaluating step autopass")
            return self._goto_step(
                ItemMatchResult(True), step.actions.win, step.actions.win_route
            )
        matcher = ItemMatcher(step, self.options.recipe.data, self.options.poecd)
        result = matcher.evaluate(item)

        logging.debug("done evaluating item %s", repr(result))
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
        logging.debug("begin goto step action=%s route=%s", action, route)
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
        logging.debug("done goto step")
        return CraftStepResult(match, done)

    def _ensure_window_focus(self):
        poe = pwc.getWindowsWithTitle("Path of Exile").pop()
        if poe == None:
            raise ValueError("Path of Exile is not running")
        if poe != pwc.getActiveWindow():
            logging.info("Path of Exile is not focussed")
            poe.activate(wait=True)
            self.move_to(self.options.config.showcase)
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

    def key_down(self, key: str):
        self._stopping_token.throw_if_cancelled()
        pyautogui.keyDown(key)
        time.sleep(self._duration(1 / self.options.speed))

    def key_up(self, key: str):
        self._stopping_token.throw_if_cancelled()
        pyautogui.keyUp(key)
        time.sleep(self._duration(1 / self.options.speed))
