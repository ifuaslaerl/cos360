"""Random instance generator for the make-or-buy problem."""

from __future__ import annotations

import random

from src.legacy.engine import MakeOrBuyModel


def random_model(
    n_items: int = 10,
    seed: int | None = None,
    arc_probability: float = 0.25,
    stock_probability: float = 0.4,
    capacity_probability: float = 0.3,
) -> MakeOrBuyModel:
    """Draw a random acyclic model with items ``p1, ..., pN``.

    Only production is capacitated, so every drawn instance stays feasible.
    """
    if n_items < 1:
        raise ValueError("n_items must be at least 1")
    probabilities = (arc_probability, stock_probability, capacity_probability)
    if not all(0 <= p <= 1 for p in probabilities):
        raise ValueError("probabilities must be between 0 and 1")
    rng = random.Random(seed)

    recipes = {
        (i, j): round(rng.uniform(0.2, 1.5), 2)
        for j in range(n_items)
        for i in range(j)
        if rng.random() < arc_probability
    }
    is_ingredient = {i for i, _ in recipes}

    items = []
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
        items.append((demand, stock, purchase, production))

    need = [0.0] * n_items
    for j in reversed(range(n_items)):
        need[j] = items[j][0] + sum(
            r * need[k] for (i, k), r in recipes.items() if i == j
        )

    capacity_rng = random.Random(f"capacity-{seed}")
    model = MakeOrBuyModel()
    for j, (demand, stock, purchase, production) in enumerate(items):
        has_capacity = capacity_rng.random() < capacity_probability
        fraction = capacity_rng.uniform(0.3, 0.9)
        model.add_item(
            f"p{j + 1}",
            demand=demand,
            inventory=stock,
            purchase_cost=purchase,
            production_cost=production,
            production_capacity=round(need[j] * fraction, 1)
            if has_capacity and need[j] > 0
            else None,
        )
    for (i, j), amount in recipes.items():
        model.add_recipe(i, j, amount)
    return model
