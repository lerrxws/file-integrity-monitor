from collections.abc import Callable
from enum import Enum
import logging
from pathlib import Path

from .hashing import collect_hashes


logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNVERIFIABLE = "unverifiable"


def scan_directory(
    website_dir: Path,
    baseline: dict[str, str],
    reported: dict[str, tuple[ChangeType, str | None]],
    report_change: Callable[[str, ChangeType], bool],
) -> None:
    current, errors = collect_hashes(website_dir)

    for path in sorted(baseline.keys() | current.keys() | errors.keys() | reported.keys()):
        if path in errors:
            difference = (ChangeType.UNVERIFIABLE, errors[path])
        elif any(error == "." or path.startswith(error + "/") for error in errors):
            continue
        elif path not in current:
            difference = (ChangeType.DELETED, None) if path in baseline else None
        elif path not in baseline:
            difference = (ChangeType.ADDED, current[path])
        elif current[path] != baseline[path]:
            difference = (ChangeType.MODIFIED, current[path])
        else:
            difference = None

        if difference is None:
            if reported.pop(path, None) is not None:
                logger.info("Recovered: %r", path)
        elif reported.get(path) != difference:
            if path in errors:
                logger.error("Cannot verify %r: %s", path, errors[path])

            if report_change(str(website_dir / path), difference[0]):
                reported[path] = difference
