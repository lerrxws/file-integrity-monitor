from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
import logging
from pathlib import Path
import sqlite3
import time

from .config import AppConfig
from .hashing import FileObservation, collect_observations
from .storage import get_expected_hashes


logger = logging.getLogger(__name__)


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


@dataclass(frozen=True)
class ScanResult:
    root: Path
    files: dict[str, FileObservation]
    errors: dict[str, str]


def scan_directory(website_dir: Path) -> ScanResult:
    return ScanResult(website_dir, *collect_observations(website_dir))


def evaluate_scan(scan: ScanResult, expected: Mapping[str, str]) -> dict[Path, FileDifference]:
    incidents = {}
    for path in sorted(expected.keys() | scan.files.keys() | scan.errors.keys()):
        if path in scan.errors:
            difference = FileDifference(ChangeType.UNVERIFIABLE, error=scan.errors[path])
        elif any(parent == "." or path.startswith(parent + "/") for parent in scan.errors):
            continue
        elif path not in scan.files:
            difference = FileDifference(ChangeType.DELETED)
        elif path not in expected:
            difference = FileDifference(ChangeType.ADDED, scan.files[path].sha256)
        elif scan.files[path].sha256 != expected[path]:
            difference = FileDifference(ChangeType.MODIFIED, scan.files[path].sha256)
        else:
            continue
        incidents[scan.root / path] = difference
    return incidents


def check_once(
    settings: AppConfig, connection: sqlite3.Connection, *, today: date | None = None,
) -> dict[Path, FileDifference]:
    try:
        current_date = today if today is not None else datetime.now(settings.timezone).date()
        scan = scan_directory(settings.website_dir)
        expected = get_expected_hashes(connection, current_date)
        incidents = evaluate_scan(scan, expected)
        if "index.html" not in expected and "." not in scan.errors and "index.html" not in scan.errors:
            incidents[scan.root / "index.html"] = FileDifference(
                ChangeType.UNVERIFIABLE, error=f"No expected index.html hash for {current_date}.",
            )
        return incidents
    except Exception as exc:
        logger.error("Cannot evaluate integrity scan (%s).", type(exc).__name__)
        return {settings.website_dir: FileDifference(
            ChangeType.UNVERIFIABLE, error=f"Scan failed: {type(exc).__name__}: {exc}",
        )}


def run(
    settings: AppConfig, connection: sqlite3.Connection,
    notify: Callable[[dict[Path, FileDifference]], None],
) -> None:
    logger.info("Monitoring %s every %s seconds. Press Ctrl+C to stop.",
                settings.website_dir, settings.scan_interval)
    while True:
        notify(check_once(settings, connection))
        time.sleep(settings.scan_interval)
