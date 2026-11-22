"""Canonical item used by optimization instances."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """A material with demand, stock, and a unit purchase cost."""

    id: str
    name: str
    demand: float
    inventory: float
    purchase_cost: float
