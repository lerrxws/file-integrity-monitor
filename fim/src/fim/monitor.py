from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .hashing import collect_hashes


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


def scan_directory(
    website_dir: Path,
    baseline: dict[str, str],
) -> dict[Path, FileDifference]:
    current, errors = collect_hashes(website_dir)
    differences = {}

    for path in sorted(baseline.keys() | current.keys() | errors.keys()):
        if path in errors:
            difference = FileDifference(ChangeType.UNVERIFIABLE, error=errors[path])
        elif any(error == "." or path.startswith(error + "/") for error in errors):
            continue
        elif path not in current:
            difference = FileDifference(ChangeType.DELETED)
        elif path not in baseline:
            difference = FileDifference(ChangeType.ADDED, sha256=current[path])
        elif current[path] != baseline[path]:
            difference = FileDifference(ChangeType.MODIFIED, sha256=current[path])
        else:
            continue

        differences[website_dir / path] = difference

    return differences
