"""JSON-compatible dataset source."""

import json
from pathlib import Path
from typing import Any

from .dataset_source import DatasetSource


class JsonDatasetSource(DatasetSource):
    """Loads a dataset from a mapping, JSON text, or local JSON file."""

    def __init__(
        self,
        payload: dict[str, Any] | str | Path,
    ) -> None:
        self.payload = payload

    def load(self) -> dict[str, Any]:
        if isinstance(self.payload, dict):
            return self.payload
        if isinstance(self.payload, Path):
            return json.loads(Path(self.payload).read_text(encoding="utf-8"))
        if isinstance(self.payload, str) and len(self.payload) < 4096:
            candidate = Path(self.payload)
            if candidate.exists():
                return json.loads(candidate.read_text(encoding="utf-8"))
        value = json.loads(str(self.payload))
        if not isinstance(value, dict):
            raise ValueError("JSON dataset root must be an object")
        return value
