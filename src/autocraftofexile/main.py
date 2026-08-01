import atexit
import logging
import os
import signal
import sys
from typing import Annotated

import typer

from autocraftofexile import GUI_CONFIG_FILE, LOG_FILE, POECD_FILE, RECIPE_FILE

from .crafting import DEFAULT_CRAFTER_METHODS, CraftingOptions, CraftingWorker
from .gui_config import load_gui_config
from .item_match_context import repr_recipe
from .poecd_loader import load_poecd_data
from .recipe_loader import load_recipe, validate_recipe
from .rules import DEFAULT_RULES

app = typer.Typer(
    suggest_commands=True, context_settings={"help_option_names": ["-h", "--help"]}
)


@app.callback(invoke_without_command=True)
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
    logging.basicConfig(
        filename=log_file,
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
        print(f"[red]{error}[/red]")
    if recipe_errors:
        return

    config = load_gui_config(gui_file)

    worker = CraftingWorker(config, recipe, poecd, CraftingOptions(speed or 60))

    def sigint():
        logging.warning("SIGINT received: terminating worker")
        worker.exit()
        logging.debug("done autocraftofexile")
        logging.shutdown()
        sys.exit(-1)

    signal.signal(signal.SIGINT, lambda signal, frame: sigint())
    worker.run()
    logging.debug("done autocraftofexile")


if __name__ == "__main__":
    app()
