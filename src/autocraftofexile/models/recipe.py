from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Self


@dataclass(slots=True, frozen=True)
class AffixGroups:
    prefix: int
    suffix: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            prefix=int(data["prefix"]),
            suffix=int(data["suffix"]),
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
            atype=str(data["atype"]),
            id=str(data["id"]),
            mgrp=str(data["mgrp"]),
            modgroups=tuple(str(value) for value in data["modgroups"]),
            weight=str(data["weight"]),
            nvalues=str(data["nvalues"]),
            tindex=int(data["tindex"]),
            frac=int(data["frac"]),
            maven=int(data["maven"]),
            bench=int(data["bench"]),
            rolls=tuple(int(value) for value in data["rolls"]),
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
            rollable_implicits=int(data["rollable_implicits"]),
            cmodpool=data.get("cmodpool"),
            hmodpool=data.get("hmodpool"),
            maxaffgrp=AffixGroups.from_dict(data["maxaffgrp"]),
            is_rare=int(data["is_rare"]),
            is_fossil=int(data["is_fossil"]),
            is_craftable=int(data["is_craftable"]),
            is_influenced=int(data["is_influenced"]),
            is_essence=int(data["is_essence"]),
            is_catalyst=int(data["is_catalyst"]),
            is_notable=int(data["is_notable"]),
            unique_notable=int(data["unique_notable"]),
            iaffixes=tuple(ItemAffix.from_dict(value)
                           for value in data["iaffixes"]),
            meta_flags=MappingProxyType(data["meta_flags"]),
            imprint=data.get("imprint"),
            enchant=str(data["enchant"]),
            iaffbt=AffixGroups.from_dict(data["iaffbt"]),
            cmaxaffgrp=AffixGroups.from_dict(data["cmaxaffgrp"]),
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
            bgroup=int(data["bgroup"]),
            base=str(data["base"]),
            bitem=str(data["bitem"]),
            ilvl=int(data["ilvl"]),
            rarity=str(data["rarity"]),
            influences=tuple(str(value) for value in data["influences"]),
            quality=int(data["quality"]),
            corrupted=int(data["corrupted"]),
            destroyed=int(data["destroyed"]),
            implicits=tuple(str(value) for value in data["implicits"]),
            veils=tuple(x for x in data["veils"]),
            socketed=tuple(x for x in data["socketed"]),
            sockets=int(data["sockets"]),
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
            id=str(data["id"]),
            treshold=(
                int(data["treshold"])
                if data.get("treshold") is not None
                else None
            ),
            max=int(data["max"]) if data.get("max") is not None else None,
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
            type=str(data["type"]),
            treshold=(
                int(data["treshold"])
                if data.get("treshold") is not None
                else None
            ),
            conds=tuple(RecipeCondition.from_dict(value)
                        for value in data["conds"]),
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
            win=str(data["win"]),
            win_route=(
                str(data["win_route"])
                if data.get("win_route") is not None
                else None
            ),
            fail=str(data["fail"]),
            fail_route=(
                str(data["fail_route"])
                if data.get("fail_route") is not None
                else None
            ),
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
        filters_data = data.get("filters")
        vfilter_data = data.get("vfilter")

        return cls(
            method=tuple(data["method"]),
            mopts=data.get("mopts"),
            autopass=bool(data["autopass"]),
            filters=(
                tuple(RecipeFilter.from_dict(value) for value in filters_data)
                if filters_data is not None
                else None
            ),
            vfilter=tuple(vfilter_data) if vfilter_data is not None else None,
            actions=RecipeActions.from_dict(data["actions"]),
        )


@dataclass(slots=True, frozen=True)
class Recipe:
    settings: RecipeSettings
    data: RecipeData
    config: tuple[RecipeStep, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            settings=RecipeSettings.from_dict(data["settings"]),
            data=RecipeData.from_dict(data["data"]),
            config=tuple(RecipeStep.from_dict(x) for x in data["config"])
        )
