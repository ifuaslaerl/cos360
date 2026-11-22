"""Standardizer for Satisfactory's native Docs.json structure."""

import re
from typing import Any, Mapping

from src.domain.item import Item
from src.domain.problem_instance import ProblemInstance
from src.domain.recipe import Recipe


class SatisfactoryDocsStandardizer:
    """Maps Satisfactory item and recipe classes to the canonical model."""

    ITEM_NATIVE_CLASSES = ("FGItemDescriptor", "FGResourceDescriptor")

    ITEM_PATTERN = re.compile(r"/(?P<item>Desc_[A-Za-z0-9_]+)\.(?P=item)_C")
    AMOUNT_PATTERN = re.compile(
        r'ItemClass="[^"]*/(?P<item>Desc_[A-Za-z0-9_]+)\.(?P=item)_C\'",Amount=(?P<amount>[-0-9.]+)'
    )
    MACHINE_PATTERN = re.compile(r"/(?P<cls>Build_[A-Za-z0-9_]+)\.(?P=cls)_C")

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
        self.default_purchase_cost = purchase_cost
        self.default_production_cost = production_cost
        self.errors: list[str] = []

    def standardize(self, payload: list[dict[str, Any]]) -> ProblemInstance:
        self.errors.clear()
        item_data = self._collect_item_classes(payload)
        recipe_data = self._collect_classes(payload, "FGRecipe")
        machine_power = self._collect_machine_power(payload)
        item_ids = {
            entry["ClassName"]
            for entry in item_data
            if str(entry.get("ClassName", "")).startswith("Desc_")
        }
        configured_ids = set(self.demands) | set(self.inventories)
        selected_item_ids = (
            item_ids if not configured_ids else item_ids & configured_ids
        )
        recipes: list[Recipe] = []
        for index, entry in enumerate(recipe_data):
            recipe = self._parse_recipe(entry, selected_item_ids, machine_power, index)
            if recipe is not None:
                recipes.append(recipe)

        items = tuple(
            Item(
                id=item_id,
                name=str(entry.get("mDisplayName", item_id)),
                demand=self.demands.get(item_id, 0.0),
                inventory=self.inventories.get(item_id, 0.0),
                purchase_cost=self._purchase_cost(entry),
            )
            for item_id, entry in self._unique_items(
                item_data, selected_item_ids
            ).items()
        )
        return ProblemInstance("satisfactory", items, tuple(recipes))

    def _purchase_cost(self, entry: dict[str, Any]) -> float:
        raw = entry.get("mResourceSinkPoints")
        try:
            return float(raw)
        except (TypeError, ValueError):
            return self.default_purchase_cost

    def _collect_item_classes(
        self, payload: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        classes: list[dict[str, Any]] = []
        for group in payload:
            native_class = str(group.get("NativeClass", ""))
            if any(name in native_class for name in self.ITEM_NATIVE_CLASSES):
                classes.extend(
                    entry
                    for entry in group.get("Classes", [])
                    if isinstance(entry, dict)
                )
        return classes

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

    @staticmethod
    def _collect_machine_power(payload: list[dict[str, Any]]) -> dict[str, float]:
        power: dict[str, float] = {}
        for group in payload:
            for entry in group.get("Classes", []):
                if not isinstance(entry, dict) or "mPowerConsumption" not in entry:
                    continue
                try:
                    power[str(entry["ClassName"])] = float(entry["mPowerConsumption"])
                except (TypeError, ValueError):
                    continue
        return power

    def _parse_recipe(
        self,
        entry: dict[str, Any],
        item_ids: set[str],
        machine_power: dict[str, float],
        index: int,
    ) -> Recipe | None:
        ingredients = self._parse_amounts(str(entry.get("mIngredients", "")))
        products = self._parse_amounts(str(entry.get("mProduct", "")))
        if not ingredients or not products:
            return None
        if any(
            item not in item_ids or amount <= 0
            for item, amount in ingredients + products
        ):
            return None
        product, product_amount = products[0]
        normalized_ingredients = tuple(
            (ingredient, amount / product_amount) for ingredient, amount in ingredients
        )
        production_cost = self._production_cost(entry, product_amount, machine_power)
        recipe_id = str(entry.get("ClassName", f"recipe_{index}"))
        return Recipe(
            id=recipe_id,
            product=product,
            ingredients=normalized_ingredients,
            production_cost=production_cost,
        )

    def _production_cost(
        self,
        entry: dict[str, Any],
        product_amount: float,
        machine_power: dict[str, float],
    ) -> float:
        try:
            duration = float(entry.get("mManufactoringDuration", 0.0))
        except (TypeError, ValueError):
            duration = 0.0
        power = self._machine_power(str(entry.get("mProducedIn", "")), machine_power)
        if duration <= 0 or power is None:
            return self.default_production_cost
        return power * duration / product_amount

    def _machine_power(
        self, produced_in: str, machine_power: dict[str, float]
    ) -> float | None:
        match = self.MACHINE_PATTERN.search(produced_in)
        if match is None:
            return None
        return machine_power.get(f"{match.group('cls')}_C")

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
