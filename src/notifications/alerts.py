import logging
import smtplib

from events.file_change import FileChange
from notifications.email import send_notification


logger = logging.getLogger(__name__)


def report_change(change: FileChange, change_type: str) -> None:
    message = f"{change_type.upper()}: {change.src_path!r}"
    if change.dest_path is not None:
        message += f" -> {change.dest_path!r}"
    logger.info(message)
    _notify(message)


def _notify(message: str) -> None:
    try:
        send_notification("FIM: website file changed", message)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        logger.error("Email notification failed (%s). Check SMTP settings and connection.", type(exc).__name__)
    else:
        logger.info("Email notification accepted by SMTP server.")
