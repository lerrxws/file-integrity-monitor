import logging
from pathlib import Path
import smtplib

from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

from db.setup import initialize_database
from logger.setup import setup_logging
from monitoring.baseline import create_baseline
from monitoring.watcher import watch_directory
from notifications.email import send_notification
from repositories.baseline import baseline_exists


logger = logging.getLogger(__name__)


def handle_change(message: str) -> None:
    try:
        send_notification("FIM: website file changed", message)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        logger.error("Email notification failed (%s). Check SMTP settings and connection.", type(exc).__name__)
    else:
        logger.info("Email notification accepted by SMTP server.")


def main() -> None:
    project_dir = Path(__file__).resolve().parent.parent
    load_dotenv(project_dir / ".env")
    try:
        setup_logging(project_dir / "logs" / "fim.log")
    except OSError as exc:
        raise SystemExit(f"Cannot initialize logging: {exc}") from exc

    website_dir = project_dir / "web"
    database_path = project_dir / "data" / "fim.db"
    try:
        initialize_database(database_path)
        if baseline_exists(database_path):
            logger.info("Using existing baseline.")
        else:
            file_count = create_baseline(website_dir, database_path)
            logger.info("Created baseline for %d files.", file_count)
    except (OSError, ValueError, SQLAlchemyError) as exc:
        logger.error("Cannot initialize baseline: %s", exc)
        raise SystemExit("Cannot initialize baseline. Check the log for details.") from exc

    watch_directory(website_dir, on_change=handle_change)


if __name__ == "__main__":
    main()
