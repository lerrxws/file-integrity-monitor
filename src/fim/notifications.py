from email.errors import HeaderParseError
from email.message import EmailMessage
from email.utils import formatdate
import logging
import smtplib
import ssl

from .config import SmtpConfig


ALERT_SUBJECT = "FIM: website file changed"

logger = logging.getLogger(__name__)


def send_notification(subject: str, message: str, settings: SmtpConfig) -> None:
    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = settings.sender
    email["To"] = settings.recipient
    email["Date"] = formatdate(usegmt=True)
    email.set_content(message)

    with smtplib.SMTP(settings.host, settings.port, timeout=settings.timeout) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(settings.username, settings.password)

        refused = smtp.send_message(email)

        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def report_change(path: str, change_type: str, settings: SmtpConfig) -> bool:
    message = f"{change_type.upper()}: {path!r}"
    logger.info(message)

    try:
        send_notification(ALERT_SUBJECT, message, settings)
    except (OSError, smtplib.SMTPException, HeaderParseError, KeyError, ValueError) as exc:
        logger.error(
            "Email notification failed (%s). Check SMTP settings and connection.",
            type(exc).__name__,
        )
        return False

    logger.info("Email notification accepted by SMTP server.")

    return True
