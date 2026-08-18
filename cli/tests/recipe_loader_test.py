from autocraftofexile.recipe_loader import load_recipe
from tests import RECIPE_EXAMPLE


def test_load_recipe() -> None:
    recipe = load_recipe(RECIPE_EXAMPLE)
    assert recipe != None
