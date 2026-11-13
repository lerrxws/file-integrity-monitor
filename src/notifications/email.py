from email.message import EmailMessage
from email.utils import formatdate
import os
import smtplib
import ssl


def send_notification(subject: str, message: str) -> None:
    required = ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_TO")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Missing SMTP settings: {', '.join(missing)}")

    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be an integer between 1 and 65535.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("SMTP_PORT must be between 1 and 65535.")

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = os.environ["SMTP_FROM"]
    email["To"] = os.environ["SMTP_TO"]
    email["Date"] = formatdate(usegmt=True)
    email.set_content(message)

    with smtplib.SMTP(os.environ["SMTP_HOST"], port, timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        refused = smtp.send_message(email)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
