from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType, TracebackType

import pyautogui
import pytweening
import pywinctl as pwc

from .cancellation_token import CancellationToken
from .item_matcher import ItemMatchResult
from .models.coordinates import Coordinates
from .models.gui_config import GuiConfig
from .models.poecd import PoeCd
from .models.recipe import Recipe
from .rich_recipe import RichRecipe

_logger = logging.getLogger(__name__)


@dataclass
class CraftingOptions:
    speed: int
    rich_recipe: RichRecipe
    config: GuiConfig
    recipe: Recipe
    poecd: PoeCd


@dataclass(slots=True, frozen=True)
class CraftStepResult:
    match: ItemMatchResult
    done: bool


@dataclass(slots=True, frozen=True)
class CurrencyMethodDefinition:
    method: tuple[str | None, ...]
    coord_field: str
    tab: tuple[str, ...]


CURRENCY_METHODS: tuple[CurrencyMethodDefinition, ...] = (
    CurrencyMethodDefinition(
        method=("currency", "transmute"),
        coord_field="transmute",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "augmentation", "augmentation_normal"),
        coord_field="augment",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "augmentation", None),
        coord_field="augment",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "alteration"),
        coord_field="alteration",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "regal", "regal_normal"),
        coord_field="regal",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "regal", None),
        coord_field="regal",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "alchemy"),
        coord_field="alchemy",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "chaos"),
        coord_field="chaos",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "exalted", "exalted_normal"),
        coord_field="exalt",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "exalted", None),
        coord_field="exalt",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "scour"),
        coord_field="scour",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "annul"),
        coord_field="annul",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "fusing", "fusing_normal"),
        coord_field="fusing",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "fusing", None),
        coord_field="fusing",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "jeweller", "jeweller_normal"),
        coord_field="jeweller",
        tab=("currency", "general"),
    ),
    CurrencyMethodDefinition(
        method=("currency", "jeweller", None),
        coord_field="jeweller",
        tab=("currency", "general"),
    ),
)

CURRENCY_METHOD_BY_SIGNATURE: Mapping[
    tuple[str | None, ...], CurrencyMethodDefinition
] = MappingProxyType({definition.method: definition for definition in CURRENCY_METHODS})


class CrafterMethod(ABC):
    method: tuple[str | None, ...]

    @abstractmethod
    def accepts_dragged_currency(self, poe: PoeController) -> bool:
        """Determines if this method accepts the the currently dragged currency

        Returns:
            bool: `True` if the dragged currency is acceptable, otherwise; `False`
        """

    @abstractmethod
    def invoke(self, poe: PoeController) -> bool:
        """Applies the crafting method to the item

        Returns:
            bool: `True` if the item changed, otherwise; `False`
        """


class CrafterMethodCheck(CrafterMethod):
    method = ("check",)

    def accepts_dragged_currency(self, poe: PoeController) -> bool:
        del poe
        return True

    def invoke(self, poe: PoeController) -> bool:
        del poe
        return False


class CrafterMethodDragCurrency(CrafterMethod, ABC):
    def accepts_dragged_currency(self, poe: PoeController) -> bool:
        return poe.dragged_currency == self.method

    def invoke(self, poe: PoeController) -> bool:
        if self.accepts_dragged_currency(poe):
            poe.left_click()
            return True
        if poe.dragged_currency:
            poe.key_up("shift")
            poe.dragged_currency = None
        self.acquire(poe)
        poe.dragged_currency = self.method
        poe.move_to_crafting_target()
        poe.key_down("shift")
        poe.left_click()
        return True

    @abstractmethod
    def acquire(self, poe: PoeController) -> None:
        raise NotImplementedError()


class CrafterMethodLeftClick(CrafterMethodDragCurrency):
    method = ("click", "left_click_drag")

    def acquire(self, poe: PoeController) -> None:
        del poe


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

    def acquire(self, poe: PoeController) -> None:
        coords = _get_currency_coordinates(self.method, poe.options.config)
        poe.move_to(StashLocation(self.definition.tab, coords))
        poe.right_click()
        poe.move_to_crafting_target()


DEFAULT_CRAFTER_METHODS: tuple[CrafterMethod, ...] = (
    CrafterMethodCheck(),
    CrafterMethodLeftClick(),
    *[CrafterMethodCurrency(method) for method in CURRENCY_METHODS],
)


@dataclass(slots=True, frozen=True)
class StashLocation:
    tab: tuple[str, ...]
    coords: Coordinates


@dataclass(slots=True)
class PoeController:
    options: CraftingOptions
    stopping_token: CancellationToken
    current_loc: StashLocation | None = field(default=None)
    crafting_target_loc: StashLocation | None = field(default=None)
    dragged_currency: tuple[str | None, ...] | None = field(default=None)

    def duration(self, duration: float) -> float:
        return random.uniform(duration * 0.85, duration * 1.15)

    def _position(self, pos: int) -> int:
        return int(random.uniform(pos - 4, pos + 4))

    def move_to_crafting_target(self):
        if not self.crafting_target_loc:
            raise ValueError("Crafting target is not configured")
        self.move_to(self.crafting_target_loc)

    def move_to(self, loc: StashLocation):
        self.stopping_token.throw_if_cancelled()
        if self.current_loc == loc:
            return
        if self.current_loc and self.current_loc.tab != loc.tab:
            pass

        self.current_loc = loc
        self._move_to_point(loc.coords)

    def _move_to_point(self, coords: Coordinates):
        weight = random.uniform(4, 6)
        pyautogui.moveTo(
            self._position(coords.x),
            self._position(coords.y),
            duration=self.duration(weight / self.options.speed),
            tween=pytweening.easeInOutElastic,
        )
        if not self.current_loc:
            self.current_loc = StashLocation((), coords)
        elif self.current_loc.coords != coords:
            replace(self.current_loc, coords=coords)

    def left_click(self):
        self.stopping_token.throw_if_cancelled()
        pyautogui.leftClick(duration=self.duration(1 / self.options.speed))

    def right_click(self):
        self.stopping_token.throw_if_cancelled()
        pyautogui.rightClick(duration=self.duration(1 / self.options.speed))

    def hotkey(self, *keys: str):
        self.stopping_token.throw_if_cancelled()
        pyautogui.hotkey(
            *keys, interval=self.duration(1 / len(keys) / self.options.speed)
        )

    def key_down(self, key: str):
        self.stopping_token.throw_if_cancelled()
        pyautogui.keyDown(key)
        time.sleep(self.duration(1 / self.options.speed))

    def key_up(self, key: str):
        self.stopping_token.throw_if_cancelled()
        pyautogui.keyUp(key)
        time.sleep(self.duration(1 / self.options.speed))


@dataclass(slots=True)
class Crafter(ABC):
    options: CraftingOptions
    poe: PoeController
    open_tab: tuple[str, ...] | None

    def __init__(
        self, options: CraftingOptions, stopping_token: CancellationToken
    ) -> None:
        self.options = options
        self.poe = PoeController(options, stopping_token)
        self.poe.dragged_currency = None
        self.open_tab = None

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception_value, exception_traceback
        if self.poe.dragged_currency:
            self.poe.dragged_currency = None
            pyautogui.keyUp("shift")

    @abstractmethod
    def execute(self) -> CraftStepResult:
        raise NotImplementedError()

    def _ensure_window_focus(self):
        poe = pwc.getWindowsWithTitle("Path of Exile").pop()
        if poe == None:
            raise ValueError("Path of Exile is not running")
        if poe != pwc.getActiveWindow():
            _logger.info("Path of Exile is not focussed")
            poe.activate(wait=True)
            self.poe.move_to_crafting_target()
            self.poe.right_click()
