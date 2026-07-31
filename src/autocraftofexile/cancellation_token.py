from asyncio import CancelledError
import threading


class CancellationTokenSource:
    _cancelled_event: threading.Event

    def __init__(self):
        self._cancelled_event = threading.Event()

    @property
    def is_cancelled(self):
        return self._cancelled_event.is_set()

    @property
    def token(self):
        return CancellationToken(self)

    def wait(self):
        self._cancelled_event.wait()

    def cancel(self):
        if not self.is_cancelled:
            self._cancelled_event.set()

    def reset(self):
        self._cancelled_event.clear()


class CancellationToken:
    source: CancellationTokenSource | None

    def __init__(self, source: CancellationTokenSource | None) -> None:
        self.source = source

    @property
    def is_cancelled(self):
        return self.source and self.source.is_cancelled

    def throw_if_cancelled(self):
        if self.is_cancelled:
            raise CancelledError()
