"""Demand configuration source."""

import json
from pathlib import Path


class DemandConfigSource:
    """Loads item demand quantities from a JSON configuration file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, float]:
        return self._load_section("demands")

    def load_inventories(self) -> dict[str, float]:
        """Load optional initial inventory quantities."""
        return self._load_section("inventories")

    def _load_section(self, section: str) -> dict[str, float]:
        if not self.path.is_file():
            raise FileNotFoundError(f"demand configuration not found: {self.path}")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        raw_values = payload.get(section, {}) if isinstance(payload, dict) else None
        if not isinstance(raw_values, dict):
            raise ValueError(f"demand configuration must contain an object '{section}'")
        values: dict[str, float] = {}
        for item, quantity in raw_values.items():
            value = float(quantity)
            if value < 0:
                raise ValueError(f"{section} for {item!r} must be non-negative")
            values[str(item)] = value
        return values
