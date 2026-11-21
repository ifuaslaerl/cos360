"""Solver adapter contract."""

from abc import ABC, abstractmethod

import numpy as np

from .linear_program import LinearProgram


class SolverAdapter(ABC):
    """Common interface for solver libraries."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the adapter name."""

    @abstractmethod
    def available_solvers(self) -> tuple[str, ...]:
        """Return supported solver/method names."""

    @abstractmethod
    def solve(
        self, problem: LinearProgram, solver: str
    ) -> tuple[float, float, np.ndarray]:
        """Return objective, solver time, and decision values."""
