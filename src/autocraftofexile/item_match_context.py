from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Collection, List

from .models.item import Item, ItemModifier
from .models.poecd import PoeCd
from .models.recipe import Recipe, RecipeCondition, RecipeData, RecipeFilter, RecipeStep
from .item_parser import ITEM_DETAIL_BY_RARITY, RarityItemDetails

RecipeConditions = set[RecipeCondition]

_NUMBER_RE = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)")
_NUMBER_RANGE_RE = rf"{_NUMBER_RE.pattern}(?:\({_NUMBER_RE.pattern}-{_NUMBER_RE.pattern}\))?"
_SPACE_RE = r"\s+"

_DAMAGE_RANGE_RE = re.compile(
    fr"(?P<minimum>{_NUMBER_RE.pattern})"
    r"\s*-\s*"
    fr"(?P<maximum>{_NUMBER_RE.pattern})"
)


def repr_condition(cond: RecipeCondition, poecd: PoeCd):
    if not cond.id.isdigit():
        return f"{cond.id}({cond.treshold or ""}..{cond.max or ""})"
    modifier = poecd.modifiers.get(cond.id)
    tier_suffix = f" tier>={cond.treshold}" if (cond.treshold or 0) > 1 else ""
    return f"{modifier.name_modifier}{tier_suffix}" if modifier != None else f"#{cond.id}{tier_suffix}"


def repr_filter(filter_: RecipeFilter, poecd: PoeCd, filter_sep=", "):
    s = ""
    operator = filter_.type.casefold()
    if len(filter_.conds) == 0:
        return "AUTOPASS"
    if len(filter_.conds) == 1 and (filter_.treshold or 1) == 1:
        return repr_condition(filter_.conds[0], poecd)
    if filter_.treshold == None:
        s += "ALL OF" if operator != "not" else "NONE OF"
    else:
        s += f"At LEAST {filter_.treshold} OF" if operator != "not" else f"FEWER THAN {filter_.treshold} OF"
    s += "(" + filter_sep.join(
        "[" + repr_condition(cond, poecd) + "]"
        for cond in filter_.conds
    ) + ")"
    return s


def repr_filter_group(filters: List[RecipeFilter], poecd: PoeCd, filter_sep=", "):
    if len(filters) == 1:
        return repr_filter(filters[0], poecd, filter_sep)
    s = ""
    for filter_ in filters:
        if len(s) != 0:
            s += " AND "
        s += repr_filter(filter_, poecd, filter_sep)
    return s


def repr_filters(filters: Collection[RecipeFilter], poecd: PoeCd, group_sep=", "):
    or_filters: list[list[RecipeFilter]] = [[]]
    for x in filters:
        if x.type.casefold() == "or":
            or_filters.append([x])
        else:
            or_filters[-1].append(x)
    return f"{group_sep}OR ".join("(" + repr_filter_group(and_filters, poecd) + ")" for and_filters in or_filters)


def repr_step(step: RecipeStep, poecd: PoeCd, indent=""):
    return (
        f"{indent}apply {step.method!r}\n"
        f"{indent}on success {step.actions.win} {step.actions.win_route or ""}\n"
        f"{indent}on failure {step.actions.fail} {step.actions.fail_route or ""}\n"
        f"{indent}filters:\n"
        f"{indent}  {repr_filters(step.filters, poecd, "\n" + indent + "  ") if step.filters and not step.autopass else "AUTOPASS"}"
    )


def repr_recipe(recipe: Recipe, poecd: PoeCd):
    influences = " ".join(poecd.mgroups[inf].name_mgroup for inf in recipe.settings.influences)
    return (
        f"Crafting {poecd.bitems[recipe.settings.bitem].name_bitem} ilvl {recipe.settings.ilvl} {influences}{" influence" if influences else ""}"
        f"\n{"\n\n".join(f"Step {i+1}\n" + repr_step(step, poecd, indent="  ") for i, step in enumerate(recipe.config))}"
    )


def _repr_condition_set(conditions: RecipeConditions) -> str:
    return "\n".join(
        f"- {condition!r}"
        for condition in conditions
    )


def in_condition_range(value: float, condition: RecipeCondition) -> bool:
    minimum = condition.treshold if condition.treshold is not None else 1
    return value >= minimum and (condition.max is None or value <= condition.max)


def rolled_value(value: str) -> float:
    return float(value.split("(", maxsplit=1)[0])


def roll_range(value: str):
    for match in _DAMAGE_RANGE_RE.finditer(value):
        yield (float(match.group("minimum")), float(match.group("maximum")))


def average_damage(value: str | None) -> float:
    """Return the sum of the averages of all damage ranges in a property.

    Examples:
        ``72-120`` -> 96
        ``10-20, 5-15, 1-3`` -> 27

    Additional display text such as ``(augmented)`` is ignored.
    """
    if value is None:
        return 0.0

    return sum(
        (min + max) / 2
        for min, max in roll_range(value)
    )


def attacks_per_second(value: str | None) -> float:
    """Extract the numeric attacks-per-second value from an item property."""
    if value is None:
        return 0.0

    match = _NUMBER_RE.search(value)
    return 0.0 if match is None else float(match.group())


def normalize_modifier_text(value: str) -> str:
    return " ".join(value.replace("\u2013", "-").replace("\u2014", "-").split())


def modifier_template_pattern(template: str) -> re.Pattern[str]:
    parts = re.split(r"(#|\s+)", normalize_modifier_text(template))
    pattern: list[str] = []
    for part in parts:
        if not part:
            continue
        if part == "#":
            pattern.append(f"({_NUMBER_RANGE_RE})")
        elif part.isspace():
            pattern.append(_SPACE_RE)
        else:
            pattern.append(re.escape(part))
    return re.compile("".join(pattern), re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class ModifierMatchResult:
    attributes: RecipeConditions = field(default_factory=RecipeConditions)
    text: RecipeConditions = field(default_factory=RecipeConditions)

    def __repr__(self) -> str:
        sections: list[str] = []

        if self.attributes:
            sections.append(
                "Attribute conditions:\n"
                f"{_repr_condition_set(self.attributes)}"
            )

        if self.text:
            sections.append(
                "Text conditions:\n"
                f"{_repr_condition_set(self.text)}"
            )

        return "\n".join(sections) if sections else "No matching conditions"


@dataclass(slots=True)
class ItemMatchResult:
    success: bool
    modifiers: dict[ItemModifier, ModifierMatchResult] = field(
        default_factory=dict[ItemModifier, ModifierMatchResult]
    )
    failed: RecipeConditions = field(default_factory=RecipeConditions)

    def merge(self, other: ItemMatchResult) -> None:
        self.success = self.success and other.success
        self.failed.update(other.failed)

        for item_modifier, other_modifier in other.modifiers.items():
            modifier = self.modifiers.setdefault(
                item_modifier,
                ModifierMatchResult(),
            )
            modifier.attributes.update(other_modifier.attributes)
            modifier.text.update(other_modifier.text)

    def negate(self) -> None:
        self.success = not self.success
        self.failed.clear()

        for modifier in self.modifiers.values():
            self.failed.update(modifier.attributes)
            self.failed.update(modifier.text)

    def __repr__(self) -> str:
        sections = [f"Success: {self.success}"]

        if self.modifiers:
            modifier_sections = [
                "\n".join((
                    repr(item_modifier),
                    repr(match_result),
                ))
                for item_modifier, match_result in self.modifiers.items()
            ]
            sections.append(
                "Matched modifiers:\n"
                + "\n--------\n".join(modifier_sections)
            )

        if self.failed:
            sections.append(
                "Failed conditions:\n"
                f"{_repr_condition_set(self.failed)}"
            )

        return "\n========\n".join(sections)


@dataclass(frozen=True, slots=True)
class ItemMatchContext:
    item: Item
    recipe_data: RecipeData
    poecd: PoeCd
    prefix_count: int = field(init=False)
    suffix_count: int = field(init=False)
    attack_rate: float = field(init=False)
    physical_damage: float = field(init=False)
    elemental_damage: float = field(init=False)
    chaos_damage: float = field(init=False)
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
            "attack_rate",
            attacks_per_second(self.item.properties.attacks_per_second),
        )
        object.__setattr__(
            self,
            "physical_damage",
            average_damage(self.item.properties.physical_damage),
        )
        object.__setattr__(
            self,
            "elemental_damage",
            average_damage(self.item.properties.elemental_damage),
        )
        object.__setattr__(
            self,
            "chaos_damage",
            average_damage(self.item.properties.chaos_damage),
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

    def _count_slot(self, slot: str) -> int:
        return sum(
            modifier.slot.casefold() == slot
            for modifier in self.item.modifiers
        )

    @property
    def open_prefixes(self) -> int:
        max_prefix = self.recipe_data.maxaffgrp.prefix
        max_prefix = min(
            max_affix.prefix,
            max_prefix
        ) if (max_affix := self.rarity_details.max_affix) else max_prefix
        return max(0, max_prefix - self.prefix_count)

    @property
    def open_suffixes(self) -> int:
        max_suffix = self.recipe_data.maxaffgrp.suffix
        max_suffix = min(
            max_affix.suffix,
            max_suffix
        ) if (max_affix := self.rarity_details.max_affix) else max_suffix
        return max(0, max_suffix - self.suffix_count)

    @property
    def rarity_details(self) -> RarityItemDetails:
        return ITEM_DETAIL_BY_RARITY[self.item.ident.rarity.casefold()]

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
                        template.casefold(),
                        (template, affected),
                    )

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
