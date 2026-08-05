import json
import logging
from dataclasses import asdict
from os import PathLike

from rich import print

from .models.gui_config import GuiConfig

_logger = logging.getLogger(__name__)


def load_gui_config(file: PathLike[str] | str) -> GuiConfig:
    try:
        data = None
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = GuiConfig.from_dict(data)
        config.prompt_missing_config()
        print(
            "Successfully loaded gui config\n"
            f" Start hotkey [cyan]{config.start_hotkey}[/cyan]\n"
            f" Stop hotkey [cyan]{config.stop_hotkey}[/cyan]\n"
        )
        return config

    except FileNotFoundError:
        _logger.debug("begin GUI config prompt")
        config = GuiConfig(start_hotkey="", stop_hotkey="")
        config.prompt_missing_config()
        _logger.debug("done GUI config prompt")
        with open(file, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=2)

        _logger.debug("done GUI config file write")
        return config
