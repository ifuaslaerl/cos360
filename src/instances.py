"""Random instance generator for the make-or-buy problem."""

from __future__ import annotations

import random

from src.engine import MakeOrBuyModel


def random_model(
    n_items: int = 10,
    seed: int | None = None,
    arc_probability: float = 0.25,
    stock_probability: float = 0.4,
) -> MakeOrBuyModel:
    """Draw a random acyclic model with items ``p1, ..., pN``."""
    if n_items < 1:
        raise ValueError("n_items must be at least 1")
    if not (0 <= arc_probability <= 1 and 0 <= stock_probability <= 1):
        raise ValueError("probabilities must be between 0 and 1")
    rng = random.Random(seed)

    recipes = {
        (i, j): round(rng.uniform(0.2, 1.5), 2)
        for j in range(n_items)
        for i in range(j)
        if rng.random() < arc_probability
    }
    is_ingredient = {i for i, _ in recipes}

    model = MakeOrBuyModel()
    full_cost: list[float] = []
    for j in range(n_items):
        production = round(rng.uniform(0.5, 5.0), 2)
        full_cost.append(
            production
            + sum(r * full_cost[i] for (i, k), r in recipes.items() if k == j)
        )
        purchase = round(full_cost[j] * rng.uniform(0.6, 1.8), 2)
        stock = round(rng.uniform(5, 50)) if rng.random() < stock_probability else 0
        demand = 0 if j in is_ingredient else round(rng.uniform(20, 100))
        model.add_item(
            f"p{j + 1}",
            demand=demand,
            inventory=stock,
            purchase_cost=purchase,
            production_cost=production,
        )
    for (i, j), amount in recipes.items():
        model.add_recipe(i, j, amount)
    return model
