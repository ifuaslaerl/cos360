"""Dataset source contract."""

from abc import ABC, abstractmethod
from typing import Any


class DatasetSource(ABC):
    """Extracts raw dataset payloads for the ETL pipeline."""

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Return one raw JSON-compatible dataset payload."""
