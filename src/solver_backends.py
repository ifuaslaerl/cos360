"""Adapters exposing different LP solver libraries through one interface."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from time import perf_counter
from typing import Protocol

if __package__:
    from .engine import LinearProgram
else:
    from engine import LinearProgram

SCIPY_METHODS = [
    "highs",
    "highs-ds",
    "highs-ipm",
    "interior-point",
    "revised simplex",
    "simplex",
]
ORTOOLS_SOLVERS = (
    "GLOP",
    "CLP",
    "PDLP",
    "CBC",
    "SCIP",
)


@dataclass(frozen=True)
class SolverResult:
    objective: float
    model_seconds: float
    solve_seconds: float


class SolverAdapter(Protocol):
    """Interface implemented by each solver-library adapter."""

    name: str

    def available_solvers(self) -> list[str]: ...

    def solve(self, problem: LinearProgram, solver: str) -> SolverResult: ...


class ScipyAdapter:
    name = "scipy"

    def available_solvers(self) -> list[str]:
        return list(SCIPY_METHODS)

    def solve(self, problem: LinearProgram, solver: str) -> SolverResult:
        from scipy.optimize import linprog

        started = perf_counter()
        result = linprog(
            problem.objective,
            A_ub=problem.inequalities,
            b_ub=problem.limits,
            bounds=problem.bounds,
            method=solver,
        )
        solve_seconds = perf_counter() - started
        if not result.success:
            raise RuntimeError(result.message)
        return SolverResult(float(result.fun), 0.0, solve_seconds)


class PulpAdapter:
    name = "pulp"

    def available_solvers(self) -> list[str]:
        if find_spec("pulp") is None:
            return []
        import pulp

        return [
            solver
            for solver in pulp.listSolvers(onlyAvailable=True)
            if solver != "CPSAT"
        ]

    def solve(self, problem: LinearProgram, solver: str) -> SolverResult:
        import pulp

        started = perf_counter()
        model = pulp.LpProblem("benchmark_lp", pulp.LpMinimize)
        variables = [
            pulp.LpVariable(
                f"x{index}",
                lowBound=lower,
                upBound=upper,
                cat=pulp.LpContinuous,
            )
            for index, (lower, upper) in enumerate(problem.bounds)
        ]
        model += pulp.lpSum(
            float(problem.objective[index]) * variable
            for index, variable in enumerate(variables)
        )
        for row_index, (row, limit) in enumerate(
            zip(problem.inequalities, problem.limits)
        ):
            model += (
                pulp.lpSum(
                    float(coefficient) * variable
                    for coefficient, variable in zip(row, variables)
                    if coefficient != 0
                )
                <= float(limit),
                f"constraint_{row_index}",
            )
        solver_instance = pulp.getSolver(solver, msg=False)
        model_seconds = perf_counter() - started

        started = perf_counter()
        status = model.solve(solver_instance)
        solve_seconds = perf_counter() - started
        if pulp.LpStatus[status] != "Optimal":
            raise RuntimeError(f"PuLP status: {pulp.LpStatus[status]}")
        value = pulp.value(model.objective)
        if value is None:
            raise RuntimeError("PuLP returned no objective value")
        return SolverResult(float(value), model_seconds, solve_seconds)


class OrToolsAdapter:
    name = "ortools"

    def available_solvers(self) -> list[str]:
        if find_spec("ortools") is None:
            return []
        from ortools.linear_solver import pywraplp

        return [
            name
            for name in ORTOOLS_SOLVERS
            if pywraplp.Solver.CreateSolver(name) is not None
        ]

    def solve(self, problem: LinearProgram, solver: str) -> SolverResult:
        from ortools.linear_solver import pywraplp

        started = perf_counter()
        model = pywraplp.Solver.CreateSolver(solver)
        if model is None:
            raise RuntimeError(f"OR-Tools solver {solver!r} is unavailable")
        infinity = model.infinity()
        variables = [
            model.NumVar(
                lower if lower is not None else -infinity,
                upper if upper is not None else infinity,
                f"x{index}",
            )
            for index, (lower, upper) in enumerate(problem.bounds)
        ]
        for row, limit in zip(problem.inequalities, problem.limits):
            constraint = model.RowConstraint(-infinity, float(limit), "")
            for coefficient, variable in zip(row, variables):
                if coefficient != 0:
                    constraint.SetCoefficient(variable, float(coefficient))
        objective = model.Objective()
        for coefficient, variable in zip(problem.objective, variables):
            objective.SetCoefficient(variable, float(coefficient))
        objective.SetMinimization()
        if solver == "PDLP":
            model.SetSolverSpecificParametersAsString(
                "termination_criteria { simple_optimality_criteria { "
                "eps_optimal_absolute: 1e-8 eps_optimal_relative: 1e-8 } }"
            )
        model_seconds = perf_counter() - started

        started = perf_counter()
        status = model.Solve()
        solve_seconds = perf_counter() - started
        if status != pywraplp.Solver.OPTIMAL:
            raise RuntimeError(f"OR-Tools status code: {status}")
        return SolverResult(
            float(objective.Value()), model_seconds, solve_seconds
        )


ADAPTERS: tuple[SolverAdapter, ...] = (
    ScipyAdapter(),
    PulpAdapter(),
    OrToolsAdapter(),
)


def available_solvers() -> list[str]:
    """Return IDs such as ``scipy/highs`` and ``pulp/PULP_CBC_CMD``."""
    return [
        f"{adapter.name}/{solver}"
        for adapter in ADAPTERS
        for solver in adapter.available_solvers()
    ]


def solve(problem: LinearProgram, solver_id: str) -> SolverResult:
    """Solve an LP using the adapter identified by ``backend/solver``."""
    parts = solver_id.split("/", maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Solver ID must use 'backend/name' format: {solver_id!r}")
    backend, solver_name = parts
    for adapter in ADAPTERS:
        if adapter.name == backend:
            return adapter.solve(problem, solver_name)
    raise ValueError(f"Unknown solver backend: {backend!r}")
