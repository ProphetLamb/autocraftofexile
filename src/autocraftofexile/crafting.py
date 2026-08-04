from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType, TracebackType

import pyautogui
import pytweening
import pywinctl as pwc

from .cancellation_token import CancellationToken
from .item_matcher import ItemMatchResult
from .models.gui_config import Coordinates, GuiConfig
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
        crafter.move_to(crafter.crafting_target)
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
        crafter.move_to(coords)
        crafter.right_click()
        crafter.move_to(crafter.crafting_target)


DEFAULT_CRAFTER_METHODS: tuple[CrafterMethod, ...] = (
    CrafterMethodCheck(),
    CrafterMethodLeftClick(),
    *[CrafterMethodCurrency(method) for method in CURRENCY_METHODS],
)


class Crafter(ABC):
    options: CraftingOptions
    stopping_token: CancellationToken
    dragged_currency: tuple[str | None, ...] | None

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception_value, exception_traceback
        if self.dragged_currency:
            self.dragged_currency = None
            pyautogui.keyUp("shift")

    @property
    @abstractmethod
    def crafting_target(self) -> Coordinates:
        raise NotImplementedError()

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
            self.move_to(self.crafting_target)
            self.right_click()

    def _duration(self, duration: float) -> float:
        return random.uniform(duration * 0.85, duration * 1.15)

    def _position(self, pos: int) -> int:
        return int(random.uniform(pos - 4, pos + 4))

    def move_to(self, coords: Coordinates):
        self.stopping_token.throw_if_cancelled()
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
        self.stopping_token.throw_if_cancelled()
        pyautogui.leftClick(duration=self._duration(1 / self.options.speed))

    def right_click(self):
        self.stopping_token.throw_if_cancelled()
        pyautogui.rightClick(duration=self._duration(1 / self.options.speed))

    def hotkey(self, *keys: str):
        self.stopping_token.throw_if_cancelled()
        pyautogui.hotkey(
            *keys, interval=self._duration(1 / len(keys) / self.options.speed)
        )

    def key_down(self, key: str):
        self.stopping_token.throw_if_cancelled()
        pyautogui.keyDown(key)
        time.sleep(self._duration(1 / self.options.speed))

    def key_up(self, key: str):
        self.stopping_token.throw_if_cancelled()
        pyautogui.keyUp(key)
        time.sleep(self._duration(1 / self.options.speed))
