"""Source for the localized Satisfactory Docs.json export."""

import json
from pathlib import Path
from typing import Any

from src.etl.dataset_source import DatasetSource


class SatisfactoryDocsSource(DatasetSource):
    """Loads Satisfactory's UTF-16 Docs.json from disk."""

    def __init__(self, path: str | Path = "Datasets/Satisfactory/Docs.json") -> None:
        self.path = Path(path)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            raise FileNotFoundError(f"Docs.json not found: {self.path}")
        payload = json.loads(self.path.read_text(encoding="utf-16"))
        if not isinstance(payload, list):
            raise ValueError("Satisfactory Docs.json root must be a list")
        return payload
