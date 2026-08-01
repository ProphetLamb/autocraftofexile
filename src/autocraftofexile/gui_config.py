import json
import logging
import time
from dataclasses import asdict
from os import PathLike

import keyboard
import pyautogui
from rich import print

from autocraftofexile import GUI_CONFIG_FILE

from .models.gui_config import Coordinates, GuiConfig


def prompt_coordinates(name: str) -> Coordinates:
    time.sleep(0.1)
    input(f"Move mouse to the {name} and press ENTER")
    x, y = pyautogui.position()
    print(f"[bright_white]{name}[/bright_white]: {x}, {y}")
    return Coordinates(x, y)


def prompt_hotkey(name: str) -> str:
    time.sleep(0.1)
    print(f"\nPress the [bright_white]{name}[/bright_white] hotkey.")
    hotkey = keyboard.read_hotkey(suppress=False)
    print(f"[bright_white]{name}[/bright_white] hotkey: [cyan]{hotkey}[/cyan]")
    return hotkey


def load_gui_config(file: PathLike[str] | str | None = None) -> GuiConfig:
    file = file or GUI_CONFIG_FILE
    try:
        data = None
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_config = GuiConfig.from_dict(data)
        config = prompt_missing_config(raw_config)
        if config != raw_config:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(asdict(config), f, indent=2)

        print(
            "Successfully loaded gui config\n"
            f" Start hotkey [cyan]{config.start_hotkey}[/cyan]\n"
            f" Stop hotkey [cyan]{config.stop_hotkey}[/cyan]\n"
        )
        return config

    except FileNotFoundError:
        logging.debug("begin GUI config prompt")
        config = prompt_missing_config(GuiConfig(*{}))
        logging.debug("done GUI config prompt")
        with open(file, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=2)

        logging.debug("done GUI config file write")
        return config


def prompt_missing_config(existing: GuiConfig):
    return GuiConfig(
        transmute=existing.transmute or prompt_coordinates("Orb of Transmutation"),
        alteration=existing.alteration or prompt_coordinates("Orb of Alteration"),
        annul=existing.annul or prompt_coordinates("Orb of Annulment"),
        augment=existing.augment or prompt_coordinates("Orb of Augmentation"),
        exalt=existing.exalt or prompt_coordinates("Exalted Orb"),
        regal=existing.regal or prompt_coordinates("Regal Orb"),
        alchemy=existing.alchemy or prompt_coordinates("Alchemy Orb"),
        chaos=existing.chaos or prompt_coordinates("Chaos Orb"),
        scour=existing.scour or prompt_coordinates("Orb of Scouring"),
        jeweller=existing.jeweller or prompt_coordinates("Jeweller's Orb"),
        fusing=existing.fusing or prompt_coordinates("Orb of Fusing"),
        showcase=existing.showcase or prompt_coordinates("Item Showcase"),
        start_hotkey=existing.start_hotkey or prompt_hotkey("start"),
        stop_hotkey=existing.stop_hotkey or prompt_hotkey("stop"),
    )
