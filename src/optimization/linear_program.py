"""Solver-independent linear program."""

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class LinearProgram:
    """Linear minimization problem in matrix form."""

    objective: np.ndarray
    inequalities: np.ndarray
    limits: np.ndarray
    bounds: tuple[tuple[float, float | None], ...]
