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
        items_per_scenario: int = 5,
        demand_range: tuple[int, int] = (1, 50),
        inventory_range: tuple[int, int] = (0, 100),
    ) -> tuple[Path, ...]:
        if count < 1 or items_per_scenario < 1:
            raise ValueError("count and items_per_scenario must be positive")
        if items_per_scenario > len(self.item_ids):
            raise ValueError("items_per_scenario exceeds available item_ids")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for index in range(1, count + 1):
            selected = self.random.sample(self.item_ids, items_per_scenario)
            payload = {
                "demands": {
                    item_id: self.random.randint(*demand_range)
                    for item_id in selected
                },
                "inventories": {
                    item_id: self.random.randint(*inventory_range)
                    for item_id in selected
                },
            }
            path = self.output_dir / f"scenario_{index:03d}.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            paths.append(path)
        return tuple(paths)
