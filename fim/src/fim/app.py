from collections.abc import Callable
import logging
from pathlib import Path
import sqlite3
import time

from .config import AppConfig
from .hashing import collect_hashes
from .incidents import ChangeType, FileDifference
from .locking import scan_lock
from .monitor import scan_directory
from .storage import get_baseline, save_baseline


logger = logging.getLogger(__name__)


def run(
    settings: AppConfig,
    connection: sqlite3.Connection,
    notify: Callable[[dict[Path, FileDifference]], None],
) -> None:
    website_dir = settings.website_dir

    with scan_lock(settings.scan_lock_path):
        baseline = _load_or_create_baseline(website_dir, connection)

    logger.info(
        "Monitoring %s every %s seconds. Press Ctrl+C to stop.",
        website_dir, settings.scan_interval,
    )

    while True:
        try:
            with scan_lock(settings.scan_lock_path):
                scan = scan_directory(website_dir)
                incidents = settings.incident_rule.evaluate(scan, baseline)

                if not isinstance(incidents, dict) or any(
                    not isinstance(path, Path) or not isinstance(incident, FileDifference)
                    for path, incident in incidents.items()
                ):
                    raise TypeError("IncidentRule.evaluate must return path-to-incident results.")
        except Exception as exc:
            logger.error("Cannot evaluate integrity scan (%s).", type(exc).__name__)

            incidents = {
                website_dir: FileDifference(ChangeType.UNVERIFIABLE, error=f"Scan failed: {type(exc).__name__}: {exc}"),
            }

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
