import json
import logging

from .models.recipe import Recipe

RECIPE_FILE = "data/recipe.json"


def load_recipe() -> Recipe:
    data = None
    logging.info("begin Recipe data file read")
    with open(RECIPE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    logging.info("done Recipe data file read")
    recipe = Recipe.from_dict(data)
    logging.info("done Recipe data parse")
    return recipe
