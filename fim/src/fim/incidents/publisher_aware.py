from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import re

from fim.src.helpers.files import read_json_file, relative_file_path

from ..monitor import ScanResult
from .base import ChangeType, FileDifference, IncidentRule
from .hash_mismatch import HashMismatchIncidentRule


def _read_manifest(path: Path) -> dict[str, str]:
    manifest = read_json_file(path, regular_only=True)

    if (
        not isinstance(manifest, dict) or set(manifest) != {"version", "files"}
        or type(manifest["version"]) is not int or manifest["version"] != 1
        or not isinstance(manifest["files"], dict)
    ):
        raise ValueError("Publisher manifest must contain version 1 and a files mapping.")

    approvals = {}

    for name, digest in manifest["files"].items():
        relative_file_path(name)

        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
            raise ValueError(f"Invalid SHA-256 approval for {name!r}.")

        approvals[name] = digest.lower()

    return approvals


@dataclass(frozen=True)
class PublisherAwareIncidentRule(IncidentRule):
    manifest_path: Path
    paths: tuple[str, ...]

    def evaluate(
        self, scan: ScanResult, baseline: Mapping[str, str],
    ) -> dict[Path, FileDifference]:
        expected = dict(baseline)
        failures = {}

        try:
            approvals = _read_manifest(self.manifest_path)

            for path in self.paths:
                if path in approvals:
                    expected[path] = approvals[path]
                else:
                    failures[path] = f"Publisher approval missing for {path!r}."
        except (OSError, ValueError) as exc:
            failures = {path: f"Cannot verify publisher approval: {exc}" for path in self.paths}

        incidents = HashMismatchIncidentRule().evaluate(scan, expected)

        for path, error in failures.items():
            if any(parent == "." or path == parent or path.startswith(parent + "/") for parent in scan.errors):
                continue

            incidents[scan.root / path] = FileDifference(ChangeType.UNVERIFIABLE, error=error)

        return incidents
