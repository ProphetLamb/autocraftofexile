from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable

from autocraftofexile.models.item import Item
from autocraftofexile.models.poecd import PoeCd
from autocraftofexile.models.recipe import (
    RecipeCondition,
    RecipeData,
    RecipeFilter,
    RecipeMethod,
)

_NUMBER = r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
_NUMBER_PATTERN = rf"{_NUMBER}(?:\({_NUMBER}-{_NUMBER}\))?"
_SPACE_PATTERN = r"\s+"


@dataclass(slots=True)
class ItemMatchResult:
    success: bool
    modifiers: list[ItemModifierMatchResult]
    failed: RecipeConditions


RecipeConditions = list[RecipeCondition]


@dataclass(slots=True)
class ItemModifierMatchResult:
    attributes: list[RecipeConditions]
    text: list[RecipeConditions]


def normalize_modifier_text(value: str) -> str:
    """Normalize whitespace and common PoE punctuation before matching."""
    return " ".join(value.replace("\u2013", "-").replace("\u2014", "-").split())


def rolled_value(value: str) -> float:
    """Return the rolled number, excluding an optional displayed roll range."""
    return float(value.split("(", maxsplit=1)[0])


def modifier_template_pattern(template: str) -> re.Pattern[str]:
    """Convert a Craft of Exile modifier template into a full-match regex.

    Every ``#`` placeholder captures a signed integer or decimal value, with
    an optional roll range such as ``95(90-104)`` or ``-10(-20--10)``.
    Literal whitespace is
    matched flexibly.
    """
    parts = re.split(r"(#|\s+)", normalize_modifier_text(template))
    pattern: list[str] = []

    for part in parts:
        if not part:
            continue
        if part == "#":
            pattern.append(f"({_NUMBER_PATTERN})")
        elif part.isspace():
            pattern.append(_SPACE_PATTERN)
        else:
            pattern.append(re.escape(part))

    return re.compile("".join(pattern), re.IGNORECASE)


class ConditionRule(ABC):
    @abstractmethod
    def supports(self, condition: RecipeCondition) -> bool:
        pass

    @abstractmethod
    def evaluate(
        self,
        condition: RecipeCondition,
        context: MatchContext,
        filter_: RecipeFilter,
    ) -> bool:
        pass


@dataclass(frozen=True, slots=True)
class MatchContext:
    item: Item
    recipe_data: RecipeData
    poecd: PoeCd
    prefix_count: int = field(init=False)
    suffix_count: int = field(init=False)
    influence_names: tuple[str, ...] = field(init=False)
    resistance_templates: tuple[
        tuple[re.Pattern[str], frozenset[str]], ...
    ] = field(init=False)
    attribute_templates: tuple[
        tuple[re.Pattern[str], frozenset[str]], ...
    ] = field(init=False)
    normalized_modifier_text: tuple[tuple[str, ...], ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "prefix_count",
            sum(
                modifier.slot.casefold() == "prefix"
                for modifier in self.item.modifiers
            ),
        )
        object.__setattr__(
            self,
            "suffix_count",
            sum(
                modifier.slot.casefold() == "suffix"
                for modifier in self.item.modifiers
            ),
        )
        object.__setattr__(
            self,
            "influence_names",
            tuple(
                group.name_mgroup
                for group in self.poecd.mgroups
                if str(group.is_influence) == "1" and group.name_mgroup
            ),
        )
        object.__setattr__(
            self,
            "resistance_templates",
            self._build_resistance_templates(),
        )
        object.__setattr__(
            self,
            "attribute_templates",
            self._build_attribute_templates(),
        )
        object.__setattr__(
            self,
            "normalized_modifier_text",
            tuple(
                tuple(normalize_modifier_text(line) for line in modifier.text)
                for modifier in self.item.modifiers
            ),
        )

    @property
    def open_prefixes(self) -> int:
        return max(0, self.recipe_data.maxaffgrp.prefix - self.prefix_count)

    @property
    def open_suffixes(self) -> int:
        return max(0, self.recipe_data.maxaffgrp.suffix - self.suffix_count)

    def _build_resistance_templates(
        self,
    ) -> tuple[tuple[re.Pattern[str], frozenset[str]], ...]:
        templates: dict[str, tuple[str, frozenset[str]]] = {}

        for modifier in self.poecd.modifiers:
            for component in modifier.name_modifier.split(","):
                template = normalize_modifier_text(component.strip())
                affected = self._affected_resistances(template)
                if affected:
                    templates.setdefault(
                        template.casefold(), (template, affected))

        return tuple(
            (modifier_template_pattern(template), affected)
            for template, affected in templates.values()
        )

    def _build_attribute_templates(
        self,
    ) -> tuple[tuple[re.Pattern[str], frozenset[str]], ...]:
        templates: dict[str, tuple[str, frozenset[str]]] = {}

        for modifier in self.poecd.modifiers:
            for component in modifier.name_modifier.split(","):
                template = normalize_modifier_text(component.strip())
                affected = self._affected_attributes(template)
                if affected:
                    templates.setdefault(
                        template.casefold(), (template, affected))

        return tuple(
            (modifier_template_pattern(template), affected)
            for template, affected in templates.values()
        )

    @staticmethod
    def _affected_attributes(template: str) -> frozenset[str]:
        value = template.casefold()

        # Count direct flat attribute bonuses only. This deliberately excludes
        # percentage increases, requirements, and conditional attribute text.
        if not re.search(r"(?:^|\s)[+]?#+\s+to\s+", value):
            return frozenset()
        if "%" in value:
            return frozenset()

        if "all attributes" in value:
            return frozenset({"strength", "dexterity", "intelligence"})

        return frozenset(
            attribute
            for attribute in ("strength", "dexterity", "intelligence")
            if re.search(rf"\b{attribute}\b", value)
        )

    @staticmethod
    def _affected_resistances(template: str) -> frozenset[str]:
        value = template.casefold()

        if not re.search(r"\bto\b.*\bresistances?\b", value):
            return frozenset()
        if any(
            excluded in value
            for excluded in ("maximum", "penetrate", "monster", "player")
        ):
            return frozenset()

        if "all resistances" in value:
            return frozenset({"fire", "cold", "lightning", "chaos"})
        if "all elemental resistances" in value:
            return frozenset({"fire", "cold", "lightning"})

        return frozenset(
            element
            for element in ("fire", "cold", "lightning", "chaos")
            if re.search(rf"\b{element}\b", value)
        )


class PseudoConditionRule(ConditionRule, ABC):
    """Base class for one pseudo-condition that evaluates an integer value."""

    condition_id: str

    def supports(self, condition: RecipeCondition) -> bool:
        return condition.id == self.condition_id

    def evaluate(
        self,
        condition: RecipeCondition,
        context: MatchContext,
        filter_: RecipeFilter,
    ) -> bool:
        del filter_
        return in_condition_range(self.value(context), condition)

    @abstractmethod
    def value(self, context: MatchContext) -> int:
        pass


class OpenAffixRule(PseudoConditionRule):
    condition_id = "open_affix"

    def value(self, context: MatchContext) -> int:
        return context.open_prefixes + context.open_suffixes


class OpenPrefixRule(PseudoConditionRule):
    condition_id = "open_prefix"

    def value(self, context: MatchContext) -> int:
        return context.open_prefixes


class OpenSuffixRule(PseudoConditionRule):
    condition_id = "open_suffix"

    def value(self, context: MatchContext) -> int:
        return context.open_suffixes


class CountAffixRule(PseudoConditionRule):
    condition_id = "count_affix"

    def value(self, context: MatchContext) -> int:
        return context.prefix_count + context.suffix_count


class CountPrefixRule(PseudoConditionRule):
    condition_id = "count_prefix"

    def value(self, context: MatchContext) -> int:
        return context.prefix_count


class CountSuffixRule(PseudoConditionRule):
    condition_id = "count_suffix"

    def value(self, context: MatchContext) -> int:
        return context.suffix_count


class AttributeCountRule(PseudoConditionRule, ABC):
    """Base class for counting affixes by modifier attribute."""

    attribute: str
    negate: bool = False

    def value(self, context: MatchContext) -> int:
        expected = self.attribute.casefold()
        return sum(
            self._matches(modifier.attributes, expected)
            for modifier in context.item.modifiers
            if modifier.slot.casefold() in {"prefix", "suffix"}
        )

    def _matches(self, attributes: list[str], expected: str) -> bool:
        contains = any(attribute.casefold() ==
                       expected for attribute in attributes)
        return not contains if self.negate else contains


class CountAttackRule(AttributeCountRule):
    condition_id = "count_attack"
    attribute = "Attack"


class CountNonAttackRule(AttributeCountRule):
    condition_id = "count_nattack"
    attribute = "Attack"
    negate = True


class CountCasterRule(AttributeCountRule):
    condition_id = "count_caster"
    attribute = "Caster"


class CountNonCasterRule(AttributeCountRule):
    condition_id = "count_ncaster"
    attribute = "Caster"
    negate = True


class InfluencedAffixRule(PseudoConditionRule, ABC):
    """Base for influenced-affix counters.

    An affix is influenced when its displayed name contains a modifier-group
    name from ``PoeCd.mgroups``. Matching is case-insensitive and uses word
    boundaries, so names such as ``The Elder's`` and ``of the Elder`` match the
    ``Elder`` modifier group.
    """

    slots: frozenset[str]

    def value(self, context: MatchContext) -> int:
        return sum(
            modifier.slot.casefold() in self.slots
            and self._has_influence_name(modifier.name, context.influence_names)
            for modifier in context.item.modifiers
        )

    @staticmethod
    def _has_influence_name(name: str, influence_names: tuple[str, ...]) -> bool:
        return any(
            re.search(
                rf"(?<!\w){re.escape(influence_name)}(?!\w)",
                name,
                re.IGNORECASE,
            )
            is not None
            for influence_name in influence_names
        )


class CountInfluencedAffixRule(InfluencedAffixRule):
    condition_id = "count_iaffix"
    slots = frozenset({"prefix", "suffix"})


class CountInfluencedPrefixRule(InfluencedAffixRule):
    condition_id = "count_iprefix"
    slots = frozenset({"prefix"})


class CountInfluencedSuffixRule(InfluencedAffixRule):
    condition_id = "count_isuffix"
    slots = frozenset({"suffix"})


class ResistanceRule(ConditionRule, ABC):
    """Base rule for summed resistance pseudo-conditions.

    Resistance templates are discovered from ``PoeCd.modifiers``. Each
    comma-separated template component is considered independently, because
    each component corresponds to one line in ``ItemModifier.text``.
    """

    elements: frozenset[str]
    condition_id: str

    def supports(self, condition: RecipeCondition) -> bool:
        return condition.id == self.condition_id

    def evaluate(
        self,
        condition: RecipeCondition,
        context: MatchContext,
        filter_: RecipeFilter,
    ) -> bool:
        del filter_
        total = self._total(context)
        return in_condition_range(total, condition)

    def _total(self, context: MatchContext) -> float:
        total = 0.0

        for modifier_text in context.normalized_modifier_text:
            for line in modifier_text:
                contribution = self._line_contribution(
                    line,
                    context.resistance_templates,
                )
                if contribution is not None:
                    total += contribution

        return total

    def _line_contribution(
        self,
        line: str,
        templates: tuple[tuple[re.Pattern[str], frozenset[str]], ...],
    ) -> float | None:
        for pattern, affected_elements in templates:
            match = pattern.fullmatch(line)
            if match is None:
                continue

            values = tuple(
                rolled_value(value)
                for value in match.groups()
            )
            if not values:
                continue

            # Direct and composite resistance templates use one shared value.
            # If a future template contains more placeholders, each contributes.
            multiplier = len(affected_elements & self.elements)
            if multiplier:
                return sum(values) * multiplier

        return None


class FireResistanceRule(ResistanceRule):
    condition_id = "pseudo_fire_resist"
    elements = frozenset({"fire"})


class ColdResistanceRule(ResistanceRule):
    condition_id = "pseudo_cold_resist"
    elements = frozenset({"cold"})


class LightningResistanceRule(ResistanceRule):
    condition_id = "pseudo_lightning_resist"
    elements = frozenset({"lightning"})


class ChaosResistanceRule(ResistanceRule):
    condition_id = "pseudo_chaos_resist"
    elements = frozenset({"chaos"})


class ElementalResistancesRule(ResistanceRule):
    condition_id = "pseudo_elemental_resists"
    elements = frozenset({"fire", "cold", "lightning"})


class TotalResistancesRule(ResistanceRule):
    condition_id = "pseudo_total_resists"
    elements = frozenset({"fire", "cold", "lightning", "chaos"})


class AttributeValueRule(ConditionRule, ABC):
    """Base rule for summed flat attribute pseudo-conditions."""

    attributes: frozenset[str]
    condition_id: str

    def supports(self, condition: RecipeCondition) -> bool:
        return condition.id == self.condition_id

    def evaluate(
        self,
        condition: RecipeCondition,
        context: MatchContext,
        filter_: RecipeFilter,
    ) -> bool:
        del filter_
        return in_condition_range(self._total(context), condition)

    def _total(self, context: MatchContext) -> float:
        total = 0.0

        for modifier_text in context.normalized_modifier_text:
            for line in modifier_text:
                contribution = self._line_contribution(
                    line,
                    context.attribute_templates,
                )
                if contribution is not None:
                    total += contribution

        return total

    def _line_contribution(
        self,
        line: str,
        templates: tuple[tuple[re.Pattern[str], frozenset[str]], ...],
    ) -> float | None:
        for pattern, affected_attributes in templates:
            match = pattern.fullmatch(line)
            if match is None:
                continue

            values = tuple(rolled_value(value) for value in match.groups())
            if not values:
                continue

            multiplier = len(affected_attributes & self.attributes)
            if multiplier:
                return sum(values) * multiplier

        return None


class AttributesRule(AttributeValueRule):
    condition_id = "pseudo_attributes"
    attributes = frozenset({"strength", "dexterity", "intelligence"})


class StrengthRule(AttributeValueRule):
    condition_id = "pseudo_strength"
    attributes = frozenset({"strength"})


class DexterityRule(AttributeValueRule):
    condition_id = "pseudo_dexterity"
    attributes = frozenset({"dexterity"})


class IntelligenceRule(AttributeValueRule):
    condition_id = "pseudo_intelligence"
    attributes = frozenset({"intelligence"})


class ModifierPresenceRule(ConditionRule):
    """Match a numeric condition ID against parsed modifier text lines.

    Craft of Exile separates hybrid modifier templates with commas, while the
    Path of Exile clipboard represents each component on a separate text line.
    A parsed item modifier matches when every template component matches at
    least one line in ``ItemModifier.text`` and every captured rolled value is
    between the condition's ``treshold`` and ``max`` bounds, inclusively. Line
    order and unrelated additional lines do not affect the match.
    """

    def supports(self, condition: RecipeCondition) -> bool:
        return condition.id.isdigit()

    def evaluate(
        self,
        condition: RecipeCondition,
        context: MatchContext,
        filter_: RecipeFilter,
    ) -> bool:
        poecd_modifier = context.poecd.modifiers.get(condition.id)
        if poecd_modifier is None:
            return False

        patterns = [
            modifier_template_pattern(template.strip())
            for template in poecd_modifier.name_modifier.split(",")
            if template.strip()
        ]
        return any(
            self._tier_matches(item_modifier.tier, filter_)
            and self._matches(
                patterns,
                context.normalized_modifier_text[index],
                condition,
            )
            for index, item_modifier in enumerate(context.item.modifiers)
        )

    @staticmethod
    def _tier_matches(item_tier: int, filter_: RecipeFilter) -> bool:
        return filter_.treshold is None or item_tier >= filter_.treshold

    @staticmethod
    def _matches(
        patterns: list[re.Pattern[str]],
        normalized_text: tuple[str, ...],
        condition: RecipeCondition,
    ) -> bool:
        return all(
            any(
                ModifierPresenceRule._values_match(match, condition)
                for line in normalized_text
                if (match := pattern.fullmatch(line)) is not None
            )
            for pattern in patterns
        )

    @staticmethod
    def _values_match(
        match: re.Match[str],
        condition: RecipeCondition,
    ) -> bool:
        return all(
            ModifierPresenceRule._value_in_range(
                rolled_value(value),
                condition,
            )
            for value in match.groups()
        )

    @staticmethod
    def _value_in_range(
        value: float,
        condition: RecipeCondition,
    ) -> bool:
        if condition.treshold is not None and value < condition.treshold:
            return False
        return condition.max is None or value <= condition.max


def in_condition_range(value: float, condition: RecipeCondition) -> bool:
    minimum = condition.treshold if condition.treshold is not None else 1
    if value < minimum:
        return False
    return condition.max is None or value <= condition.max


class RecipeMethodMatcher:
    """Evaluate a recipe method's filters against a parsed item."""

    def __init__(
        self,
        method: RecipeMethod,
        recipe_data: RecipeData,
        poecd: PoeCd,
        rules: Iterable[ConditionRule] | None = None,
    ) -> None:
        self.method = method
        self.context_data = recipe_data
        self.poecd = poecd
        self.rules = tuple(
            rules
            or (
                OpenAffixRule(),
                OpenPrefixRule(),
                OpenSuffixRule(),
                CountAffixRule(),
                CountPrefixRule(),
                CountSuffixRule(),
                CountAttackRule(),
                CountNonAttackRule(),
                CountCasterRule(),
                CountNonCasterRule(),
                CountInfluencedAffixRule(),
                CountInfluencedPrefixRule(),
                CountInfluencedSuffixRule(),
                FireResistanceRule(),
                ColdResistanceRule(),
                LightningResistanceRule(),
                ChaosResistanceRule(),
                ElementalResistancesRule(),
                TotalResistancesRule(),
                AttributesRule(),
                StrengthRule(),
                DexterityRule(),
                IntelligenceRule(),
                ModifierPresenceRule(),
            )
        )

    def evaluate(self, item: Item) -> bool:
        # Craft methods with no filters pass automatically. A check method with
        # an explicitly empty filter list also has no conditions to reject it.
        if not self.method.filters:
            return True

        context = MatchContext(item, self.context_data, self.poecd)
        and_filters = [
            f for f in self.method.filters if f.type.casefold() == "and"]
        or_filters = [
            f for f in self.method.filters if f.type.casefold() == "or"]
        not_filters = [
            f for f in self.method.filters if f.type.casefold() == "not"]
        unknown = [
            f for f in self.method.filters
            if f.type.casefold() not in {"and", "or", "not"}
        ]
        if unknown:
            names = ", ".join(sorted({f.type for f in unknown}))
            raise ValueError(f"Unsupported recipe filter type(s): {names}")

        # All AND groups must pass. If OR groups exist, at least one must pass.
        # Every NOT group must have none of its conditions succeed.
        return (
            all(self._evaluate_filter(f, context) for f in and_filters)
            and (
                not or_filters
                or any(self._evaluate_filter(f, context) for f in or_filters)
            )
            and all(self._evaluate_filter(f, context) for f in not_filters)
        )

    def _evaluate_filter(
        self,
        filter_: RecipeFilter,
        context: MatchContext,
    ) -> bool:
        results = [
            self._evaluate_condition(condition, context, filter_)
            for condition in filter_.conds
        ]
        if filter_.type.casefold() == "and":
            return all(results)
        if filter_.type.casefold() == "or":
            return any(results)
        if filter_.type.casefold() == "not":
            return not any(results)
        raise ValueError(f"Unsupported recipe filter type: {filter_.type}")

    def _evaluate_condition(
        self,
        condition: RecipeCondition,
        context: MatchContext,
        filter_: RecipeFilter,
    ) -> bool:
        for rule in self.rules:
            if rule.supports(condition):
                return rule.evaluate(condition, context, filter_)
        raise ValueError(f"No condition rule handles {condition.id!r}")


def evaluate_recipe_method(
    method: RecipeMethod,
    recipe_data: RecipeData,
    poecd: PoeCd,
    item: Item,
) -> bool:
    """Convenience function for one-off method evaluation."""
    return RecipeMethodMatcher(method, recipe_data, poecd).evaluate(item)
