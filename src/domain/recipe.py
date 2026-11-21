"""Canonical production recipe."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Recipe:
    """Quantity of an ingredient required per product unit."""

    ingredient: str
    product: str
    amount: float
