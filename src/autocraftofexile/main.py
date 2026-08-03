import atexit
import logging
import os
import signal
import sys
from typing import Annotated

import typer
from rich import print
from rich.live import Live

from autocraftofexile import GUI_CONFIG_FILE, LOG_FILE, POECD_FILE, RECIPE_FILE

from .crafting import CraftingOptions
from .currency_crafting_worker import CurrencyCraftingWorker
from .gui_config import load_gui_config
from .poecd_loader import load_poecd_data
from .recipe_loader import load_recipe
from .rich_recipe import RichRecipe, repr_recipe

app = typer.Typer(
    suggest_commands=True, context_settings={"help_option_names": ["-h", "--help"]}
)


def _setup_logging(log_file: str):
    logging.basicConfig(
        filename=log_file,
        format="%(asctime)s|%(levelname)s|%(name)s|%(message)s",
        encoding="utf-8",
        level=logging.DEBUG,
    )
    logger = logging.getLogger(__name__)
    atexit.register(logging.shutdown)
    return logger


@app.command()
def main(
    speed: Annotated[
        int, typer.Option("--speed", help="The number of actions per second")
    ] = 60,
    poecd_data_file: Annotated[
        str, typer.Option("--poecd", help="Path to the pocd.json file")
    ] = str(POECD_FILE),
    recipe_file: Annotated[
        str, typer.Option("--recipe", help="Path to the recipe.json file")
    ] = str(RECIPE_FILE),
    gui_file: Annotated[
        str, typer.Option("--gui", help="Path to the gui.json file")
    ] = str(GUI_CONFIG_FILE),
    log_file: Annotated[str, typer.Option("--log", help="Path to the log file")] = str(
        LOG_FILE
    ),
):
    if (log_dir := os.path.dirname(log_file)) != "":
        os.makedirs(log_dir, exist_ok=True)
    if (poecd_dir := os.path.dirname(poecd_data_file)) != "":
        os.makedirs(poecd_dir, exist_ok=True)
    logger = _setup_logging(log_file)
    logger.debug("begin autocraftofexile")
    poecd = load_poecd_data(poecd_data_file)
    recipe = load_recipe(recipe_file)
    config = load_gui_config(gui_file)

    print()
    logger.info(repr_recipe(recipe, poecd, {}))
    with Live(repr_recipe(recipe, poecd, {})) as live:
        rr = RichRecipe(recipe, poecd, [], {}, {}, live)
        worker = CurrencyCraftingWorker(
            CraftingOptions(speed or 60, rr, config, recipe, poecd)
        )

        def sigint():
            logger.warning("SIGINT received: terminating worker")
            worker.exit()
            logger.debug("done autocraftofexile")
            logging.shutdown()
            sys.exit(-1)

        signal.signal(signal.SIGINT, lambda signal, frame: sigint())
        worker.run()
    logger.debug("done autocraftofexile")


if __name__ == "__main__":
    app()
