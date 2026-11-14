from collections.abc import Callable
from datetime import datetime
import logging
import sqlite3
import time

from .config import AppConfig
from .daily_update import fetch_name_day, seconds_until_midnight, update_index
from .hashing import collect_hashes
from .monitor import ChangeType, scan_directory
from .storage import get_baseline, save_baseline


logger = logging.getLogger(__name__)


def run(
    settings: AppConfig,
    connection: sqlite3.Connection,
    report: Callable[[str, ChangeType], bool],
) -> None:
    website_dir = settings.website_dir
    baseline = get_baseline(connection)

    if baseline:
        logger.info("Loaded baseline for %d files.", len(baseline))

    reported: dict[str, tuple[ChangeType, str | None]] = {}
    last_update = None

    logger.info(
        "Monitoring %s every %s seconds. Press Ctrl+C to stop.",
        website_dir, settings.scan_interval,
    )

    if baseline:
        scan_directory(website_dir, baseline, reported, report)

    while True:
        today = datetime.now(settings.timezone).date()

        if today != last_update:
            try:
                name_day = fetch_name_day(today, settings.name_day_api)
                changed = update_index(website_dir, today, name_day, settings.template_path)
            except (OSError, ValueError, KeyError) as exc:
                logger.error("Cannot update index.html: %s", exc)
            else:
                last_update = today

                if changed:
                    logger.info("Updated index.html for %s.", today)

        if not baseline:
            baseline, errors = collect_hashes(website_dir)

            if errors:
                raise ValueError(f"Cannot create a baseline: {errors}")

            save_baseline(connection, baseline)
            logger.info("Created baseline for %d files. Initial content is assumed trusted.", len(baseline))

        scan_directory(website_dir, baseline, reported, report)

        now = datetime.now(settings.timezone)
        time.sleep(min(settings.scan_interval, seconds_until_midnight(now)))
