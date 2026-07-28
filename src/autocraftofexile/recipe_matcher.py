from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Iterable

from autocraftofexile.models.item import Item, ItemModifier
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

RecipeConditions = set[RecipeCondition]


@dataclass(slots=True, frozen=True)
class ModifierMatchResult:
    attributes: RecipeConditions = field(default_factory=set[RecipeCondition])
    text: RecipeConditions = field(default_factory=set[RecipeCondition])


@dataclass(slots=True)
class ItemMatchResult:
    success: bool
    modifiers: dict[ItemModifier, ModifierMatchResult] = field(
        default_factory=dict[ItemModifier, ModifierMatchResult]
    )
    failed: RecipeConditions = field(default_factory=set[RecipeCondition])

    def merge(self, other: ItemMatchResult) -> None:
        self.success = self.success and other.success
        self.failed.update(other.failed)
        for item_modifier, other_modifier in other.modifiers.items():
            modifier = self.modifiers.setdefault(
                item_modifier, ModifierMatchResult()
            )
            modifier.attributes.update(other_modifier.attributes)
            modifier.text.update(other_modifier.text)


def normalize_modifier_text(value: str) -> str:
    return " ".join(value.replace("\u2013", "-").replace("\u2014", "-").split())


def rolled_value(value: str) -> float:
    return float(value.split("(", maxsplit=1)[0])


def modifier_template_pattern(template: str) -> re.Pattern[str]:
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


def in_condition_range(value: float, condition: RecipeCondition) -> bool:
    minimum = condition.treshold if condition.treshold is not None else 1
    return value >= minimum and (condition.max is None or value <= condition.max)


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
        object.__setattr__(self, "prefix_count", self._count_slot("prefix"))
        object.__setattr__(self, "suffix_count", self._count_slot("suffix"))
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
            self, "resistance_templates", self._build_resistance_templates()
        )
        object.__setattr__(
            self, "attribute_templates", self._build_attribute_templates()
        )
        object.__setattr__(
            self,
            "normalized_modifier_text",
            tuple(
                tuple(normalize_modifier_text(line) for line in modifier.text)
                for modifier in self.item.modifiers
            ),
        )

    def _count_slot(self, slot: str) -> int:
        return sum(m.slot.casefold() == slot for m in self.item.modifiers)

    @property
    def open_prefixes(self) -> int:
        return max(0, self.recipe_data.maxaffgrp.prefix - self.prefix_count)

    @property
    def open_suffixes(self) -> int:
        return max(0, self.recipe_data.maxaffgrp.suffix - self.suffix_count)

    def _build_templates(
        self,
        classifier: Callable[[str], frozenset[str]],
    ) -> tuple[tuple[re.Pattern[str], frozenset[str]], ...]:
        templates: dict[str, tuple[str, frozenset[str]]] = {}
        for modifier in self.poecd.modifiers:
            for component in modifier.name_modifier.split(","):
                template = normalize_modifier_text(component.strip())
                affected = classifier(template)
                if affected:
                    templates.setdefault(
                        template.casefold(), (template, affected))
        return tuple(
            (modifier_template_pattern(template), affected)
            for template, affected in templates.values()
        )

    def _build_resistance_templates(
        self,
    ) -> tuple[tuple[re.Pattern[str], frozenset[str]], ...]:
        return self._build_templates(self._affected_resistances)

    def _build_attribute_templates(
        self,
    ) -> tuple[tuple[re.Pattern[str], frozenset[str]], ...]:
        return self._build_templates(self._affected_attributes)

    @staticmethod
    def _affected_resistances(template: str) -> frozenset[str]:
        value = template.casefold()
        if not re.search(r"\bto\b.*\bresistances?\b", value):
            return frozenset()
        if any(x in value for x in ("maximum", "penetrate", "monster", "player")):
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

    @staticmethod
    def _affected_attributes(template: str) -> frozenset[str]:
        value = template.casefold()
        if not re.search(r"(?:^|\s)[+]?#+\s+to\s+", value) or "%" in value:
            return frozenset()
        if "all attributes" in value:
            return frozenset({"strength", "dexterity", "intelligence"})
        return frozenset(
            attribute
            for attribute in ("strength", "dexterity", "intelligence")
            if re.search(rf"\b{attribute}\b", value)
        )


class MatchRule(ABC):
    @abstractmethod
    def supports(self, condition: RecipeCondition) -> bool:
        pass

    @abstractmethod
    def evaluate(
        self,
        condition: RecipeCondition,
        context: MatchContext,
        filter_: RecipeFilter,
    ) -> ItemMatchResult:
        pass

    @staticmethod
    def result(
        success: bool,
        condition: RecipeCondition,
        *,
        attribute_modifiers: Iterable[ItemModifier] = (),
        text_modifiers: Iterable[ItemModifier] = (),
    ) -> ItemMatchResult:
        if not success:
            return ItemMatchResult(False, failed={condition})

        result = ItemMatchResult(True)
        for item_modifier in attribute_modifiers:
            result.modifiers.setdefault(
                item_modifier, ModifierMatchResult()
            ).attributes.add(condition)
        for item_modifier in text_modifiers:
            result.modifiers.setdefault(
                item_modifier, ModifierMatchResult()
            ).text.add(condition)
        return result


@dataclass(slots=True, frozen=True)
class NamedRuleResult:
    value: float
    attributes: set[ItemModifier] = field(
        default_factory=set[ItemModifier]
    )
    text: set[ItemModifier] = field(
        default_factory=set[ItemModifier]
    )


class NamedRule(MatchRule, ABC):
    condition_id: str

    def supports(self, condition: RecipeCondition) -> bool:
        return condition.id == self.condition_id

    def evaluate(
        self,
        condition: RecipeCondition,
        context: MatchContext,
        filter_: RecipeFilter,
    ) -> ItemMatchResult:
        del filter_

        match = self.match(context)

        return self.result(
            in_condition_range(match.value, condition),
            condition,
            attribute_modifiers=match.attributes,
            text_modifiers=match.text,
        )

    @abstractmethod
    def match(self, context: MatchContext) -> NamedRuleResult:
        pass


class OpenSlotRule(NamedRule):
    slot: str | None = None

    def match(
        self, context: MatchContext
    ) -> NamedRuleResult:
        if self.slot == "prefix":
            return NamedRuleResult(float(context.open_prefixes))
        if self.slot == "suffix":
            return NamedRuleResult(float(context.open_suffixes))
        return NamedRuleResult(float(context.open_prefixes + context.open_suffixes))


class OpenAffixRule(OpenSlotRule):
    condition_id = "open_affix"


class OpenPrefixRule(OpenSlotRule):
    condition_id = "open_prefix"
    slot = "prefix"


class OpenSuffixRule(OpenSlotRule):
    condition_id = "open_suffix"
    slot = "suffix"


class CountSlotRule(NamedRule):
    slots: frozenset[str]

    def match(
        self, context: MatchContext
    ) -> NamedRuleResult:
        modifiers = {
            modifier for modifier in context.item.modifiers
            if modifier.slot.casefold() in self.slots
        }
        return NamedRuleResult(float(len(modifiers)))


class CountAffixRule(CountSlotRule):
    condition_id = "count_affix"
    slots = frozenset({"prefix", "suffix"})


class CountPrefixRule(CountSlotRule):
    condition_id = "count_prefix"
    slots = frozenset({"prefix"})


class CountSuffixRule(CountSlotRule):
    condition_id = "count_suffix"
    slots = frozenset({"suffix"})


class AttributeCountRule(NamedRule):
    attribute: str
    negate = False

    def match(
        self, context: MatchContext
    ) -> NamedRuleResult:
        expected = self.attribute.casefold()
        modifiers: set[ItemModifier] = set()
        for modifier in context.item.modifiers:
            if modifier.slot.casefold() not in {"prefix", "suffix"}:
                continue
            contains = any(
                a.casefold() == expected for a in modifier.attributes)
            if (not contains) if self.negate else contains:
                modifiers.add(modifier)
        return NamedRuleResult(float(len(modifiers)), modifiers)


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


class InfluencedAffixRule(NamedRule):
    slots: frozenset[str]

    def match(
        self, context: MatchContext
    ) -> NamedRuleResult:
        influenced_names = {
            name.casefold()
            for influence in context.influence_names
            for name in (f"of the {influence}", f"The {influence}'s")
        }
        modifiers = {
            modifier
            for modifier in context.item.modifiers
            if modifier.slot.casefold() in self.slots
            and modifier.name.casefold() in influenced_names
        }
        return NamedRuleResult(float(len(modifiers)), text=modifiers)


class CountInfluencedAffixRule(InfluencedAffixRule):
    condition_id = "count_iaffix"
    slots = frozenset({"prefix", "suffix"})


class CountInfluencedPrefixRule(InfluencedAffixRule):
    condition_id = "count_iprefix"
    slots = frozenset({"prefix"})


class CountInfluencedSuffixRule(InfluencedAffixRule):
    condition_id = "count_isuffix"
    slots = frozenset({"suffix"})


class TemplateValueRule(NamedRule):
    affected: frozenset[str]
    template_kind: str

    def match(
        self, context: MatchContext
    ) -> NamedRuleResult:
        templates = (
            context.resistance_templates
            if self.template_kind == "resistance"
            else context.attribute_templates
        )
        total = 0.0
        modifiers: set[ItemModifier] = set()
        for item_modifier, lines in zip(
            context.item.modifiers,
            context.normalized_modifier_text,
            strict=True,
        ):
            for line in lines:
                contribution = self._line_contribution(line, templates)
                if contribution is not None:
                    total += contribution
                    modifiers.add(item_modifier)
        return NamedRuleResult(total, text=modifiers)

    def _line_contribution(
        self, line: str,
        templates: tuple[tuple[re.Pattern[str], frozenset[str]], ...],
    ) -> float | None:
        for pattern, affected in templates:
            match = pattern.fullmatch(line)
            if match is None:
                continue
            multiplier = len(affected & self.affected)
            if multiplier:
                return sum(rolled_value(value) for value in match.groups()) * multiplier
        return None


class FireResistanceRule(TemplateValueRule):
    condition_id = "pseudo_fire_resist"
    affected = frozenset({"fire"})
    template_kind = "resistance"


class ColdResistanceRule(TemplateValueRule):
    condition_id = "pseudo_cold_resist"
    affected = frozenset({"cold"})
    template_kind = "resistance"


class LightningResistanceRule(TemplateValueRule):
    condition_id = "pseudo_lightning_resist"
    affected = frozenset({"lightning"})
    template_kind = "resistance"


class ChaosResistanceRule(TemplateValueRule):
    condition_id = "pseudo_chaos_resist"
    affected = frozenset({"chaos"})
    template_kind = "resistance"


class ElementalResistancesRule(TemplateValueRule):
    condition_id = "pseudo_elemental_resists"
    affected = frozenset({"fire", "cold", "lightning"})
    template_kind = "resistance"


class TotalResistancesRule(TemplateValueRule):
    condition_id = "pseudo_total_resists"
    affected = frozenset({"fire", "cold", "lightning", "chaos"})
    template_kind = "resistance"


class AttributesRule(TemplateValueRule):
    condition_id = "pseudo_attributes"
    affected = frozenset({"strength", "dexterity", "intelligence"})
    template_kind = "attribute"


class StrengthRule(TemplateValueRule):
    condition_id = "pseudo_strength"
    affected = frozenset({"strength"})
    template_kind = "attribute"


class DexterityRule(TemplateValueRule):
    condition_id = "pseudo_dexterity"
    affected = frozenset({"dexterity"})
    template_kind = "attribute"


class IntelligenceRule(TemplateValueRule):
    condition_id = "pseudo_intelligence"
    affected = frozenset({"intelligence"})
    template_kind = "attribute"


class ModifierPresenceRule(MatchRule):
    def supports(self, condition: RecipeCondition) -> bool:
        return condition.id.isdigit()

    def evaluate(
        self, condition: RecipeCondition,
        context: MatchContext, filter_: RecipeFilter,
    ) -> ItemMatchResult:
        poecd_modifier = context.poecd.modifiers.get(condition.id)
        if poecd_modifier is None:
            return self.result(False, condition)
        patterns = [
            modifier_template_pattern(template.strip())
            for template in poecd_modifier.name_modifier.split(",")
            if template.strip()
        ]
        modifiers = {
            item_modifier
            for item_modifier, text in zip(
                context.item.modifiers,
                context.normalized_modifier_text,
                strict=True,
            )
            if (filter_.treshold is None or item_modifier.tier >= filter_.treshold)
            and self._matches(patterns, text, condition)
        }
        return self.result(
            bool(modifiers), condition, text_modifiers=modifiers
        )

    @staticmethod
    def _matches(
        patterns: list[re.Pattern[str]],
        text: tuple[str, ...],
        condition: RecipeCondition,
    ) -> bool:
        return all(
            any(
                all(
                    in_condition_range(rolled_value(value), condition)
                    for value in match.groups()
                )
                for line in text
                if (match := pattern.fullmatch(line)) is not None
            )
            for pattern in patterns
        )


DEFAULT_RULES: tuple[MatchRule, ...] = (
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


class RecipeMethodMatcher:
    def __init__(
        self, method: RecipeMethod, recipe_data: RecipeData, poecd: PoeCd,
        rules: Iterable[MatchRule] | None = None,
    ) -> None:
        self.method = method
        self.recipe_data = recipe_data
        self.poecd = poecd
        self.rules = DEFAULT_RULES if rules is None else tuple(rules)

    def evaluate(self, item: Item) -> ItemMatchResult:
        if not self.method.filters:
            return ItemMatchResult(True)

        context = MatchContext(item, self.recipe_data, self.poecd)
        aggregate = ItemMatchResult(True)
        filter_results: list[tuple[str, bool]] = []
        for filter_ in self.method.filters:
            filter_type = filter_.type.casefold()
            if filter_type not in {"and", "or", "not"}:
                raise ValueError(
                    f"Unsupported recipe filter type: {filter_.type}")
            condition_results: list[bool] = []
            for condition in filter_.conds:
                result = self._rule_for(condition).evaluate(
                    condition, context, filter_
                )
                condition_results.append(result.success)
                aggregate.merge(result)

            passed = (
                all(condition_results) if filter_type == "and"
                else any(condition_results) if filter_type == "or"
                else not any(condition_results)
            )
            filter_results.append((filter_type, passed))

        and_results = [x for kind, x in filter_results if kind == "and"]
        or_results = [x for kind, x in filter_results if kind == "or"]
        not_results = [x for kind, x in filter_results if kind == "not"]
        aggregate.success = (
            all(and_results)
            and (not or_results or any(or_results))
            and all(not_results)
        )
        return aggregate

    def _rule_for(self, condition: RecipeCondition) -> MatchRule:
        for rule in self.rules:
            if rule.supports(condition):
                return rule
        raise ValueError(f"No condition rule handles {condition.id!r}")


def evaluate_recipe_method(
    method: RecipeMethod,
    recipe_data: RecipeData,
    poecd: PoeCd,
    item: Item,
) -> ItemMatchResult:
    return RecipeMethodMatcher(method, recipe_data, poecd).evaluate(item)
