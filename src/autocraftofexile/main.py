import os

from .crafting import CraftingWorker
from .gui_config import load_gui_config
from .poecd_loader import load_poecd_data
from .recipe_loader import load_recipe

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    poecd = load_poecd_data()
    recipe = load_recipe()
    config = load_gui_config()
    worker = CraftingWorker(config, recipe, poecd)
    worker.run()
