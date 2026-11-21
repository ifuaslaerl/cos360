"""Standardizer for Satisfactory's native Docs.json structure."""

import re
from typing import Any, Mapping

from src.domain.item import Item
from src.domain.problem_instance import ProblemInstance
from src.domain.recipe import Recipe


class SatisfactoryDocsStandardizer:
    """Maps Satisfactory item and recipe classes to the canonical model."""

    ITEM_PATTERN = re.compile(r"/(?P<item>Desc_[A-Za-z0-9_]+)\.(?P=item)_C")
    AMOUNT_PATTERN = re.compile(
        r'ItemClass="[^"]*/(?P<item>Desc_[A-Za-z0-9_]+)\.(?P=item)_C\'",Amount=(?P<amount>[-0-9.]+)'
    )

    def __init__(
        self,
        demand_item: str | None = None,
        demand: float = 1.0,
        purchase_cost: float = 1.0,
        production_cost: float = 1.0,
        demands: Mapping[str, float] | None = None,
        inventories: Mapping[str, float] | None = None,
    ) -> None:
        self.demands = dict(demands or {})
        self.inventories = dict(inventories or {})
        if demand_item is not None:
            self.demands[demand_item] = demand
        self.purchase_cost = purchase_cost
        self.production_cost = production_cost
        self.errors: list[str] = []

    def standardize(self, payload: list[dict[str, Any]]) -> ProblemInstance:
        self.errors.clear()
        item_data = self._collect_classes(payload, "FGItemDescriptor")
        recipe_data = self._collect_classes(payload, "FGRecipe")
        item_ids = {
            entry["ClassName"]
            for entry in item_data
            if str(entry.get("ClassName", "")).startswith("Desc_")
        }
        selected_recipes: dict[str, tuple[str, str, float]] = {}
        recipes: list[Recipe] = []
        for entry in recipe_data:
            parsed = self._parse_recipe(entry, item_ids)
            for ingredient, product, amount in parsed:
                if product not in selected_recipes:
                    selected_recipes[product] = (ingredient, product, amount)
                    recipes.append(Recipe(ingredient, product, amount))

        items = tuple(
            Item(
                id=item_id,
                name=str(entry.get("mDisplayName", item_id)),
                demand=self.demands.get(item_id, 0.0),
                inventory=self.inventories.get(item_id, 0.0),
                purchase_cost=self.purchase_cost,
                production_cost=self.production_cost,
            )
            for item_id, entry in self._unique_items(item_data, item_ids).items()
        )
        return ProblemInstance("satisfactory", items, tuple(recipes))

    @staticmethod
    def _collect_classes(
        payload: list[dict[str, Any]], native_class: str
    ) -> list[dict[str, Any]]:
        classes: list[dict[str, Any]] = []
        for group in payload:
            if native_class in str(group.get("NativeClass", "")):
                classes.extend(
                    entry
                    for entry in group.get("Classes", [])
                    if isinstance(entry, dict)
                )
        return classes

    def _parse_recipe(
        self, entry: dict[str, Any], item_ids: set[str]
    ) -> tuple[tuple[str, str, float], ...]:
        ingredients = self._parse_amounts(str(entry.get("mIngredients", "")))
        products = self._parse_amounts(str(entry.get("mProduct", "")))
        if not ingredients or not products:
            return ()
        valid_products = [
            (product, amount)
            for product, amount in products
            if product in item_ids and amount > 0
        ]
        if not valid_products:
            return ()
        product, product_amount = valid_products[0]
        result = []
        for ingredient, ingredient_amount in ingredients:
            if ingredient in item_ids and ingredient_amount > 0:
                result.append((ingredient, product, ingredient_amount / product_amount))
        return tuple(result)

    @classmethod
    def _parse_amounts(cls, value: str) -> tuple[tuple[str, float], ...]:
        return tuple(
            (f"{match.group('item')}_C", float(match.group("amount")))
            for match in cls.AMOUNT_PATTERN.finditer(value)
        )

    @staticmethod
    def _unique_items(
        entries: list[dict[str, Any]], item_ids: set[str]
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for entry in entries:
            item_id = str(entry.get("ClassName", ""))
            if item_id in item_ids:
                result.setdefault(item_id, entry)
        return result
