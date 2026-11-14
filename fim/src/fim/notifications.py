from email.errors import HeaderParseError
from email.message import EmailMessage
from email.utils import formatdate
import logging
from pathlib import Path
import smtplib
import ssl

from .config import NotificationConfig, SmtpConfig
from .incidents import ChangeType, FileDifference


ALERT_SUBJECT = "FIM: website file changed"

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, settings: NotificationConfig, smtp: SmtpConfig) -> None:
        self._recipients = settings.recipients
        self._smtp = smtp
        self._delivered: dict[Path, dict[str, FileDifference]] = {}

        logger.info("Alerts use group %r with %d recipients.", settings.group, len(self._recipients))

    def notify(self, differences: dict[Path, FileDifference]) -> None:
        unverifiable = [
            path for path, difference in differences.items()
            if difference.change_type == ChangeType.UNVERIFIABLE
        ]

        for path in self._delivered.keys() - differences.keys():
            if any(path.is_relative_to(parent) for parent in unverifiable):
                continue

            del self._delivered[path]
            logger.info("Recovered: %r", str(path))

        for path, difference in differences.items():
            delivered = self._delivered.get(path, {})
            pending = [
                recipient for recipient in self._recipients
                if delivered.get(recipient) != difference
            ]

            if difference.error and pending:
                logger.error("Cannot verify %r: %s", str(path), difference.error)

            for recipient in pending:
                if report_change(str(path), difference.change_type, recipient, self._smtp):
                    self._delivered.setdefault(path, {})[recipient] = difference


def send_notification(subject: str, message: str, recipient: str, settings: SmtpConfig) -> None:
    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = settings.sender
    email["To"] = recipient
    email["Date"] = formatdate(usegmt=True)
    email.set_content(message)

    with smtplib.SMTP(settings.host, settings.port, timeout=settings.timeout) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(settings.username, settings.password)

        refused = smtp.send_message(email, to_addrs=[recipient])

        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def report_change(path: str, change_type: str, recipient: str, settings: SmtpConfig) -> bool:
    message = f"{change_type.upper()}: {path!r}"
    logger.info("%s; recipient=%r", message, recipient)

    try:
        send_notification(ALERT_SUBJECT, message, recipient, settings)
    except (OSError, smtplib.SMTPException, HeaderParseError, KeyError, ValueError) as exc:
        logger.error(
            "Email notification to %r failed (%s). Check SMTP settings and connection.",
            recipient, type(exc).__name__,
        )
        return False

    logger.info("Email notification to %r accepted by SMTP server.", recipient)

    return True
