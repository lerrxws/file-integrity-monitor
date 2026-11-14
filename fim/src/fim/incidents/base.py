from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..monitor import ScanResult


class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNVERIFIABLE = "unverifiable"


@dataclass(frozen=True)
class FileDifference:
    change_type: ChangeType
    sha256: str | None = None
    error: str | None = None


class IncidentRule(ABC):
    """Evaluate one complete scan and return every active incident."""

    @abstractmethod
    def evaluate(
        self, scan: ScanResult, baseline: Mapping[str, str],
    ) -> dict[Path, FileDifference]:
        raise NotImplementedError
