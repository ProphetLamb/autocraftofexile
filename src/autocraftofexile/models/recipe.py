from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Self


@dataclass(slots=True, frozen=True)
class AffixGroups:
    prefix: int
    suffix: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            prefix=data.get("prefix", 0),
            suffix=data.get("suffix", 0),
        )


@dataclass(slots=True, frozen=True)
class ItemAffix:
    atype: str
    id: str
    mgrp: str
    modgroups: tuple[str, ...]
    weight: str
    nvalues: str
    tindex: int
    frac: int
    maven: int
    bench: int
    rolls: tuple[int, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            atype=data.get("atype", ""),
            id=data.get("id", ""),
            mgrp=data.get("mgrp", ""),
            modgroups=tuple(data.get("modgroups", ())),
            weight=data.get("weight", "0"),
            nvalues=data.get("nvalues", "0"),
            tindex=data.get("tindex", 0),
            frac=data.get("frac", 0),
            maven=data.get("maven", 0),
            bench=data.get("bench", 0),
            rolls=tuple(data.get("rolls", ())),
        )


@dataclass(slots=True, frozen=True)
class RecipeData:
    fmodpool: Any | None
    eldritch: Any | None
    dominance: Any | None
    mtypes: Any | None
    implicits: Any | None
    rollable_implicits: int
    cmodpool: Any | None
    hmodpool: Any | None
    maxaffgrp: AffixGroups
    is_rare: int
    is_fossil: int
    is_craftable: int
    is_influenced: int
    is_essence: int
    is_catalyst: int
    is_notable: int
    unique_notable: int
    iaffixes: tuple[ItemAffix, ...]
    meta_flags: Mapping[str, Any]
    imprint: Any | None
    enchant: str
    iaffbt: AffixGroups
    cmaxaffgrp: AffixGroups
    mgrpdata: Any | None
    affbymgrp: Any | None
    veiledmods: Any | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            fmodpool=data.get("fmodpool"),
            eldritch=data.get("eldritch"),
            dominance=data.get("dominance"),
            mtypes=data.get("mtypes"),
            implicits=data.get("implicits"),
            rollable_implicits=data.get("rollable_implicits", 0),
            cmodpool=data.get("cmodpool"),
            hmodpool=data.get("hmodpool"),
            maxaffgrp=AffixGroups.from_dict(data.get("maxaffgrp", {})),
            is_rare=data.get("is_rare", 0),
            is_fossil=data.get("is_fossil", 0),
            is_craftable=data.get("is_craftable", 0),
            is_influenced=data.get("is_influenced", 0),
            is_essence=data.get("is_essence", 0),
            is_catalyst=data.get("is_catalyst", 0),
            is_notable=data.get("is_notable", 0),
            unique_notable=data.get("unique_notable", 0),
            iaffixes=tuple(
                ItemAffix.from_dict(value) for value in data.get("iaffixes", ())
            ),
            meta_flags=MappingProxyType(data.get("meta_flags", {})),
            imprint=data.get("imprint"),
            enchant=data.get("enchant", ""),
            iaffbt=AffixGroups.from_dict(data.get("iaffbt", {})),
            cmaxaffgrp=AffixGroups.from_dict(data.get("cmaxaffgrp", {})),
            mgrpdata=data.get("mgrpdata"),
            affbymgrp=data.get("affbymgrp"),
            veiledmods=data.get("veiledmods"),
        )


@dataclass(slots=True, frozen=True)
class RecipeSettings:
    bgroup: int
    base: str
    bitem: str
    ilvl: int
    rarity: str
    influences: tuple[str, ...]
    quality: int
    corrupted: int
    destroyed: int
    implicits: tuple[str, ...]
    veils: tuple[Any, ...]
    socketed: tuple[Any, ...]
    sockets: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            bgroup=data.get("bgroup", 0),
            base=data.get("base", ""),
            bitem=data.get("bitem", ""),
            ilvl=data.get("ilvl", 0),
            rarity=data.get("rarity", "Normal"),
            influences=tuple(data.get("influences", [])),
            quality=data.get("quality", 0),
            corrupted=data.get("corrupted", 0),
            destroyed=data.get("destroyed", 0),
            implicits=tuple(data.get("implicits", [])),
            veils=tuple(data.get("veils") or []),
            socketed=tuple(data.get("socketed", [])),
            sockets=data.get("sockets") or 0,
        )


@dataclass(slots=True, frozen=True)
class RecipeCondition:
    id: str
    treshold: int | None
    max: int | None
    base: Any | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            id=data.get("id", ""),
            treshold=data.get("treshold"),
            max=data.get("max"),
            base=data.get("base"),
        )


@dataclass(slots=True, frozen=True)
class RecipeFilter:
    type: str
    treshold: int | None
    conds: tuple[RecipeCondition, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            type=str(data.get("type", "")),
            treshold=int(data["treshold"])
            if "treshold" in data and data["treshold"] is not None
            else None,
            conds=tuple(
                RecipeCondition.from_dict(value) for value in data.get("conds", ())
            ),
        )


@dataclass(slots=True, frozen=True)
class RecipeActions:
    win: str
    win_route: str | None
    fail: str
    fail_route: str | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            win=data.get("win", ""),
            win_route=data.get("win_route"),
            fail=data.get("fail", ""),
            fail_route=data.get("fail_route"),
        )


@dataclass(slots=True, frozen=True)
class RecipeStep:
    method: tuple[str | None, ...]
    mopts: Any | None
    autopass: bool
    filters: tuple[RecipeFilter, ...] | None
    vfilter: tuple[Any, ...] | None
    actions: RecipeActions

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        method = tuple(data.get("method", ()))
        mopts = data.get("mopts")
        autopass = bool(data.get("autopass", False))

        filters_raw = data.get("filters")
        filters = (
            tuple(RecipeFilter.from_dict(value) for value in filters_raw)
            if filters_raw is not None
            else None
        )

        vfilter_raw = data.get("vfilter")
        vfilter = tuple(vfilter_raw) if vfilter_raw is not None else None

        return cls(
            method=method,
            mopts=mopts,
            autopass=autopass,
            filters=filters,
            vfilter=vfilter,
            actions=RecipeActions.from_dict(data.get("actions", {})),
        )


@dataclass(slots=True, frozen=True)
class Recipe:
    settings: RecipeSettings
    data: RecipeData
    config: tuple[RecipeStep, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            settings=RecipeSettings.from_dict(data.get("settings", {})),
            data=RecipeData.from_dict(data.get("data", {})),
            config=tuple(RecipeStep.from_dict(x) for x in data.get("config", ())),
        )
