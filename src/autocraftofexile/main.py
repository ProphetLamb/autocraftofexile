import logging
import os

from autocraftofexile import LOG_FILE

from .crafting import CraftingWorker
from .gui_config import load_gui_config
from .poecd_loader import load_poecd_data
from .recipe_loader import load_recipe


def main():
    os.makedirs("data", exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        format='%(asctime)s|%(levelname)s|%(message)s',
        encoding='utf-8',
        level=logging.DEBUG
    )
    logging.debug("begin autocraftofexile")
    poecd = load_poecd_data()
    recipe = load_recipe()
    config = load_gui_config()
    worker = CraftingWorker(config, recipe, poecd)
    worker.run()
    logging.debug("done autocraftofexile")


if __name__ == "__main__":
    main()
