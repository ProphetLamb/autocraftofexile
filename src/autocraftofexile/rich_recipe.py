from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, field

import rich.box
from rich.console import Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .item_match_context import ItemMatchResult
from .models.poecd import PoeCd
from .models.recipe import Recipe, RecipeCondition, RecipeFilter, RecipeStep


@dataclass(slots=True)
class StepStatus:
    active: bool
    result: ItemMatchResult | None = None
    status_info: RenderableType | None = None


CraftingStats = dict[tuple[str | None, ...], int]


def repr_stat_table(stats: CraftingStats) -> RenderableType:
    table = Table(title="Crafting Costs", box=rich.box.ROUNDED)
    table.add_column("Method", justify="right", style="bright_white", no_wrap=True)
    table.add_column("Count", style="cyan")
    for method, count in stats.items():
        if method != ("check",):
            table.add_row(", ".join(x for x in method if x), repr(count))
    return table


def _repr_condition_style(cond: RecipeCondition, status: StepStatus | None):
    if not status or not status.result:
        return "none"
    if cond in status.result.failed:
        return "red"
    if next(
        (
            x
            for x in status.result.modifiers.values()
            if cond in x.attributes or cond in x.text
        ),
        None,
    ):
        return "green"
    return "none"


def repr_condition(
    cond: RecipeCondition, poecd: PoeCd, status: StepStatus | None
) -> str:
    style = _repr_condition_style(cond, status)
    if not cond.id.isdigit():
        return (
            f"[{style}]'{cond.id}({cond.treshold or ''}..{cond.max or ''})'[/{style}]"
        )
    modifier = poecd.modifiers.get(cond.id)
    tier_suffix = (
        f" AT LEAST TIER {cond.treshold}"
        if (cond.treshold or 0) > 1
        else " TIER 1"
        if (cond.treshold or 0) == 1
        else ""
    )
    return (
        f"[{style}]"
        f"{
            f"'{modifier.name_modifier}'{tier_suffix}"
            if modifier != None
            else f"'#{cond.id}'{tier_suffix}"
        }"
        f"[/{style}]"
    )


def repr_filter(
    filter_: RecipeFilter, poecd: PoeCd, status: StepStatus | None = None
) -> str:
    s = ""
    operator = filter_.type.casefold()
    if len(filter_.conds) == 0:
        return "AUTOPASS"
    if len(filter_.conds) == 1 and (filter_.treshold or 1) == 1:
        return repr_condition(filter_.conds[0], poecd, status)
    if filter_.treshold == None:
        s += "ALL OF" if operator != "not" else "NONE OF"
    else:
        s += (
            f"AT LEAST {filter_.treshold} OF"
            if operator != "not"
            else f"FEWER THAN {filter_.treshold} OF"
        )
    s += (
        "(\n    "
        + "\n    ".join(repr_condition(cond, poecd, status) for cond in filter_.conds)
        + "\n  )"
    )
    return s


def repr_filter_group(
    filters: list[RecipeFilter], poecd: PoeCd, status: StepStatus | None = None
) -> str:
    if len(filters) == 1:
        return repr_filter(filters[0], poecd, status)
    if len(filters) == 0:
        return ""
    s = "\n  "
    for i, filter_ in enumerate(filters):
        if i != 0:
            s += "\n  AND "
        s += repr_filter(filter_, poecd, status)
    s += "\n"
    return s


def repr_filters(
    filters: Collection[RecipeFilter], poecd: PoeCd, status: StepStatus | None = None
) -> RenderableType:
    or_filters: list[list[RecipeFilter]] = [[]]
    for x in filters:
        if x.type.casefold() == "or":
            or_filters.append([x])
        else:
            or_filters[-1].append(x)
    return "\n  OR ".join(
        "(" + repr_filter_group(and_filters, poecd, status) + ")"
        for and_filters in or_filters
    )


def repr_step(
    step: RecipeStep, poecd: PoeCd, status: StepStatus | None = None
) -> RenderableType:
    return Group(
        f"apply {', '.join(x for x in step.method if x)}\n"
        f"on success {step.actions.win} {step.actions.win_route or ''}\n"
        f"on failure {step.actions.fail} {step.actions.fail_route or ''}\n"
        f"filters:\n"
        f"{repr_filters(step.filters, poecd, status) if step.filters and not step.autopass else 'AUTOPASS'}",
        status.status_info if status and status.status_info else " ",
    )


def _step_border_style(status: StepStatus | None):
    if not status:
        return "none"
    if status.active:
        return "cyan"
    if not status.result:
        return "none"
    if status.result.failed:
        return "red"
    return "green"


def repr_recipe(
    recipe: Recipe, poecd: PoeCd, statusByStep: dict[RecipeStep, StepStatus]
) -> RenderableType:
    influences = " ".join(
        poecd.mgroups[inf].name_mgroup for inf in recipe.settings.influences
    )
    return Group(
        f"[bold]Crafting {poecd.bitems[recipe.settings.bitem].name_bitem} ilvl {recipe.settings.ilvl} {influences}{' influence' if influences else ''}[/bold]",
        *[
            Panel(
                repr_step(step, poecd, statusByStep.get(step)),
                title=f"Step {i + 1}",
                title_align="left",
                border_style=_step_border_style(statusByStep.get(step)),
                expand=False,
            )
            for i, step in enumerate(recipe.config)
        ],
    )


@dataclass(slots=True)
class RichRecipe:
    recipe: Recipe
    poecd: PoeCd
    live: Live
    appendix: list[RenderableType] = field(default_factory=list[RenderableType])
    status: dict[RecipeStep, StepStatus] = field(
        default_factory=dict[RecipeStep, StepStatus]
    )
    stats: dict[tuple[str | None, ...], int] = field(
        default_factory=dict[tuple[str | None, ...], int]
    )

    def update(self, append: RenderableType | None = None):
        if append:
            self.appendix.append(append)
        self.live.update(self.repr_renderable())

    def repr_renderable(self) -> RenderableType:
        return Group(
            repr_recipe(self.recipe, self.poecd, self.status),
            repr_stat_table(self.stats),
            *self.appendix,
        )

    def inc_stat(self, method: tuple[str | None, ...]):
        self.stats[method] = self.stats.setdefault(method, 0) + 1
