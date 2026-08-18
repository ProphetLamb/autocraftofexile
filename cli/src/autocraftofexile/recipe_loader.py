import json
import logging
from collections.abc import Iterable
from os import PathLike

from rich.prompt import Prompt

from .crafting import CrafterMethod, find_crafter_method
from .models.poecd import PoeCd
from .models.recipe import Recipe, RecipeCondition, RecipeFilter, RecipeStep
from .rules import Rule

_logger = logging.getLogger(__name__)


def load_recipe(file: PathLike[str] | str) -> Recipe:
    data = None
    _logger.debug("begin Recipe data file read")
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = Prompt.ask(
            f"[red]No recipe found at {file!r}[/red]\n"
            "[bright_white]Please export your [link=https://www.craftofexile.com/?game=poe1][i]Craft of Exile[/i][/link] Simulator, and paste the JSON here.[/bright_white] Confirm with ENTER:"
        )
        data = json.loads(data)
    _logger.debug("done Recipe data file read")
    recipe = Recipe.from_dict(data)
    _logger.debug("done Recipe data parse")
    return recipe


def validate_recipe(
    recipe: Recipe,
    poecd: PoeCd,
    filter_logic_types: set[str],
    crafting_methods: Iterable[CrafterMethod],
    modifier_rules: Iterable[Rule],
):
    _logger.debug("begin validating recipe")
    errors: list[str] = []

    def validate_cond(prefix: str, cond: RecipeCondition):
        if cond.id.isdigit():
            if not poecd.modifiers.get(cond.id):
                errors.append(f"{prefix} unrecognized modifier {cond.id}")
        else:
            rule = next(rule for rule in modifier_rules if rule.supports(cond))
            if not rule:
                errors.append(f"{prefix} unknown rule {cond.id}")

    def validate_filter(prefix: str, filter_: RecipeFilter):
        if not filter_.type.casefold() in filter_logic_types:
            errors.append(f"{prefix} invalid type {filter_.type}")
        for ci, cond in enumerate(filter_.conds or []):
            validate_cond(f"{prefix} condition {ci + 1}", cond)

    def validate_step(prefix: str, step: RecipeStep):
        if not find_crafter_method(crafting_methods, step.method):
            errors.append(
                f"{prefix} could not resolve the crafting method {step.method!r}"
            )
        for fi, filter_ in enumerate(step.filters or []):
            validate_filter(f"{prefix} filter {fi + 1}", filter_)

    for si, step in enumerate(recipe.config):
        validate_step(f"Step {si + 1}", step)
    _logger.debug("done validating recipe %s", repr(errors))
    return errors
