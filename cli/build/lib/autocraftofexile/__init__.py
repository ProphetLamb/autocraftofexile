""" AutoCraftOfExile. """

__version__ = "0.1.0"

from pathlib import Path

DATA_ROOT = Path("data")

GUI_CONFIG_FILE = DATA_ROOT / "gui.json"
LOG_FILE = DATA_ROOT / 'crafting.log'
POECD_FILE = DATA_ROOT / "poecd_data.json"
RECIPE_FILE = DATA_ROOT / "recipe.json"

POECD_URL = "https://www.craftofexile.com/json/data/main/poec_data.json"
