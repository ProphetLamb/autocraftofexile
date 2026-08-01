import atexit
import logging
import os
import signal
import sys
from typing import Annotated

import typer

from autocraftofexile import LOG_FILE, POECD_FILE
from autocraftofexile.rules import DEFAULT_RULES

from .crafting import DEFAULT_CRAFTER_METHODS, CraftingOptions, CraftingWorker
from .gui_config import load_gui_config
from .item_match_context import repr_recipe
from .poecd_loader import load_poecd_data
from .recipe_loader import load_recipe, validate_recipe

app = typer.Typer(
    suggest_commands=True, context_settings={"help_option_names": ["-h", "--help"]}
)


@app.callback(invoke_without_command=True)
def main(
    speed: Annotated[
        int, typer.Option("--speed", help="The number of actions per second")
    ] = 60,
    poecd_data_file: Annotated[
        str | None, typer.Option("--poecd", help="Path to the pocd.json file")
    ] = None,
    recipe_file: Annotated[
        str | None, typer.Option("--recipe", help="Path to the recipe.json file")
    ] = None,
    gui_file: Annotated[
        str | None, typer.Option("--gui", help="Path to the gui.json file")
    ] = None,
    log_file: Annotated[
        str | None, typer.Option("--log", help="Path to the log file")
    ] = None,
):
    if (log_dir := os.path.dirname(log_file or LOG_FILE)) != "":
        os.makedirs(log_dir, exist_ok=True)
    if (poecd_dir := os.path.dirname(poecd_data_file or POECD_FILE)) != "":
        os.makedirs(poecd_dir, exist_ok=True)
    logging.basicConfig(
        filename=log_file or LOG_FILE,
        format="%(asctime)s|%(levelname)s|%(message)s",
        encoding="utf-8",
        level=logging.DEBUG,
    )
    atexit.register(logging.shutdown)
    logging.debug("begin autocraftofexile")
    poecd = load_poecd_data(poecd_data_file)
    recipe = load_recipe(recipe_file)

    r = repr_recipe(recipe, poecd)
    print("\n" + r + "\n")
    logging.info(r)
    recipe_errors = validate_recipe(
        recipe,
        poecd,
        filter_logic_types={"and", "or", "not"},
        modifier_rules=DEFAULT_RULES,
        crafting_methods=DEFAULT_CRAFTER_METHODS,
    )
    for error in recipe_errors:
        print("[red]error[/red]")
    if recipe_errors:
        return

    config = load_gui_config(gui_file)

    worker = CraftingWorker(config, recipe, poecd, CraftingOptions(speed or 60))

    def sigint(signal, frame):
        del signal, frame
        logging.warning("SIGINT received: terminating worker")
        worker.exit()
        logging.debug("done autocraftofexile")
        logging.shutdown()
        sys.exit(-1)

    signal.signal(signal.SIGINT, sigint)
    worker.run()
    logging.debug("done autocraftofexile")
