import time
import types
from typing import Optional, Type


class TimerError(Exception):
    """An exception used to report errors in use of the `Timer` class."""


class Timer:
    _name: str
    _start_time: Optional[float]

    def __init__(self, name: str) -> None:
        self._name = name
        self._start_time = None

    def start(self) -> None:
        """Starts a new timer."""

        if self._start_time is not None:
            raise TimerError(f"timer is running; use `stop()` to stop it")

        self._start_time = time.perf_counter()

    def stop(self) -> None:
        """Stops the timer, and reports the elapsed time."""

        if self._start_time is None:
            raise TimerError(f"timer is not running; use `start()` to start it")

        elapsed_time = time.perf_counter() - self._start_time
        self._start_time = None
        print(f"{self._name} took {elapsed_time:0.3f}s")

    def __enter__(self) -> "Timer":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[types.TracebackType],
    ) -> None:
        self.stop()
