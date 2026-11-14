from collections.abc import Callable
import logging
from pathlib import Path
import sqlite3
import time

from .config import AppConfig
from .hashing import collect_hashes
from .monitor import FileDifference, scan_directory
from .storage import get_baseline, save_baseline


logger = logging.getLogger(__name__)


def run(
    settings: AppConfig,
    connection: sqlite3.Connection,
    notify: Callable[[dict[Path, FileDifference]], None],
) -> None:
    website_dir = settings.website_dir
    baseline = get_baseline(connection)

    if baseline:
        logger.info("Loaded baseline for %d files.", len(baseline))
    else:
        baseline, errors = collect_hashes(website_dir)

        if errors:
            raise ValueError(f"Cannot create a baseline: {errors}")

        save_baseline(connection, baseline)
        logger.info("Created baseline for %d files. Initial content is assumed trusted.", len(baseline))

    logger.info(
        "Monitoring %s every %s seconds. Press Ctrl+C to stop.",
        website_dir, settings.scan_interval,
    )

    while True:
        differences = scan_directory(website_dir, baseline)
        notify(differences)
        time.sleep(settings.scan_interval)
