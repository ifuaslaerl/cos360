"""Optimization engine independent from solver implementations."""

import numpy as np

from ..domain.problem_instance import ProblemInstance
from ..domain.solution import Solution
from ..monitoring.execution_monitor import ExecutionMonitor
from .linear_program import LinearProgram
from .solver_adapter import SolverAdapter


class OptimizationEngine:
    """Builds the notebook LP and executes an injected solver adapter."""

    def __init__(self, monitor: ExecutionMonitor | None = None) -> None:
        self.monitor = monitor or ExecutionMonitor()

    def solve(
        self,
        instance: ProblemInstance,
        adapter: SolverAdapter,
        solver: str,
        repeat: int,
    ) -> Solution:
        try:
            problem = self._build_problem(instance)

            (objective, _solver_elapsed, values), elapsed, memory = (
                self.monitor.measure(lambda: adapter.solve(problem, solver))
            )
            quantities = values.reshape(len(instance.items), 3)
            rows = tuple(
                {
                    "Item": item.id,
                    "Compra": float(quantities[index, 0]),
                    "Produção": float(quantities[index, 1]),
                    "EstoqueUtilizado": float(quantities[index, 2]),
                    "Custo": float(
                        item.purchase_cost * quantities[index, 0]
                        + item.production_cost * quantities[index, 1]
                    ),
                }
                for index, item in enumerate(instance.items)
            )
            return Solution(
                instance.dataset,
                f"{adapter.name}/{solver}",
                repeat,
                "optimal",
                objective,
                elapsed,
                memory,
                rows,
            )
        except Exception as error:
            return Solution(
                instance.dataset,
                f"{adapter.name}/{solver}",
                repeat,
                "error",
                None,
                self.monitor.last_elapsed_seconds,
                self.monitor.last_peak_memory_mib,
                (),
                (str(error),),
            )

    def _build_problem(self, instance: ProblemInstance) -> LinearProgram:
        item_count = len(instance.items)
        if not item_count:
            raise ValueError("instance must contain at least one item")
        indexes = {item.id: index for index, item in enumerate(instance.items)}
        objective = np.zeros(3 * item_count)
        restrictions = np.zeros((item_count, 3 * item_count))
        limits = np.zeros(item_count)
        bounds: list[tuple[float, float | None]] = []
        for index, item in enumerate(instance.items):
            purchase = 3 * index
            production = purchase + 1
            stock = purchase + 2
            objective[purchase] = item.purchase_cost
            objective[production] = item.production_cost
            restrictions[index, purchase] = -1.0
            restrictions[index, production] = -1.0
            restrictions[index, stock] = -1.0
            limits[index] = -item.demand
            bounds.extend(((0.0, None), (0.0, None), (0.0, item.inventory)))
        for recipe in instance.recipes:
            ingredient = indexes[recipe.ingredient]
            product = indexes[recipe.product]
            restrictions[ingredient, 3 * product + 1] += recipe.amount
        return LinearProgram(objective, restrictions, limits, tuple(bounds))

