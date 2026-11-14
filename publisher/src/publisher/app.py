from datetime import date, datetime
import logging
from pathlib import Path
import time

from .config import PublisherConfig
from .page import fetch_name_day, seconds_until_midnight, update_index


logger = logging.getLogger(__name__)


def publish(settings: PublisherConfig, today: date) -> bool:
    try:
        name_day = fetch_name_day(today, settings.name_day_api)
    except (OSError, ValueError) as exc:
        logger.error("Cannot fetch name-day information: %s", exc)
        name_day = None

    changed = update_index(
        settings.website_dir, today, name_day, settings.template_path, settings.staging_dir,
        manifest_path=settings.manifest_path,
    )

    if changed:
        logger.info("Published index.html for %s.", today)

    return name_day is not None


def run(
    settings: PublisherConfig,
    *,
    once: bool = False,
    ready_file: Path | None = None,
) -> None:
    if ready_file is not None:
        ready_file.unlink(missing_ok=True)

    last_success = None

    while True:
        today = datetime.now(settings.timezone).date()

        if today != last_success:
            try:
                if publish(settings, today):
                    last_success = today
            except (OSError, ValueError, KeyError) as exc:
                logger.error("Cannot publish index.html: %s", exc)

                if once:
                    raise
            else:
                if ready_file is not None:
                    ready_file.touch()

            if once:
                return

        now = datetime.now(settings.timezone)

        if now.date() != today:
            continue

        delay = seconds_until_midnight(now)

        if last_success != today:
            delay = min(settings.retry_interval, delay)

        time.sleep(delay)
