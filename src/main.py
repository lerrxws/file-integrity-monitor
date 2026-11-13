import logging
from pathlib import Path
import smtplib

from dotenv import load_dotenv

from logger.setup import setup_logging
from monitoring.watcher import watch_directory
from notifications.email import send_notification


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
    watch_directory(project_dir / "web", on_change=handle_change)


if __name__ == "__main__":
    main()
