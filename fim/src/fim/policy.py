from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from .monitor import FileDifference


class ChangeDecision(str, Enum):
    APPROVED = "approved"
    INCIDENT = "incident"


@dataclass(frozen=True)
class ChangeAssessment:
    decision: ChangeDecision
    reason: str


class ChangePolicy(Protocol):
    """Assess approval of the exact observed path, operation, and content."""

    def assess(self, path: Path, difference: FileDifference) -> ChangeAssessment:
        ...


class ReportAllChangesPolicy:
    """Keep changes reportable until a trusted approval source is available."""

    def assess(self, path: Path, difference: FileDifference) -> ChangeAssessment:
        return ChangeAssessment(
            ChangeDecision.INCIDENT,
            "No trusted approval evidence is configured.",
        )
