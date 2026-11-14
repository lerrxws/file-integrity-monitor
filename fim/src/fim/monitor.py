from dataclasses import dataclass
from pathlib import Path

from .hashing import FileObservation, collect_observations


@dataclass(frozen=True)
class ScanResult:
    root: Path
    files: dict[str, FileObservation]
    errors: dict[str, str]


def scan_directory(website_dir: Path) -> ScanResult:
    return ScanResult(website_dir, *collect_observations(website_dir))
