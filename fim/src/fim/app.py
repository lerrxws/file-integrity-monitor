from collections.abc import Callable
import logging
from pathlib import Path
import sqlite3
import time

from .config import AppConfig
from .hashing import collect_hashes
from .incidents import find_incidents
from .monitor import FileDifference, scan_directory
from .storage import get_baseline, save_baseline


logger = logging.getLogger(__name__)


def run(
    settings: AppConfig,
    connection: sqlite3.Connection,
    notify: Callable[[dict[Path, FileDifference]], None],
) -> None:
    website_dir = settings.website_dir
    baseline = _load_or_create_baseline(website_dir, connection)

    logger.info(
        "Monitoring %s every %s seconds. Press Ctrl+C to stop.",
        website_dir, settings.scan_interval,
    )

    while True:
        differences = scan_directory(website_dir, baseline)
        incidents = find_incidents(
            website_dir, baseline, differences, settings.incident_rule,
        )
        notify(incidents)
        time.sleep(settings.scan_interval)


def _load_or_create_baseline(
    website_dir: Path,
    connection: sqlite3.Connection,
) -> dict[str, str]:
    baseline = get_baseline(connection)

    if baseline:
        logger.info("Loaded baseline for %d files.", len(baseline))
    else:
        baseline, errors = collect_hashes(website_dir)

        if errors:
            raise ValueError(f"Cannot create a baseline: {errors}")

        save_baseline(connection, baseline)
        logger.info("Created baseline for %d files. Initial content is assumed trusted.", len(baseline))

    return baseline
