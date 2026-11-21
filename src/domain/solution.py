"""Optimization result representation."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Solution:
    """One solver execution and its item-level decision values."""

    dataset: str
    solver: str
    repeat: int
    status: str
    objective: float | None
    elapsed_seconds: float
    peak_memory_mib: float | None
    rows: tuple[dict[str, Any], ...]
    errors: tuple[str, ...] = ()
