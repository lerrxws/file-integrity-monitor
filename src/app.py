from functools import partial
import logging
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from events.file_change import FileChange
from integrity.baseline import collect_baseline
from integrity.hashing import compare_file
from notifications.alerts import report_change
from repositories.baseline import baseline_exists, get_baseline_hash, save_baseline
from watching.watcher import watch_directory


logger = logging.getLogger(__name__)


def run(website_dir: Path, engine: Engine) -> None:
    try:
        _prepare_baseline(website_dir, engine)
    except (OSError, ValueError, SQLAlchemyError) as exc:
        logger.error("Cannot initialize baseline: %s", exc)
        raise SystemExit("Cannot initialize baseline. Check the log for details.") from exc

    on_change = partial(handle_change, website_dir=website_dir, engine=engine)
    watch_directory(website_dir, on_change=on_change)


def _prepare_baseline(website_dir: Path, engine: Engine) -> None:
    database_path = engine.url.database
    if database_path and Path(database_path).resolve().is_relative_to(website_dir.resolve()):
        raise ValueError("The database must be outside the website directory.")

    if baseline_exists(engine):
        logger.info("Using existing baseline.")
        return

    hashes = collect_baseline(website_dir)
    save_baseline(engine, hashes)
    logger.info("Created baseline for %d files.", len(hashes))


def handle_change(change: FileChange, website_dir: Path, engine: Engine) -> None:
    change_type = change.event_type
    if change.event_type in {"created", "modified"}:
        try:
            path = Path(change.src_path)
            relative_path = path.resolve().relative_to(website_dir.resolve()).as_posix()
            baseline_hash = get_baseline_hash(engine, relative_path)
            difference = compare_file(path, baseline_hash)
        except (OSError, ValueError, SQLAlchemyError) as exc:
            logger.error("Cannot check integrity for %r (%s).", change.src_path, type(exc).__name__)
            return

        if difference is None:
            logger.info("Unchanged from baseline: %r", change.src_path)
            return
        change_type = difference

    report_change(change, change_type)
