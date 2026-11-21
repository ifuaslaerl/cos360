"""Canonical item used by optimization instances."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """A material with demand, stock, and unit costs."""

    id: str
    name: str
    demand: float
    inventory: float
    purchase_cost: float
    production_cost: float
