"""Canonical production recipe."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Recipe:
    """One way of producing one unit of ``product`` from its ``ingredients``."""

    id: str
    product: str
    ingredients: tuple[tuple[str, float], ...]
    production_cost: float = 0.0
