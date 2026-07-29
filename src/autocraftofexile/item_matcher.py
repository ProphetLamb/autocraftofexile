from __future__ import annotations

from typing import Iterable

from .item_match_context import ItemMatchContext, ItemMatchResult
from .models.item import Item
from .models.poecd import PoeCd
from .models.recipe import (
    RecipeCondition,
    RecipeData,
    RecipeFilter,
    RecipeStep,
)
from .rules import (
    DEFAULT_RULES,
    Rule,
)


class ItemMatcher:
    def __init__(
        self, method: RecipeStep, recipe_data: RecipeData, poecd: PoeCd,
        rules: Iterable[Rule] | None = None,
    ) -> None:
        self.method = method
        self.recipe_data = recipe_data
        self.poecd = poecd
        self.rules = DEFAULT_RULES if rules is None else tuple(rules)

    def evaluate(self, item: Item) -> ItemMatchResult:
        if self.method.autopass or not self.method.filters:
            return ItemMatchResult(True)

        context = ItemMatchContext(item, self.recipe_data, self.poecd)
        result = ItemMatchResult(True)

        for recipe_filter in self.method.filters:
            rhs = self._evauate_filter(recipe_filter, context)
            # boolean logic
            operator = recipe_filter.type.casefold()
            if operator == "and":
                result.merge(rhs)
            elif operator == "not":
                rhs.negate()
                result.merge(rhs)
            elif operator == "or":
                result.merge(rhs)
                if result.success:
                    return result
                result = ItemMatchResult(True)
            else:
                raise ValueError(
                    f"Unsupported recipe filter type: {operator}"
                )
        return result

    def _evauate_filter(self, recipe_filter: RecipeFilter, context: ItemMatchContext) -> ItemMatchResult:
        result = ItemMatchResult(True)
        passed = 0

        for condition in recipe_filter.conds:
            condition_result = self._rule_for(condition).evaluate(
                condition,
                context,
                recipe_filter,
            )
            passed += int(condition_result.success)
            result.merge(condition_result)

        result.success = passed >= (
            recipe_filter.treshold or len(recipe_filter.conds)
        )
        return result

    def _rule_for(self, condition: RecipeCondition) -> Rule:
        for rule in self.rules:
            if rule.supports(condition):
                return rule
        raise ValueError(f"No condition rule handles {condition.id!r}")
