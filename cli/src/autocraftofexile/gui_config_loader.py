import json
import logging
from os import PathLike

from rich import print

from .models.gui_config import GuiConfig

_logger = logging.getLogger(__name__)


def load_gui_config(file: PathLike[str] | str) -> GuiConfig:
    try:
        data = None
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            _logger.exception("Failed to load gui config from %s", file)

        config = GuiConfig.from_dict(data or {})
        if config.prompt_missing_config():
            with open(file, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2)

        print(
            "Successfully loaded gui config\n"
            f" Start hotkey [cyan]{config.start_hotkey}[/cyan]\n"
            f" Stop hotkey [cyan]{config.stop_hotkey}[/cyan]\n"
        )
        return config

    except FileNotFoundError:
        _logger.debug("begin GUI config prompt")
        config = GuiConfig.from_dict({})
        config.prompt_missing_config()
        _logger.debug("done GUI config prompt")
        with open(file, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2)

        _logger.debug("done GUI config file write")
        return config
