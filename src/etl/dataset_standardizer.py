"""Conversion from external JSON to the canonical domain model."""

from typing import Any

from ..domain.item import Item
from ..domain.problem_instance import ProblemInstance
from ..domain.recipe import Recipe


class DatasetStandardizer:
    """Maps configured JSON fields into canonical items and recipes."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def standardize(self, payload: dict[str, Any]) -> ProblemInstance:
        self.errors.clear()
        dataset = str(payload.get("dataset", "dataset"))
        raw_items = payload.get("items", [])
        raw_recipes = payload.get("recipes", [])
        if not isinstance(raw_items, list) or not isinstance(raw_recipes, list):
            raise ValueError("dataset must contain list fields 'items' and 'recipes'")

        items: list[Item] = []
        for index, raw in enumerate(raw_items):
            try:
                items.append(
                    Item(
                        id=str(raw["id"]),
                        name=str(raw.get("name", raw["id"])),
                        demand=float(raw.get("demand", 0.0)),
                        inventory=float(raw.get("inventory", 0.0)),
                        purchase_cost=float(raw["purchase_cost"]),
                        production_cost=float(raw["production_cost"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as error:
                self.errors.append(f"items[{index}]: {error}")
        recipes: list[Recipe] = []
        for index, raw in enumerate(raw_recipes):
            try:
                recipes.append(
                    Recipe(
                        ingredient=str(raw["ingredient"]),
                        product=str(raw["product"]),
                        amount=float(raw["amount"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as error:
                self.errors.append(f"recipes[{index}]: {error}")
        return ProblemInstance(dataset, items, recipes)
