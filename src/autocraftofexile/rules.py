import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable

from .item_match_context import (
    ItemMatchContext,
    ItemMatchResult,
    ModifierMatchResult,
    in_condition_range,
    modifier_template_pattern,
    rolled_value,
)
from .models.item import ItemModifier
from .models.recipe import RecipeCondition, RecipeFilter


class Rule(ABC):
    @abstractmethod
    def supports(self, condition: RecipeCondition) -> bool:
        pass

    @abstractmethod
    def evaluate(
        self,
        condition: RecipeCondition,
        context: ItemMatchContext,
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


class NamedRule(Rule, ABC):
    condition_id: str

    def supports(self, condition: RecipeCondition) -> bool:
        return condition.id == self.condition_id

    def evaluate(
        self,
        condition: RecipeCondition,
        context: ItemMatchContext,
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
    def match(self, context: ItemMatchContext) -> NamedRuleResult:
        pass


class OpenAffixRule(NamedRule):
    condition_id = "open_affix"

    def match(self, context: ItemMatchContext) -> NamedRuleResult:
        return NamedRuleResult(float(context.open_prefixes + context.open_suffixes))


class OpenPrefixRule(NamedRule):
    condition_id = "open_prefix"

    def match(self, context: ItemMatchContext) -> NamedRuleResult:
        return NamedRuleResult(float(context.open_prefixes))


class OpenSuffixRule(NamedRule):
    condition_id = "open_suffix"

    def match(self, context: ItemMatchContext) -> NamedRuleResult:
        return NamedRuleResult(float(context.open_suffixes))


class CountSlotRule(NamedRule):
    slots: frozenset[str]

    def match(
        self, context: ItemMatchContext
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


class ModifierAttributeRule(NamedRule):
    attribute: str
    negate = False

    def match(
        self, context: ItemMatchContext
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
        return NamedRuleResult(float(len(modifiers)), attributes=modifiers)


class ModifierAttackRule(ModifierAttributeRule):
    condition_id = "count_attack"
    attribute = "Attack"


class ModifierNonAttackRule(ModifierAttributeRule):
    condition_id = "count_nattack"
    attribute = "Attack"
    negate = True


class ModifierCasterRule(ModifierAttributeRule):
    condition_id = "count_caster"
    attribute = "Caster"


class ModifierNonCasterRule(ModifierAttributeRule):
    condition_id = "count_ncaster"
    attribute = "Caster"
    negate = True


class InfluencedRule(NamedRule):
    slots: frozenset[str]

    def match(
        self, context: ItemMatchContext
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


class CountInfluencedAffixRule(InfluencedRule):
    condition_id = "count_iaffix"
    slots = frozenset({"prefix", "suffix"})


class CountInfluencedPrefixRule(InfluencedRule):
    condition_id = "count_iprefix"
    slots = frozenset({"prefix"})


class CountInfluencedSuffixRule(InfluencedRule):
    condition_id = "count_isuffix"
    slots = frozenset({"suffix"})


class TemplateRule(NamedRule):
    affected: frozenset[str]

    @abstractmethod
    def templates(self, context: ItemMatchContext) -> tuple[
        tuple[re.Pattern[str], frozenset[str]], ...
    ]:
        pass

    def match(
        self, context: ItemMatchContext
    ) -> NamedRuleResult:
        total = 0.0
        modifiers: set[ItemModifier] = set()
        for item_modifier, lines in zip(
            context.item.modifiers,
            context.normalized_modifier_text,
            strict=True,
        ):
            for line in lines:
                contribution = self._line_contribution(
                    line, self.templates(context))
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


class ResistanceRule(TemplateRule):
    def templates(self, context: ItemMatchContext) -> tuple[tuple[re.Pattern[str], frozenset[str]], ...]:
        return context.resistance_templates


class AttributeRule(TemplateRule):
    def templates(self, context: ItemMatchContext) -> tuple[tuple[re.Pattern[str], frozenset[str]], ...]:
        return context.attribute_templates


class FireResistanceRule(ResistanceRule):
    condition_id = "pseudo_fire_resist"
    affected = frozenset({"fire"})


class ColdResistanceRule(ResistanceRule):
    condition_id = "pseudo_cold_resist"
    affected = frozenset({"cold"})


class LightningResistanceRule(ResistanceRule):
    condition_id = "pseudo_lightning_resist"
    affected = frozenset({"lightning"})


class ChaosResistanceRule(ResistanceRule):
    condition_id = "pseudo_chaos_resist"
    affected = frozenset({"chaos"})


class ElementalResistancesRule(ResistanceRule):
    condition_id = "pseudo_elemental_resists"
    affected = frozenset({"fire", "cold", "lightning"})


class TotalResistancesRule(ResistanceRule):
    condition_id = "pseudo_total_resists"
    affected = frozenset({"fire", "cold", "lightning", "chaos"})


class AttributesRule(AttributeRule):
    condition_id = "pseudo_attributes"
    affected = frozenset({"strength", "dexterity", "intelligence"})


class StrengthRule(AttributeRule):
    condition_id = "pseudo_strength"
    affected = frozenset({"strength"})


class DexterityRule(AttributeRule):
    condition_id = "pseudo_dexterity"
    affected = frozenset({"dexterity"})


class IntelligenceRule(AttributeRule):
    condition_id = "pseudo_intelligence"
    affected = frozenset({"intelligence"})


class ModifierPresentRule(Rule):
    def supports(self, condition: RecipeCondition) -> bool:
        return condition.id.isdigit()

    def evaluate(
        self, condition: RecipeCondition,
        context: ItemMatchContext, filter_: RecipeFilter,
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
        patterns: Iterable[re.Pattern[str]],
        text: Iterable[str],
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


class ItemPropertyRule(NamedRule):
    """Base class for pseudo rules derived from immutable item properties."""

    def match(self, context: ItemMatchContext) -> NamedRuleResult:
        return NamedRuleResult(self.value(context))

    def value(self, context: ItemMatchContext) -> float:
        raise NotImplementedError


class TotalDpsRule(ItemPropertyRule):
    condition_id = "pseudo_total_dps"

    def value(self, context: ItemMatchContext) -> float:
        average_hit = (
            context.physical_damage
            + context.elemental_damage
            + context.chaos_damage
        )
        return average_hit * context.attack_rate


class ElementalDpsRule(ItemPropertyRule):
    condition_id = "pseudo_elemental_dps"

    def value(self, context: ItemMatchContext) -> float:
        return context.elemental_damage * context.attack_rate


class PhysicalDpsRule(ItemPropertyRule):
    condition_id = "pseudo_physical_dps"

    def value(self, context: ItemMatchContext) -> float:
        return context.physical_damage * context.attack_rate


class PhysicalDamageRule(ItemPropertyRule):
    condition_id = "pseudo_physical_damage"

    def value(self, context: ItemMatchContext) -> float:
        return context.physical_damage


class ElementalDamageRule(ItemPropertyRule):
    condition_id = "pseudo_elemental_damage"

    def value(self, context: ItemMatchContext) -> float:
        return context.elemental_damage


DEFAULT_RULES: tuple[Rule, ...] = (
    OpenAffixRule(),
    OpenPrefixRule(),
    OpenSuffixRule(),
    CountAffixRule(),
    CountPrefixRule(),
    CountSuffixRule(),
    ModifierAttackRule(),
    ModifierNonAttackRule(),
    ModifierCasterRule(),
    ModifierNonCasterRule(),
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
    ModifierPresentRule(),
    TotalDpsRule(),
    ElementalDpsRule(),
    PhysicalDpsRule(),
    PhysicalDamageRule(),
    ElementalDamageRule(),
)
