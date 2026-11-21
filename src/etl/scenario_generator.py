"""Random Satisfactory scenario generation."""

import json
import random
from pathlib import Path
from typing import Sequence


class SatisfactoryScenarioGenerator:
    """Generates reproducible JSON files with random demands and inventories."""

    def __init__(
        self,
        output_dir: str | Path,
        item_ids: Sequence[str],
        seed: int = 360,
    ) -> None:
        if not item_ids:
            raise ValueError("item_ids must not be empty")
        self.output_dir = Path(output_dir)
        self.item_ids = tuple(dict.fromkeys(item_ids))
        self.random = random.Random(seed)

    def generate(
        self,
        count: int = 10,
        items_per_scenario: int | None = None,
        items_per_scenario_range: tuple[int, int] | None = None,
        demand_range: tuple[int, int] = (1, 50),
        inventory_range: tuple[int, int] = (0, 100),
        use_all_items: bool = False,
    ) -> tuple[Path, ...]:
        if count < 1:
            raise ValueError("count must be positive")
        if not use_all_items and (
            items_per_scenario is None and items_per_scenario_range is None
        ):
            raise ValueError("an item count or item count range is required")
        if items_per_scenario_range is not None:
            low, high = items_per_scenario_range
            if low < 2 or high < low:
                raise ValueError("invalid items_per_scenario_range")
            if high > len(self.item_ids):
                raise ValueError("item count range exceeds available item_ids")
        elif not use_all_items and (
            items_per_scenario is None or items_per_scenario > len(self.item_ids)
        ):
            raise ValueError("items_per_scenario exceeds available item_ids")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for index in range(1, count + 1):
            if use_all_items:
                selected = self.random.sample(self.item_ids, len(self.item_ids))
            else:
                item_count = (
                    self.random.randint(*items_per_scenario_range)
                    if items_per_scenario_range is not None
                    else items_per_scenario
                )
                selected = self.random.sample(self.item_ids, item_count)
            split = (len(selected) + 1) // 2
            demand_items = selected[:split]
            inventory_items = selected[split:]
            payload = {
                "demands": {
                    item_id: self.random.randint(*demand_range)
                    for item_id in demand_items
                },
                "inventories": {
                    item_id: self.random.randint(*inventory_range)
                    for item_id in inventory_items
                },
            }
            path = self.output_dir / f"scenario_{index:03d}.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            paths.append(path)
        return tuple(paths)
