from __future__ import annotations

import logging
import threading
from asyncio import CancelledError

import keyboard

from autocraftofexile.rules import DEFAULT_RULES

from .cancellation_token import CancellationTokenSource
from .crafting import DEFAULT_CRAFTER_METHODS, Crafter, CraftingOptions
from .recipe_loader import validate_recipe


class CurrencyCraftingWorker:
    _stop: CancellationTokenSource
    _exit: CancellationTokenSource
    _thread: threading.Thread | None
    options: CraftingOptions
    is_exit_requested: bool
    is_running: bool

    def __init__(self, options: CraftingOptions) -> None:
        self._stop = CancellationTokenSource()
        self._exit = CancellationTokenSource()
        self._thread_lock = threading.Lock()
        self._thread = None
        self.options = options
        self.is_exit_requested = False
        self.is_running = False

    def run(self) -> None:
        rr = self.options.rich_recipe
        recipe_errors = validate_recipe(
            self.options.recipe,
            self.options.poecd,
            filter_logic_types={"and", "or", "not"},
            modifier_rules=DEFAULT_RULES,
            crafting_methods=DEFAULT_CRAFTER_METHODS,
        )
        rr.appendix.extend(f"[red]{error}[/red]" for error in recipe_errors)
        rr.update()
        if recipe_errors:
            return
        hotkeys = [
            keyboard.add_hotkey(self.options.config.start_hotkey, self.start),
            keyboard.add_hotkey(self.options.config.stop_hotkey, self.stop),
        ]
        try:
            self._exit.wait()
        finally:
            for h in hotkeys:
                keyboard.remove_hotkey(h)

            self.stop()

            with self._thread_lock:
                thread = self._thread
                try:
                    if thread is not None and thread.is_alive():
                        thread.join()
                finally:
                    self._exit.reset()

    def start(self) -> None:
        with self._thread_lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._stop.reset()

            self._thread = threading.Thread(
                target=self._main,
                name="crafting-worker",
                daemon=True,
            )
            self._thread.start()
            self.is_running = True

    def exit(self) -> None:
        self.is_exit_requested = True
        self.stop()
        if self.is_running:
            self._exit.wait()

    def stop(self) -> None:
        with self._thread_lock:
            thread = self._thread

            if thread is not None and thread.is_alive():
                self._stop.cancel()

    def _clean_rich_recipe(self):
        rr = self.options.rich_recipe
        rr.appendix = []
        rr.status = {}
        rr.update()

    def _main(self) -> None:
        current_thread = threading.current_thread()

        try:
            self._clean_rich_recipe()
            crafter = Crafter(self._stop.token, self.options)
            with crafter:
                while not self._stop.is_cancelled:
                    result = crafter.execute()

                    if result.done:
                        return
        except CancelledError:
            message = "Crafter stopped"
            logging.exception(message)
            self.options.rich_recipe.update(append=f"[red]{message}[/red]")
        except Exception:
            message = "Crafter terminated unexpectedly"
            logging.exception(message)
            self.options.rich_recipe.update(append=f"[red]{message}[/red]")

        finally:
            with self._thread_lock:
                self.is_running = False
                # Avoid an old worker clearing a newer thread reference.
                if self._thread is current_thread:
                    self._thread = None

                self._stop.reset()
                if self.is_exit_requested:
                    self._exit.cancel()

        if not self.is_exit_requested:
            self.options.rich_recipe.update(
                append=f"Press [cyan]{self.options.config.start_hotkey}[/cyan] to start crafting again"
            )
