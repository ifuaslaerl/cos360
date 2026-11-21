"""SciPy linear-programming adapter."""

from time import perf_counter

import numpy as np

from .linear_program import LinearProgram
from .solver_adapter import SolverAdapter


class ScipySolverAdapter(SolverAdapter):
    """Executes all requested SciPy linprog methods, including legacy names."""

    METHODS = (
        "highs",
        "highs-ds",
        "highs-ipm",
        "interior-point",
        "revised simplex",
        "simplex",
    )

    @property
    def name(self) -> str:
        return "scipy"

    def available_solvers(self) -> tuple[str, ...]:
        return self.METHODS

    def solve(
        self, problem: LinearProgram, solver: str
    ) -> tuple[float, float, np.ndarray]:
        from scipy.optimize import linprog

        started = perf_counter()
        result = linprog(
            problem.objective,
            A_ub=problem.inequalities,
            b_ub=problem.limits,
            bounds=problem.bounds,
            method=solver,
        )
        elapsed = perf_counter() - started
        if not result.success:
            raise RuntimeError(result.message)
        return float(result.fun), elapsed, np.asarray(result.x)
