import json
import logging
from dataclasses import asdict

import keyboard
import pyautogui

from .models.gui_config import Coordinates, GuiConfig

GUI_CONFIG_FILE = "data/gui.json"


def prompt_coordinates(name: str) -> Coordinates:
    print()
    print(f"Move mouse to the {name} and press ENTER.")
    input()

    x, y = pyautogui.position()
    print(f"{name}: {x}, {y}")
    return Coordinates(x, y)


def prompt_hotkey(name: str) -> str:
    print()
    print(f"Press the {name} hotkey.")

    hotkey = keyboard.read_hotkey()
    print(f"{name} hotkey: {hotkey}")
    return hotkey


def load_gui_config() -> GuiConfig:
    try:
        data = None
        with open(GUI_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return GuiConfig.from_dict(data)

    except FileNotFoundError:
        logging.debug("begin GUI config prompt")
        config = GuiConfig(
            showcase=prompt_coordinates("Item Showcase"),
            transmute=prompt_coordinates("Orb of Transmutation"),
            augment=prompt_coordinates("Orb of Augmentation"),
            alteration=prompt_coordinates("Orb of Alteration"),
            regal=prompt_coordinates("Regal Orb"),
            alchemy=prompt_coordinates("Alchemy Orb"),
            chaos=prompt_coordinates("Chaos Orb"),
            exalt=prompt_coordinates("Exalted Orb"),
            scour=prompt_coordinates("Orb of Scouring"),
            annul=prompt_coordinates("Orb of Annulment"),
            start_hotkey=prompt_hotkey("start"),
            stop_hotkey=prompt_hotkey("stop"),
        )

        logging.debug("done GUI config prompt")
        with open(GUI_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=2)

        logging.debug("done GUI config file write")
        return config
