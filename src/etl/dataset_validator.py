"""Dataset validation and non-fatal error collection."""

from typing import Any

from ..domain.problem_instance import ProblemInstance


class DatasetValidator:
    """Validates canonical instances and returns all detected errors."""

    def validate(self, instance: ProblemInstance) -> tuple[str, ...]:
        errors: list[str] = []
        item_ids = [item.id for item in instance.items]
        if len(item_ids) != len(set(item_ids)):
            errors.append("items: duplicate ids")
        known_ids = set(item_ids)
        for item in instance.items:
            for field in (
                "demand",
                "inventory",
                "purchase_cost",
                "production_cost",
            ):
                if getattr(item, field) < 0:
                    errors.append(f"items[{item.id}].{field}: must be non-negative")
        for index, recipe in enumerate(instance.recipes):
            if recipe.ingredient not in known_ids:
                errors.append(
                    f"recipes[{index}].ingredient: unknown item {recipe.ingredient!r}"
                )
            if recipe.product not in known_ids:
                errors.append(
                    f"recipes[{index}].product: unknown item {recipe.product!r}"
                )
            if recipe.amount <= 0:
                errors.append(f"recipes[{index}].amount: must be positive")
        return tuple(errors)
