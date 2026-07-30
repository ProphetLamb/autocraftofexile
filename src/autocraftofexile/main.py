import logging
import os
import signal
import sys
from typing import Annotated

import typer

from autocraftofexile import LOG_FILE

from .crafting import CraftingOptions, CraftingWorker
from .gui_config import load_gui_config
from .poecd_loader import load_poecd_data
from .recipe_loader import load_recipe

def main(
    speed: Annotated[int, typer.Option(help="The number of actions per second")] = 20,
    poecd_data_file: Annotated[str | None, typer.Option(help="Path to the pocd.json file")] = None,
    recipe_file: Annotated[str | None, typer.Option(help="Path to the recipe.json file")] = None,
    gui_file: Annotated[str | None, typer.Option(help="Path to the gui.json file")] = None
):
    os.makedirs("data", exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        format='%(asctime)s|%(levelname)s|%(message)s',
        encoding='utf-8',
        level=logging.DEBUG
    )
    logging.debug("begin autocraftofexile")
    poecd = load_poecd_data(poecd_data_file)
    recipe = load_recipe(recipe_file)
    config = load_gui_config(gui_file)
    worker = CraftingWorker(config, recipe, poecd, CraftingOptions(speed or 20))
    def sigint(signal, frame):
        del signal, frame
        if worker.is_running:
            worker.stop()
        else:
            sys.exit(-1)
    signal.signal(signal.SIGINT, sigint)
    worker.run()
    logging.debug("done autocraftofexile")

app = typer.Typer()
app.command()(main)

if __name__ == "__main__":
    app()
