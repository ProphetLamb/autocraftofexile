from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Self, TypeVar

T = TypeVar("T")


@dataclass(slots=True, frozen=True)
class SparseArray[T]:
    """A sparse array contains items in ``seq`` and their index in ``ind``.

    Accessing ``array[key]`` resolves to ``array.seq[array.ind[key]]``.
    """

    seq: tuple[T]
    ind: Mapping[str, int]

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        item_factory: Callable[[Mapping[str, Any]], T],
    ) -> Self:
        return cls(
            seq=tuple[T](
                item_factory(item)
                for item in data.get("seq") or list[Mapping[str, Any]]()
            ),
            ind=MappingProxyType(
                {
                    key: index
                    for key, index in (data.get("ind") or dict[str, int]()).items()
                }
            ),
        )

    def __getitem__(self, key: str) -> T:
        return self.seq[self.ind[key]]

    def __contains__(self, key: object) -> bool:
        return key in self.ind

    def __len__(self) -> int:
        return len(self.seq)

    def __iter__(self) -> Iterator[T]:
        return iter(self.seq)

    def get(self, key: str, default: T | None = None) -> T | None:
        index = self.ind.get(key)
        return default if index is None else self.seq[index]

    def keys(self) -> Iterator[str]:
        return iter(self.ind)

    def values(self) -> Iterator[T]:
        for index in self.ind.values():
            yield self.seq[index]

    def items(self) -> Iterator[tuple[str, T]]:
        for key, index in self.ind.items():
            yield key, self.seq[index]


@dataclass(slots=True, frozen=True)
class BItem:
    id_bitem: str
    id_base: str
    name_bitem: str
    drop_level: str
    properties: str
    requirements: str
    implicits: str
    exp: str
    imgurl: str
    is_legacy: str
    exmods: str | None
    tgb: str | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(**data)


@dataclass(slots=True, frozen=True)
class BItems:
    values: SparseArray[BItem]
    name: Mapping[str, int]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            values=SparseArray[BItem].from_dict(data, BItem.from_dict),
            name=MappingProxyType(data["name"]),
        )

    def __getitem__(self, key: str) -> BItem:
        return self.values[key]

    def by_name(self, name: str) -> BItem:
        return self.values.seq[self.name[name]]


@dataclass(slots=True, frozen=True)
class Base:
    id_bgroup: str
    id_base: str
    name_base: str
    is_jewellery: str
    base_type: str
    has_childs: str
    master_base: str | None
    unique_notable: str
    enchant: str | None
    is_legacy: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(**data)


@dataclass(slots=True, frozen=True)
class Bases:
    values: SparseArray[Base]
    items: Mapping[str, tuple[int, ...]]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            values=SparseArray[Base].from_dict(data, Base.from_dict),
            items=MappingProxyType(
                {
                    str(base_id): tuple(int(index) for index in indices)
                    for base_id, indices in data["items"].items()
                }
            ),
        )

    def __getitem__(self, key: str) -> Base:
        return self.values[key]


@dataclass(slots=True, frozen=True)
class BGroup:
    id_bgroup: str
    name_bgroup: str
    max_affix: str
    is_rare: str
    is_influenced: str
    is_fossil: str
    is_ess: str
    is_craftable: str
    is_notable: str
    is_catalyst: str
    has_items: str
    max_sockets: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(**data)


@dataclass(slots=True, frozen=True)
class Modifier:
    id_modifier: str
    modgroup: str | None
    modgroups: str
    affix: str
    id_mgroup: str
    name_modifier: str
    id_fossil: str | None
    mtypes: str
    meta: str | None
    mtags: str | None
    hybrid: str
    notable: str
    vex: str
    amg: str | None
    exkey: str | None
    ubt: str | None
    tgb: str | None
    ntgb: str
    hr: bool
    ha: bool

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(**data)


@dataclass(slots=True, frozen=True)
class MGroup:
    is_influence: str
    id_mgroup: str
    name_mgroup: str
    poedb_id: str | None
    paste_link: str | None
    is_main: str
    max_chosen: str
    is_compute: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(**data)


@dataclass(slots=True, frozen=True)
class MType:
    id_mtype: str
    poedb_id: str
    jewellery_tag: str
    harvest: str
    tangled: str
    parent_id: str | None
    name_mtype: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(**data)


@dataclass(slots=True, frozen=True)
class AliasModifier:
    mgroup: str
    modid: str
    tier: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(**data)


@dataclass(slots=True, frozen=True)
class Aliases:
    """Aliases indexed by base ID, affix type, and displayed modifier name."""

    values: Mapping[str, Mapping[str, Mapping[str, tuple[AliasModifier, ...]]]]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            values=MappingProxyType(
                {
                    base_id: MappingProxyType(
                        {
                            affix: MappingProxyType(
                                {
                                    modifier_name: tuple(
                                        AliasModifier.from_dict(entry)
                                        for entry in entries
                                    )
                                    for modifier_name, entries in modifiers.items()
                                }
                            )
                            for affix, modifiers in affixes.items()
                        }
                    )
                    for base_id, affixes in data.items()
                }
            )
        )

    def __getitem__(
        self, base_id: str
    ) -> Mapping[str, Mapping[str, tuple[AliasModifier, ...]]]:
        return self.values[base_id]


@dataclass(slots=True, frozen=True)
class ModifierTier:
    ilvl: str
    weighting: str
    nvalues: str
    tord: int
    alias: str | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(**data)


@dataclass(slots=True, frozen=True)
class Tiers:
    """Tiers indexed by modifier ID and then base/group ID."""

    values: Mapping[str, Mapping[str, tuple[ModifierTier, ...]]]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            values=MappingProxyType(
                {
                    modifier_id: MappingProxyType(
                        {
                            group_id: tuple(
                                ModifierTier.from_dict(tier) for tier in tiers
                            )
                            for group_id, tiers in groups.items()
                        }
                    )
                    for modifier_id, groups in data.items()
                }
            )
        )

    def __getitem__(self, modifier_id: str) -> Mapping[str, tuple[ModifierTier, ...]]:
        return self.values[modifier_id]


@dataclass(slots=True, frozen=True)
class PoeCd:
    bitems: BItems
    bases: Bases
    bgroups: SparseArray[BGroup]
    modifiers: SparseArray[Modifier]
    mgroups: SparseArray[MGroup]
    mtypes: SparseArray[MType]
    aliases: Aliases
    tiers: Tiers

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            bitems=BItems.from_dict(data.get("bitems") or {}),
            bases=Bases.from_dict(data.get("bases") or {}),
            bgroups=SparseArray[BGroup].from_dict(
                data.get("bgroups") or {}, BGroup.from_dict
            ),
            modifiers=SparseArray[Modifier].from_dict(
                data.get("modifiers") or {}, Modifier.from_dict
            ),
            mgroups=SparseArray[MGroup].from_dict(
                data.get("mgroups") or {}, MGroup.from_dict
            ),
            mtypes=SparseArray[MType].from_dict(
                data.get("mtypes") or {}, MType.from_dict
            ),
            aliases=Aliases.from_dict(data.get("aliases") or {}),
            tiers=Tiers.from_dict(data.get("tiers") or {}),
        )
