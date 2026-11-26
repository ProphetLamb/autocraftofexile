from __future__ import annotations

import logging
import threading
from asyncio import CancelledError
from collections.abc import Callable

import keyboard

from .cancellation_token import (
    CancellationToken,
    CancellationTokenSource,
)
from .crafting import (
    DEFAULT_CRAFTER_METHODS,
    Crafter,
    CraftingOptions,
)
from .recipe_loader import validate_recipe
from .rules import DEFAULT_RULES

_logger = logging.getLogger(__name__)


class CraftingWorker:
    _stop: CancellationTokenSource
    _exit: CancellationTokenSource
    _thread: threading.Thread | None
    _thread_lock: threading.Lock

    options: CraftingOptions
    is_exit_requested: bool
    is_running: bool

    crafter_factory: Callable[
        [CraftingOptions, CancellationToken],
        Crafter,
    ]

    def __init__(
        self,
        crafter_factory: Callable[
            [CraftingOptions, CancellationToken],
            Crafter,
        ],
        options: CraftingOptions,
    ) -> None:
        self._stop = CancellationTokenSource()
        self._exit = CancellationTokenSource()
        self._thread_lock = threading.Lock()
        self._thread = None

        self.options = options
        self.is_exit_requested = False
        self.is_running = False
        self.crafter_factory = crafter_factory

    def run(self) -> None:
        rich_recipe = self.options.rich_recipe

        recipe_errors = validate_recipe(
            self.options.recipe,
            self.options.poecd,
            filter_logic_types={
                "and",
                "or",
                "not",
            },
            modifier_rules=DEFAULT_RULES,
            crafting_methods=DEFAULT_CRAFTER_METHODS,
        )

        rich_recipe.appendix.extend(f"[red]{error}[/red]" for error in recipe_errors)
        rich_recipe.update()

        if recipe_errors:
            return

        # Keep the original, previously working hotkey behavior. Exceptions
        # inside callbacks are explicitly logged.
        hotkeys = [
            keyboard.add_hotkey(
                self.options.config.start_hotkey,
                self._start_hotkey_callback,
            ),
            keyboard.add_hotkey(
                self.options.config.stop_hotkey,
                self._stop_hotkey_callback,
            ),
        ]

        _logger.info(
            "Crafting hotkeys registered: start=%s stop=%s",
            self.options.config.start_hotkey,
            self.options.config.stop_hotkey,
        )

        try:
            self._exit.wait()
        except CancelledError:
            # Cancellation of _exit is the expected shutdown mechanism.
            pass
        finally:
            for hotkey in hotkeys:
                keyboard.remove_hotkey(hotkey)

            self.stop()
            self._join_worker()

    def _start_hotkey_callback(self) -> None:
        try:
            _logger.info("Start hotkey pressed")
            self.start()
        except Exception:
            # keyboard executes callbacks on its own thread. Without this
            # wrapper, an exception can look like the hotkey did nothing.
            _logger.exception("Start hotkey callback failed")

    def _stop_hotkey_callback(self) -> None:
        try:
            _logger.info("Stop hotkey pressed")
            self.stop()
        except Exception:
            _logger.exception("Stop hotkey callback failed")

    def start(self) -> None:
        with self._thread_lock:
            if self.is_exit_requested:
                _logger.warning(
                    "Ignoring start request because worker exit was requested"
                )
                return

            if self.is_running:
                _logger.debug(
                    "Ignoring start request because crafting is already running"
                )
                return

            if self._thread is not None and self._thread.is_alive():
                _logger.debug("Ignoring start request because worker thread is alive")
                return

            # Reset before passing the token to the new Crafter.
            self._stop.reset()

            thread = threading.Thread(
                target=self._main,
                name="crafting-worker",
                daemon=True,
            )

            self._thread = thread
            self.is_running = True

        # Do not start a thread while holding the lifecycle lock. The new
        # thread's cleanup path also needs this lock.
        try:
            thread.start()
        except Exception:
            with self._thread_lock:
                if self._thread is thread:
                    self._thread = None
                    self.is_running = False
            raise

        _logger.info(
            "Crafting worker started with thread identifier %s",
            thread.ident,
        )

    def stop(self) -> None:
        with self._thread_lock:
            thread = self._thread
            running = self.is_running

        if not running and (thread is None or not thread.is_alive()):
            _logger.debug("Ignoring stop request because crafting is not running")
            return

        _logger.info("Crafting cancellation requested")
        self._stop.cancel()

    def exit(self) -> None:
        _logger.info("Crafting-worker exit requested")
        self.is_exit_requested = True

        self.stop()
        self._join_worker()

        if not self._exit.is_cancelled:
            self._exit.cancel()

    def _join_worker(
        self,
        timeout: float | None = None,
    ) -> None:
        # Capture the thread under the lock, but never join while holding it.
        with self._thread_lock:
            thread = self._thread

        if (
            thread is None
            or thread is threading.current_thread()
            or not thread.is_alive()
        ):
            return

        thread.join(timeout=timeout)

    def _clean_rich_recipe(self) -> None:
        rich_recipe = self.options.rich_recipe
        rich_recipe.appendix = []
        rich_recipe.status = {}
        rich_recipe.update()

    def _main(self) -> None:
        current_thread = threading.current_thread()

        try:
            self._clean_rich_recipe()

            crafter = self.crafter_factory(
                self.options,
                self._stop.token,
            )

            with crafter:
                while not self._stop.is_cancelled:
                    result = crafter.execute()

                    if self._stop.is_cancelled:
                        raise CancelledError

                    if result.done:
                        return

        except CancelledError:
            message = "Crafter stopped"
            _logger.info(message)

            self.options.rich_recipe.update(append=f"[yellow]{message}[/yellow]")

        except Exception:
            message = "Crafter terminated unexpectedly"
            _logger.exception(message)

            self.options.rich_recipe.update(append=f"[red]{message}[/red]")

        finally:
            with self._thread_lock:
                if self._thread is current_thread:
                    self._thread = None
                    self.is_running = False

            if self.is_exit_requested:
                self._exit.cancel()

        if not self.is_exit_requested:
            self.options.rich_recipe.update(
                append=(
                    "Press "
                    f"[cyan]{self.options.config.start_hotkey}[/cyan] "
                    "to start crafting again"
                )
            )