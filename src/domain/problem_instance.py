"""Validated optimization problem representation."""

from dataclasses import dataclass

from .item import Item
from .recipe import Recipe


@dataclass(frozen=True)
class ProblemInstance:
    """Items and recipes belonging to one dataset."""

    dataset: str
    items: tuple[Item, ...]
    recipes: tuple[Recipe, ...]
