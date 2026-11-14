from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .base import ChangeType, FileDifference, IncidentRule
from .hash_mismatch import HashMismatchIncidentRule
from ..monitor import ScanResult


def relative_file_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise ValueError("Managed paths must be normalized relative file paths.")

    path = PurePosixPath(value)

    if path.is_absolute() or ".." in path.parts or str(path) != value or value == ".":
        raise ValueError(f"Invalid relative file path: {value!r}.")

    return value


def _read_manifest(path: Path) -> dict[str, str]:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)

    with os.fdopen(descriptor, "rb") as file:
        if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
            raise ValueError("Publisher manifest must be a regular file.")

        manifest = json.load(file)

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
