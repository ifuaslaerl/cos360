"""Generic execution resource measurement."""

import resource
import sys
from time import perf_counter
from typing import Any, Callable


class ExecutionMonitor:
    """Measures elapsed time and process peak RSS around any operation."""

    def __init__(self) -> None:
        self.last_elapsed_seconds = 0.0
        self.last_peak_memory_mib = 0.0

    def measure(self, operation: Callable[[], Any]) -> tuple[Any, float, float]:
        """Run ``operation`` and return its value, seconds, and peak RSS in MiB."""
        started = perf_counter()
        try:
            return_value = operation()
        finally:
            self.last_elapsed_seconds = perf_counter() - started
            self.last_peak_memory_mib = self._rss_mib(
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            )
        return return_value, self.last_elapsed_seconds, self.last_peak_memory_mib

    @staticmethod
    def _rss_mib(value: int) -> float:
        divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
        return float(value / divisor)
