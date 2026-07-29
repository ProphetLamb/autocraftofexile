import json
from typing import Any, Mapping

from autocraftofexile.models.recipe import RecipeData, RecipeSettings, RecipeStep
from tests import RECIPE_EXAMPLE


def load_recipe_json() -> Mapping[str, Any]:
    with RECIPE_EXAMPLE.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_parse_recipe_settings() -> None:
    settings = RecipeSettings.from_dict(load_recipe_json()["settings"])

    assert settings.bgroup == 7
    assert settings.base == "21"
    assert settings.bitem == "8114"
    assert settings.ilvl == 85
    assert settings.rarity == "rare"
    assert settings.influences == ("3", )
    assert settings.quality == 20
    assert settings.corrupted == 0
    assert settings.destroyed == 0
    assert settings.implicits == (
        "{ Implicit Modifier }",
        "+25% Chance to Block Spell Damage",
    )
    assert settings.veils == ()
    assert settings.socketed == ()
    assert settings.sockets == 0


def test_parse_recipe_data() -> None:
    recipe_data = RecipeData.from_dict(load_recipe_json()["data"])

    assert recipe_data.fmodpool is None
    assert recipe_data.eldritch is None
    assert recipe_data.dominance is None
    assert recipe_data.mtypes is None
    assert recipe_data.implicits is None
    assert recipe_data.rollable_implicits == 0
    assert recipe_data.cmodpool is None
    assert recipe_data.hmodpool is None

    assert recipe_data.maxaffgrp.prefix == 3
    assert recipe_data.maxaffgrp.suffix == 3

    assert recipe_data.is_rare == 1
    assert recipe_data.is_fossil == 1
    assert recipe_data.is_craftable == 1
    assert recipe_data.is_influenced == 1
    assert recipe_data.is_essence == 1
    assert recipe_data.is_catalyst == 0
    assert recipe_data.is_notable == 0
    assert recipe_data.unique_notable == 0

    assert len(recipe_data.iaffixes) == 5

    poison = recipe_data.iaffixes[0]
    assert poison.atype == "prefix"
    assert poison.id == "611"
    assert poison.mgrp == "3"
    assert poison.modgroups == ("PoisonDamage", )
    assert poison.weight == "500"
    assert poison.nvalues == "[[37,42]]"
    assert poison.tindex == 0
    assert poison.frac == 0
    assert poison.maven == 0
    assert poison.bench == 0
    assert poison.rolls == (37, )

    strength = recipe_data.iaffixes[-1]
    assert strength.atype == "suffix"
    assert strength.id == "2336"
    assert strength.modgroups == ("Strength", )
    assert strength.tindex == 2
    assert strength.rolls == (19, )

    assert recipe_data.meta_flags == {}
    assert recipe_data.imprint is None
    assert recipe_data.enchant == ""
    assert recipe_data.iaffbt.prefix == 2
    assert recipe_data.iaffbt.suffix == 3
    assert recipe_data.cmaxaffgrp.prefix == 3
    assert recipe_data.cmaxaffgrp.suffix == 3
    assert recipe_data.mgrpdata is None
    assert recipe_data.affbymgrp is None
    assert recipe_data.veiledmods is None


def test_parse_recipe_config() -> None:
    config = [
        RecipeStep.from_dict(entry)
        for entry in load_recipe_json()["config"]
    ]

    assert len(config) == 5

    scour = config[0]
    assert scour.method == ("currency", "scour")
    assert scour.mopts is None
    assert scour.autopass is True
    assert scour.filters is None
    assert scour.vfilter is None
    assert scour.actions.win == "next"
    assert scour.actions.win_route is None
    assert scour.actions.fail == "loop"
    assert scour.actions.fail_route is None

    check = config[3]
    assert check.method == ("check", )
    assert check.autopass is False
    assert check.vfilter == ()
    assert check.actions.win == "next"
    assert check.actions.fail == "step"
    assert check.actions.fail_route == "3"
    assert check.filters is not None
    assert len(check.filters) == 1
    assert check.filters[0].type == "and"
    assert check.filters[0].treshold is None
    assert len(check.filters[0].conds) == 1
    assert check.filters[0].conds[0].id == "open_affix"
    assert check.filters[0].conds[0].treshold == 1
    assert check.filters[0].conds[0].max is None
    assert check.filters[0].conds[0].base is None

    augmentation = config[4]
    assert augmentation.method == (
        "currency",
        "augmentation",
        "augmentation_normal",
    )
    assert augmentation.autopass is False
    assert augmentation.filters is not None
    assert [filter_.type for filter_ in augmentation.filters] == ["and", "or"]
    assert augmentation.filters[0].conds[0].id == "2354"
    assert augmentation.filters[1].conds[0].id == "2318"
    assert augmentation.actions.fail == "step"
    assert augmentation.actions.fail_route == "3"
