"""Linear optimization model for the multi-stage make-or-buy problem."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np
from scipy.optimize import linprog


class InfeasibleError(RuntimeError):
    """Raised when the capacities leave no plan that meets the demand."""


@dataclass(frozen=True)
class Solution:
    """Optimal purchase, production, and inventory-use quantity vectors."""

    total_cost: float
    purchases: np.ndarray
    production: np.ndarray
    inventory_used: np.ndarray


@dataclass(frozen=True)
class LinearProgram:
    """Solver-independent representation of a linear minimization problem."""

    objective: np.ndarray
    inequalities: np.ndarray
    limits: np.ndarray
    bounds: tuple[tuple[float, float | None], ...]


class MakeOrBuyModel:
    """Build and solve a make-or-buy LP by adding items and recipe arcs."""

    def __init__(self) -> None:
        self.item_index: dict[str, int] = {}
        self._objective = np.zeros(0)
        self._restrictions = np.zeros((0, 0))
        self._restriction_limits: list[float] = []
        self._bounds: list[tuple[float, float | None]] = []
        self._recipes: dict[tuple[int, int], float] = {}

    def add_item(
        self,
        name: str,
        demand: float = 0.0,
        inventory: float = 0.0,
        *,
        purchase_cost: float,
        production_cost: float,
        purchase_capacity: float | None = None,
        production_capacity: float | None = None,
    ) -> None:
        """Add an item with its demand, stock, unit costs, and optional capacities.

        A capacity of ``None`` means unlimited.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if name in self.item_index:
            raise ValueError(f"item {name!r} has already been added")

        demand_value = self._non_negative(demand, "demand")
        inventory_value = self._non_negative(inventory, "inventory")
        purchase_value = self._non_negative(purchase_cost, "purchase_cost")
        production_value = self._non_negative(production_cost, "production_cost")
        purchase_limit = self._capacity(purchase_capacity, "purchase_capacity")
        production_limit = self._capacity(production_capacity, "production_capacity")

        index = len(self.item_index)
        self.item_index[name] = index

        self._objective = np.pad(self._objective, (0, 3))
        self._restrictions = np.pad(self._restrictions, ((0, 1), (0, 3)))
        self._restriction_limits.append(-demand_value)
        self._bounds.extend(
            [(0.0, purchase_limit), (0.0, production_limit), (0.0, inventory_value)]
        )

        purchase_variable = 3 * index
        production_variable = purchase_variable + 1
        inventory_variable = purchase_variable + 2
        self._modify_objective(purchase_variable, purchase_value)
        self._modify_objective(production_variable, production_value)
        self._add_restriction(index, purchase_variable, -1.0)
        self._add_restriction(index, production_variable, -1.0)
        self._add_restriction(index, inventory_variable, -1.0)

    def add_recipe(
        self, ingredient: str | int, product: str | int, amount: float
    ) -> None:
        """Add a recipe using item names or their indices."""
        ingredient_index = self._resolve_item_index(ingredient, "ingredient")
        product_index = self._resolve_item_index(product, "product")
        amount_value = self._positive(amount, "amount")
        if ingredient_index == product_index:
            raise ValueError("an item cannot be an ingredient of itself")
        arc = (ingredient_index, product_index)
        if arc in self._recipes:
            raise ValueError(
                f"recipe from item {ingredient_index} to item {product_index} "
                "has already been added"
            )

        self._recipes[arc] = amount_value
        self._add_restriction(
            ingredient_index, 3 * product_index + 1, amount_value
        )

    def set_demand(self, item: str | int, demand: float) -> None:
        """Replace the external demand of an item."""
        index = self._resolve_item_index(item, "item")
        self._restriction_limits[index] = -self._non_negative(demand, "demand")

    def set_inventory(self, item: str | int, inventory: float) -> None:
        """Replace the available stock of an item."""
        index = self._resolve_item_index(item, "item")
        value = self._non_negative(inventory, "inventory")
        self._bounds[3 * index + 2] = (0.0, value)

    def set_purchase_cost(self, item: str | int, cost: float) -> None:
        """Replace the unit purchase cost of an item."""
        index = self._resolve_item_index(item, "item")
        self._objective[3 * index] = self._non_negative(cost, "purchase_cost")

    def set_production_cost(self, item: str | int, cost: float) -> None:
        """Replace the unit production cost of an item."""
        index = self._resolve_item_index(item, "item")
        self._objective[3 * index + 1] = self._non_negative(cost, "production_cost")

    def set_purchase_capacity(self, item: str | int, capacity: float | None) -> None:
        """Replace the purchase capacity of an item (``None`` is unlimited)."""
        index = self._resolve_item_index(item, "item")
        self._bounds[3 * index] = (0.0, self._capacity(capacity, "purchase_capacity"))

    def set_production_capacity(self, item: str | int, capacity: float | None) -> None:
        """Replace the production capacity of an item (``None`` is unlimited)."""
        index = self._resolve_item_index(item, "item")
        self._bounds[3 * index + 1] = (
            0.0,
            self._capacity(capacity, "production_capacity"),
        )

    @property
    def item_names(self) -> list[str]:
        """Item names ordered by index."""
        return list(self.item_index)

    @property
    def recipes(self) -> dict[tuple[int, int], float]:
        """Amount of ingredient needed per unit of product, by (ingredient, product)."""
        return dict(self._recipes)

    @property
    def demands(self) -> np.ndarray:
        """External demand of each item."""
        return -np.asarray(self._restriction_limits)

    @property
    def purchase_costs(self) -> np.ndarray:
        """Unit purchase cost of each item."""
        return self._objective[0::3].copy()

    @property
    def production_costs(self) -> np.ndarray:
        """Unit production cost of each item."""
        return self._objective[1::3].copy()

    @property
    def inventories(self) -> np.ndarray:
        """Initial stock of each item."""
        return np.array([upper for _, upper in self._bounds[2::3]])

    @property
    def purchase_capacities(self) -> list[float | None]:
        """Purchase capacity of each item (``None`` is unlimited)."""
        return [upper for _, upper in self._bounds[0::3]]

    @property
    def production_capacities(self) -> list[float | None]:
        """Production capacity of each item (``None`` is unlimited)."""
        return [upper for _, upper in self._bounds[1::3]]

    def _resolve_item_index(self, item: str | int, role: str) -> int:
        if isinstance(item, str):
            try:
                return self.item_index[item]
            except KeyError:
                raise KeyError(f"unknown {role} {item!r}") from None
        if isinstance(item, bool) or not isinstance(item, (int, np.integer)):
            raise TypeError(f"{role} must be an item name or index")
        if not 0 <= item < len(self.item_index):
            raise IndexError(
                f"{role} index must be between 0 and {len(self.item_index) - 1}"
            )
        return int(item)

    def solve(self, method: str = "highs") -> Solution:
        """Solve the current model and return its optimal vectors."""
        problem = self.export_linear_program()
        result = linprog(
            problem.objective,
            A_ub=problem.inequalities,
            b_ub=problem.limits,
            bounds=problem.bounds,
            method=method,
        )
        if result.status == 2:
            raise InfeasibleError(f"No feasible plan: {result.message}")
        if not result.success:
            raise RuntimeError(f"Optimization failed: {result.message}")

        quantities = result.x.reshape(len(self.item_index), 3)
        return Solution(
            total_cost=float(result.fun),
            purchases=quantities[:, 0].copy(),
            production=quantities[:, 1].copy(),
            inventory_used=quantities[:, 2].copy(),
        )

    def export_linear_program(self) -> LinearProgram:
        """Return copies of the LP data for use by different solver libraries."""
        if not self.item_index:
            raise ValueError("add at least one item before solving")
        return LinearProgram(
            objective=self._objective.copy(),
            inequalities=self._restrictions.copy(),
            limits=np.asarray(self._restriction_limits, dtype=float),
            bounds=tuple(self._bounds),
        )

    def _add_restriction(
        self, restriction_index: int, variable_index: int, coefficient: float
    ) -> None:
        self._restrictions[restriction_index, variable_index] += coefficient

    def _modify_objective(self, variable_index: int, coefficient: float) -> None:
        self._objective[variable_index] += coefficient

    @staticmethod
    def _non_negative(value: float, name: str) -> float:
        number = MakeOrBuyModel._finite_number(value, name)
        if number < 0:
            raise ValueError(f"{name} must be non-negative")
        return number

    @staticmethod
    def _capacity(value: float | None, name: str) -> float | None:
        if value is None:
            return None
        return MakeOrBuyModel._non_negative(value, name)

    @staticmethod
    def _positive(value: float, name: str) -> float:
        number = MakeOrBuyModel._finite_number(value, name)
        if number <= 0:
            raise ValueError(f"{name} must be positive")
        return number

    @staticmethod
    def _finite_number(value: float, name: str) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be a finite number")
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} must be a finite number") from error
        if not isfinite(number):
            raise ValueError(f"{name} must be a finite number")
        return number
