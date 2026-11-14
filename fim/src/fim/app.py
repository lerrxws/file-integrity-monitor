from collections.abc import Callable
import logging
from pathlib import Path
import sqlite3
import time

from .config import AppConfig
from .hashing import collect_hashes
from .monitor import ChangeType, FileDifference, scan_directory
from .policy import ChangeAssessment, ChangeDecision, ChangePolicy
from .storage import get_baseline, get_expected_hashes, save_approved_version, save_baseline


logger = logging.getLogger(__name__)


def run(
    settings: AppConfig,
    connection: sqlite3.Connection,
    notify: Callable[[dict[Path, FileDifference]], None],
    *,
    policy: ChangePolicy,
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

    expected = get_expected_hashes(connection)

    logger.info(
        "Monitoring %s every %s seconds. Press Ctrl+C to stop.",
        website_dir, settings.scan_interval,
    )

    while True:
        differences = scan_directory(website_dir, expected)
        incidents = _assess_changes(website_dir, connection, expected, differences, policy)
        notify(incidents)
        time.sleep(settings.scan_interval)


def _assess_changes(
    website_dir: Path,
    connection: sqlite3.Connection,
    expected: dict[str, str],
    differences: dict[Path, FileDifference],
    policy: ChangePolicy,
) -> dict[Path, FileDifference]:
    incidents = {}

    for path, difference in differences.items():
        if difference.change_type == ChangeType.UNVERIFIABLE:
            incidents[path] = difference
            continue

        try:
            assessment = policy.assess(path, difference)

            if not isinstance(assessment, ChangeAssessment):
                raise TypeError("Policy must return a ChangeAssessment.")
        except Exception as exc:
            logger.error("Cannot assess %r (%s); reporting incident.", str(path), type(exc).__name__)
            incidents[path] = difference
            continue

        if assessment.decision is not ChangeDecision.APPROVED:
            logger.debug("Incident: %r; %s", str(path), assessment.reason)
            incidents[path] = difference
            continue

        if difference.change_type != ChangeType.DELETED and difference.sha256 is None:
            logger.error("Cannot approve %r without its observed hash; reporting incident.", str(path))
            incidents[path] = difference
            continue

        relative_path = path.relative_to(website_dir).as_posix()

        try:
            save_approved_version(connection, relative_path, difference.sha256)
        except sqlite3.Error as exc:
            logger.error("Cannot record approval for %r (%s); reporting incident.", str(path), type(exc).__name__)
            incidents[path] = difference
            continue

        if difference.sha256 is None:
            expected.pop(relative_path, None)
        else:
            expected[relative_path] = difference.sha256

        logger.info(
            "Approved %s: %r; expected SHA-256=%s; %s",
            difference.change_type.value, str(path), difference.sha256, assessment.reason,
        )

    return incidents
