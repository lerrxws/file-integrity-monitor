from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Protocol

from .monitor import ChangeType, FileDifference


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChangeContext:
    """Observed facts and the expected hash from the original baseline."""

    path: Path
    difference: FileDifference
    expected_hash: str | None


class IncidentRule(Protocol):
    """Match an incident condition using facts collected for one file."""

    def matches(self, context: ChangeContext) -> bool:
        ...


class AnyChangeRule:
    """Treat every observed difference as an incident."""

    def matches(self, context: ChangeContext) -> bool:
        return True


class HashMismatchRule:
    def matches(self, context: ChangeContext) -> bool:
        if context.difference.change_type == ChangeType.UNVERIFIABLE:
            return False

        return context.difference.sha256 != context.expected_hash


def find_incidents(
    website_dir: Path,
    baseline: dict[str, str],
    differences: dict[Path, FileDifference],
    incident_rule: IncidentRule,
) -> dict[Path, FileDifference]:
    """Select incidents, including unverifiable files and rule evaluation failures."""
    incidents = {}

    for path, difference in differences.items():
        if difference.change_type == ChangeType.UNVERIFIABLE:
            incidents[path] = difference
            continue

        relative_path = path.relative_to(website_dir).as_posix()

        try:
            context = ChangeContext(path, difference, baseline.get(relative_path))
            matched = incident_rule.matches(context)

            if not isinstance(matched, bool):
                raise TypeError("IncidentRule.matches must return a boolean.")
        except Exception as exc:
            logger.error("Cannot evaluate %r (%s); reporting incident.", str(path), type(exc).__name__)
            incidents[path] = difference
            continue

        if matched:
            logger.debug("Incident rule matched: %r", str(path))
            incidents[path] = difference

    return incidents
