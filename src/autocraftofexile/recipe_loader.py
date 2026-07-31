import json
import logging
from os import PathLike
from typing import Iterable

from autocraftofexile import RECIPE_FILE
from .rules import Rule
from .models.poecd import PoeCd
from .crafting import CrafterMethod, _find_method

from .models.recipe import Recipe, RecipeCondition, RecipeFilter, RecipeStep


def load_recipe(file: PathLike[str] | str | None = None) -> Recipe:
    data = None
    logging.debug("begin Recipe data file read")
    with open(file or RECIPE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    logging.debug("done Recipe data file read")
    recipe = Recipe.from_dict(data)
    logging.debug("done Recipe data parse")
    return recipe


def validate_recipe(
    recipe: Recipe,
    poecd: PoeCd,
    filter_logic_types: set[str],
    crafting_methods: Iterable[CrafterMethod],
    modifier_rules: Iterable[Rule]
):
    errors: list[str] = []

    def validate_cond(prefix: str, cond: RecipeCondition):
        if cond.id.isdigit():
            if not poecd.modifiers.get(cond.id):
                errors.append(
                    f"{prefix} unrecognized modifier {cond.id}")
        else:
            rule = next(
                rule
                for rule in modifier_rules
                if rule.supports(cond)
            )
            if not rule:
                errors.append(
                    f"{prefix} unknown rule {cond.id}")

    def validate_filter(prefix: str, filter_: RecipeFilter):
        if not filter_.type.casefold() in filter_logic_types:
            errors.append(
                f"{prefix} invalid type {filter_.type}")
        for ci, cond in enumerate(filter_.conds or []):
            validate_cond(
                f"{prefix} condition {ci + 1}", cond)

    def validate_step(prefix: str, step: RecipeStep):
        if not _find_method(crafting_methods, step.method):
            errors.append(
                f"{prefix} could not resolve the crafting method {step.method!r}")
        for fi, filter_ in enumerate(step.filters or []):
            validate_filter(f"{prefix} filter {fi+1}", filter_)

    for si, step in enumerate(recipe.config):
        validate_step(f"Step {si+1}", step)
    return errors
