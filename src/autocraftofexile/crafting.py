import threading

import keyboard

from .models.gui_config import GuiConfig
from .models.poecd import PoeCd
from .models.recipe import Recipe


class CraftingWorker:
    stop_event: threading.Event
    thread: threading.Thread | None
    config: GuiConfig
    recipe: Recipe
    poecd: PoeCd

    def __init__(self, config: GuiConfig, recipe: Recipe, poecd: PoeCd):
        self.stop_event = threading.Event()
        self.thread = None
        self.config = config
        self.recipe = recipe
        self.poecd = poecd

    def run(self):
        keyboard.add_hotkey(
            self.config.start_hotkey,
            self._start
        )

        keyboard.add_hotkey(
            self.config.stop_hotkey,
            self._stop
        )

        self._get_thread().join()

    def _is_stopped(self) -> bool:
        return self.stop_event.is_set()

    def _start(self):
        if self._is_stopped():
            return
        self._get_thread().start()

    def _stop(self):
        t = self.thread
        if t and t.is_alive():
            self.stop_event.set()

    def _get_thread(self):
        t = self.thread
        if t and t.is_alive():
            return t
        t = threading.Thread(
            target=self._main,
            daemon=True
        )
        self.thread = t
        return t

    def _main(self):
        try:
            while not self._is_stopped():
                #
                # Placeholder
                #
                print("Crafting...")
                self.stop_event.wait(1)
        finally:
            self.thread = None
            self.stop_event.clear()


class Crafter:
    config: GuiConfig
    recipe: Recipe
    poecd: PoeCd
