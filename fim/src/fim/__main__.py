import argparse
import logging
from pathlib import Path
import sqlite3

from dotenv import load_dotenv

from .app import run
from .config import load_config, load_smtp_settings
from .notifications import Notifier
from .policy import ReportAllChangesPolicy
from .storage import initialize_database


PROJECT_DIR = Path(__file__).resolve().parents[2]
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S%z"

logger = logging.getLogger(__name__)


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8", errors="backslashreplace"),
        ],
        force=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor website file integrity.")
    parser.add_argument("--config", type=Path, default=PROJECT_DIR / "config" / "config.json")
    args = parser.parse_args()
    connection = None

    try:
        settings = load_config(args.config, PROJECT_DIR)
        setup_logging(settings.log_file)

        load_dotenv(PROJECT_DIR.parent / ".env")
        smtp = load_smtp_settings(settings.smtp_timeout)
        notifier = Notifier(settings.notifications, smtp)

        connection = initialize_database(settings.database_path)

        run(settings, connection, notifier.notify, policy=ReportAllChangesPolicy())

    except KeyboardInterrupt:
        logger.info("Stopped monitoring.")

    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        logger.error("Cannot run FIM: %s", exc)
        raise SystemExit(1) from exc

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
