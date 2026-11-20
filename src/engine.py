"""Linear optimization model for the multi-stage make-or-buy problem."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np
from scipy.optimize import linprog


@dataclass(frozen=True)
class Solution:
    """Optimal purchase, production, and inventory-use quantity vectors."""

    total_cost: float
    purchases: np.ndarray
    production: np.ndarray
    inventory_used: np.ndarray


class MakeOrBuyModel:
    """Build and solve a make-or-buy LP by adding items and recipe arcs."""

    def __init__(self) -> None:
        self.item_index: dict[str, int] = {}
        self._objective = np.zeros(0)
        self._restrictions = np.zeros((0, 0))
        self._restriction_limits: list[float] = []
        self._bounds: list[tuple[float, float | None]] = []
        self._recipes: set[tuple[int, int]] = set()

    def add_item(
        self,
        name: str,
        demand: float = 0.0,
        inventory: float = 0.0,
        *,
        purchase_cost: float,
        production_cost: float,
    ) -> None:
        """Add an item and its demand, available stock, and unit costs."""
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if name in self.item_index:
            raise ValueError(f"item {name!r} has already been added")

        demand_value = self._non_negative(demand, "demand")
        inventory_value = self._non_negative(inventory, "inventory")
        purchase_value = self._non_negative(purchase_cost, "purchase_cost")
        production_value = self._non_negative(production_cost, "production_cost")

        index = len(self.item_index)
        self.item_index[name] = index

        self._objective = np.pad(self._objective, (0, 3))
        self._restrictions = np.pad(self._restrictions, ((0, 1), (0, 3)))
        self._restriction_limits.append(-demand_value)
        self._bounds.extend([(0.0, None), (0.0, None), (0.0, inventory_value)])

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
        arc = (ingredient_index, product_index)
        if arc in self._recipes:
            raise ValueError(
                f"recipe from item {ingredient_index} to item {product_index} "
                "has already been added"
            )

        self._recipes.add(arc)
        self._add_restriction(
            ingredient_index, 3 * product_index + 1, amount_value
        )

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

    def solve(self) -> Solution:
        """Solve the current model and return its optimal vectors."""
        if not self.item_index:
            raise ValueError("add at least one item before solving")

        result = linprog(
            self._objective,
            A_ub=self._restrictions,
            b_ub=np.asarray(self._restriction_limits),
            bounds=self._bounds,
            method="highs",
        )
        if not result.success:
            raise RuntimeError(f"Optimization failed: {result.message}")

        quantities = result.x.reshape(len(self.item_index), 3)
        return Solution(
            total_cost=float(result.fun),
            purchases=quantities[:, 0].copy(),
            production=quantities[:, 1].copy(),
            inventory_used=quantities[:, 2].copy(),
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
