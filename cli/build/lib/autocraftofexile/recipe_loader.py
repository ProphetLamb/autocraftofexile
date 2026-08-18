import json
import logging
from os import PathLike

from autocraftofexile import RECIPE_FILE

from .models.recipe import Recipe


def load_recipe(file: PathLike[str] | str | None = None) -> Recipe:
    data = None
    logging.debug("begin Recipe data file read")
    with open(file or RECIPE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    logging.debug("done Recipe data file read")
    recipe = Recipe.from_dict(data)
    logging.debug("done Recipe data parse")
    return recipe
