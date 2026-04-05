"""Interrupt flag for controlling long-running tableau reasoning tasks."""

from __future__ import annotations

import threading


class InterruptFlag:
    """Thread-safe flag for interrupting or timing out reasoning tasks.

    The flag supports two interrupt types: explicit interruption (via
    ``interrupt()``) and timeout-based interruption (when a task exceeds
    the configured ``individual_task_timeout``).

    Args:
        individual_task_timeout: Maximum time in milliseconds allowed for a
            single reasoning task. Use ``0`` or a negative value for no timeout.
    """

    _INTERRUPTED = "interrupted"
    _TIMEOUT = "timeout"

    def __init__(self, individual_task_timeout: int = 0) -> None:
        self._interrupt_type: str | None = None
        self._individual_task_timeout = individual_task_timeout
        self._interrupt_timer: _InterruptTimer | None = None

        if individual_task_timeout > 0:
            self._interrupt_timer = _InterruptTimer(
                individual_task_timeout, self
            )
            self._interrupt_timer.daemon = True
            self._interrupt_timer.name = "HermiT Interrupt Current Task Thread"
            self._interrupt_timer.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_interrupt(self) -> None:
        """Raise an exception if an interrupt has been signalled.

        Raises:
            InterruptCurrentTaskException: if the task was explicitly interrupted.
            TimeoutError: if the task timed out.
        """
        interrupt_type = self._interrupt_type
        if interrupt_type is not None:
            if interrupt_type == self._TIMEOUT:
                raise TimeoutError()
            else:
                from hermit.tableau.interrupt_current_task_exception import (
                    InterruptCurrentTaskException,
                )

                raise InterruptCurrentTaskException()

    def interrupt(self) -> None:
        """Signal that the current task should be interrupted."""
        self._interrupt_type = self._INTERRUPTED

    def start_task(self) -> None:
        """Mark the beginning of a reasoning task, resetting the interrupt state."""
        self._interrupt_type = None
        if self._interrupt_timer is not None:
            self._interrupt_timer.start_timing()

    def end_task(self) -> None:
        """Mark the end of a reasoning task, stopping any active timeout."""
        if self._interrupt_timer is not None:
            self._interrupt_timer.stop_timing()
        self._interrupt_type = None

    def dispose(self) -> None:
        """Release resources associated with the interrupt timer thread."""
        if self._interrupt_timer is not None:
            self._interrupt_timer.dispose()


# ------------------------------------------------------------------
# Internal timer thread
# ------------------------------------------------------------------


class _InterruptTimer(threading.Thread):
    """Background thread that triggers a timeout after *timeout* milliseconds."""

    _WAIT_FOR_TASK = "wait_for_task"
    _TIMING = "timing"
    _TIMING_STOPPED = "timing_stopped"
    _DISPOSED = "disposed"

    def __init__(self, timeout: int, flag: InterruptFlag) -> None:
        super().__init__()
        self._timeout = timeout / 1000.0  # convert ms -> seconds
        self._flag = flag
        self._state: str = self._WAIT_FOR_TASK
        self._lock = threading.Condition()

    # ------------------------------------------------------------------

    def run(self) -> None:
        while self._state != self._DISPOSED:
            self._state = self._WAIT_FOR_TASK
            with self._lock:
                self._lock.notify_all()
                while self._state == self._WAIT_FOR_TASK:
                    try:
                        self._lock.wait()
                    except OSError:
                        self._state = self._DISPOSED

            if self._state == self._TIMING:
                with self._lock:
                    try:
                        self._lock.wait(self._timeout)
                        if self._state == self._TIMING:
                            self._flag._interrupt_type = InterruptFlag._TIMEOUT
                    except OSError:
                        self._state = self._DISPOSED

    def start_timing(self) -> None:
        with self._lock:
            while (
                self._state != self._WAIT_FOR_TASK
                and self._state != self._DISPOSED
            ):
                try:
                    self._lock.wait()
                except OSError:
                    return
            if self._state == self._WAIT_FOR_TASK:
                self._state = self._TIMING
                self._lock.notify_all()

    def stop_timing(self) -> None:
        with self._lock:
            if self._state == self._TIMING:
                self._state = self._TIMING_STOPPED
                self._lock.notify_all()
                while (
                    self._state != self._WAIT_FOR_TASK
                    and self._state != self._DISPOSED
                ):
                    try:
                        self._lock.wait()
                    except OSError:
                        return

    def dispose(self) -> None:
        with self._lock:
            self._state = self._DISPOSED
            self._lock.notify_all()
        try:
            self.join()
        except OSError:
            pass
