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
            item_count = len(instance.items)
            recipe_count = len(instance.recipes)
            producers = self._producers_by_item(instance)
            problem = self._build_problem(instance, producers)

            (objective, _solver_elapsed, values), elapsed, memory = (
                self.monitor.measure(lambda: adapter.solve(problem, solver))
            )
            purchases = values[0:item_count]
            stocks = values[item_count : 2 * item_count]
            productions = values[2 * item_count : 2 * item_count + recipe_count]
            rows = tuple(
                {
                    "Item": item.id,
                    "Compra": float(purchases[index]),
                    "Produção": float(
                        sum(productions[recipe_index] for recipe_index in producers[item.id])
                    ),
                    "EstoqueUtilizado": float(stocks[index]),
                    "Custo": float(
                        item.purchase_cost * purchases[index]
                        + sum(
                            instance.recipes[recipe_index].production_cost
                            * productions[recipe_index]
                            for recipe_index in producers[item.id]
                        )
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

    @staticmethod
    def _producers_by_item(instance: ProblemInstance) -> dict[str, list[int]]:
        producers: dict[str, list[int]] = {item.id: [] for item in instance.items}
        for recipe_index, recipe in enumerate(instance.recipes):
            producers[recipe.product].append(recipe_index)
        return producers

    def _build_problem(
        self, instance: ProblemInstance, producers: dict[str, list[int]]
    ) -> LinearProgram:
        item_count = len(instance.items)
        recipe_count = len(instance.recipes)
        if not item_count:
            raise ValueError("instance must contain at least one item")
        indexes = {item.id: index for index, item in enumerate(instance.items)}
        variable_count = 2 * item_count + recipe_count
        objective = np.zeros(variable_count)
        restrictions = np.zeros((item_count, variable_count))
        limits = np.zeros(item_count)
        bounds: list[tuple[float, float | None]] = []

        for index, item in enumerate(instance.items):
            purchase = index
            stock = item_count + index
            objective[purchase] = item.purchase_cost
            restrictions[index, purchase] = -1.0
            restrictions[index, stock] = -1.0
            limits[index] = -item.demand
            bounds.append((0.0, None))
        for item in instance.items:
            bounds.append((0.0, item.inventory))

        for recipe_index, recipe in enumerate(instance.recipes):
            variable = 2 * item_count + recipe_index
            objective[variable] = recipe.production_cost
            product = indexes[recipe.product]
            restrictions[product, variable] += -1.0
            for ingredient, amount in recipe.ingredients:
                restrictions[indexes[ingredient], variable] += amount
            bounds.append((0.0, None))

        return LinearProgram(objective, restrictions, limits, tuple(bounds))
