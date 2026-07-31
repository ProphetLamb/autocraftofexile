import json
import logging
from dataclasses import asdict
from os import PathLike
import time

import keyboard
import pyautogui

from autocraftofexile import GUI_CONFIG_FILE

from .models.gui_config import Coordinates, GuiConfig


def prompt_coordinates(name: str) -> Coordinates:
    time.sleep(0.1)
    print()
    input(f"Move mouse to the {name} and press ENTER.")
    x, y = pyautogui.position()
    print(f"{name}: {x}, {y}")
    return Coordinates(x, y)


def prompt_hotkey(name: str) -> str:
    time.sleep(0.1)
    print()
    print(f"Press the {name} hotkey.")
    hotkey = keyboard.read_hotkey(suppress=False)
    print(f"{name} hotkey: {hotkey}")
    return hotkey


def load_gui_config(file: PathLike[str] | str | None = None) -> GuiConfig:
    file = file or GUI_CONFIG_FILE
    try:
        data = None
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = GuiConfig.from_dict(data)
        print(
            "Successfully loaded gui config\n",
            f" Start hotkey {config.start_hotkey}\n",
            f" Stop hotkey {config.stop_hotkey}\n",
        )
        return config

    except FileNotFoundError:
        logging.debug("begin GUI config prompt")
        config = GuiConfig(
            transmute=prompt_coordinates("Orb of Transmutation"),
            alteration=prompt_coordinates("Orb of Alteration"),
            annul=prompt_coordinates("Orb of Annulment"),
            augment=prompt_coordinates("Orb of Augmentation"),
            exalt=prompt_coordinates("Exalted Orb"),
            regal=prompt_coordinates("Regal Orb"),
            alchemy=prompt_coordinates("Alchemy Orb"),
            chaos=prompt_coordinates("Chaos Orb"),
            scour=prompt_coordinates("Orb of Scouring"),
            showcase=prompt_coordinates("Item Showcase"),
            start_hotkey=prompt_hotkey("start"),
            stop_hotkey=prompt_hotkey("stop"),
        )

        logging.debug("done GUI config prompt")
        with open(file, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=2)

        logging.debug("done GUI config file write")
        return config
