from collections.abc import Mapping
from pathlib import Path

from .base import ChangeType, FileDifference, IncidentRule
from ..monitor import ScanResult


class HashMismatchIncidentRule(IncidentRule):
    """Compare supplied facts with expectations without reading files."""

    def evaluate(
        self, scan: ScanResult, baseline: Mapping[str, str],
    ) -> dict[Path, FileDifference]:
        incidents = {}

        for path in sorted(baseline.keys() | scan.files.keys() | scan.errors.keys()):
            if path in scan.errors:
                difference = FileDifference(ChangeType.UNVERIFIABLE, error=scan.errors[path])
            elif any(parent == "." or path.startswith(parent + "/") for parent in scan.errors):
                continue
            elif path not in scan.files:
                difference = FileDifference(ChangeType.DELETED)
            elif path not in baseline:
                difference = FileDifference(ChangeType.ADDED, scan.files[path].sha256)
            elif scan.files[path].sha256 != baseline[path]:
                difference = FileDifference(ChangeType.MODIFIED, scan.files[path].sha256)
            else:
                continue

            incidents[scan.root / path] = difference

        return incidents
