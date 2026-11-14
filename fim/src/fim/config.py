from dataclasses import dataclass, field
from email.errors import HeaderParseError
from email.headerregistry import Address
import json
import math
import os
from pathlib import Path


DEFAULT_SMTP_PORT = 587


@dataclass(frozen=True)
class NotificationConfig:
    group: str
    recipients: tuple[str, ...]


@dataclass(frozen=True)
class AppConfig:
    website_dir: Path
    database_path: Path
    log_file: Path
    scan_interval: float
    smtp_timeout: float
    notifications: NotificationConfig


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str = field(repr=False)
    sender: str
    timeout: float


def _positive_number(value: object, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be a finite positive number of seconds.")

    return float(value)


def _email_address(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an email address.")

    try:
        address = Address(addr_spec=value.strip())
    except (ValueError, HeaderParseError) as exc:
        raise ValueError(f"{field_name} must be a bare email address.") from exc

    if not address.username or not address.domain:
        raise ValueError(f"{field_name} must include a username and domain.")

    return Address(username=address.username, domain=address.domain.lower()).addr_spec


def _load_notifications(settings: object) -> NotificationConfig:
    if not isinstance(settings, dict):
        raise ValueError("notifications must contain a group and groups mapping.")

    group = settings.get("group")
    groups = settings.get("groups")

    if not isinstance(group, str) or not group.strip():
        raise ValueError("notifications.group must be a nonempty group name.")

    if not isinstance(groups, dict) or not groups:
        raise ValueError("notifications.groups must contain at least one group.")

    recipients_by_group = {}

    for name, addresses in groups.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Notification group names must be nonempty strings.")

        if not isinstance(addresses, list) or not addresses:
            raise ValueError(f"notifications.groups.{name} must be a nonempty email list.")

        recipients_by_group[name] = tuple(dict.fromkeys(
            _email_address(address, f"notifications.groups.{name}[{index}]")
            for index, address in enumerate(addresses)
        ))

    if group not in recipients_by_group:
        raise ValueError(f"Unknown notification group: {group!r}.")

    return NotificationConfig(group=group, recipients=recipients_by_group[group])


def load_config(path: Path, project_dir: Path) -> AppConfig:
    with path.open(encoding="utf-8") as file:
        settings = json.load(file)

    paths = {}

    for key in ("website_dir", "database_path", "log_file"):
        if not isinstance(settings[key], str) or not settings[key].strip():
            raise ValueError(f"{key} must be a nonempty path.")

        paths[key] = Path(os.path.abspath(project_dir / settings[key]))

    website_dir = paths["website_dir"]

    if website_dir.is_symlink() or not website_dir.is_dir():
        raise ValueError("website_dir must be an existing directory, not a symlink.")

    for key in ("database_path", "log_file"):
        if paths[key].resolve().is_relative_to(website_dir.resolve()):
            raise ValueError(f"{key} must be outside website_dir.")

    return AppConfig(
        **paths,
        scan_interval=_positive_number(settings["scan_interval"], "scan_interval"),
        smtp_timeout=_positive_number(settings["smtp_timeout"], "smtp_timeout"),
        notifications=_load_notifications(settings["notifications"]),
    )


def load_smtp_settings(timeout: float) -> SmtpConfig:
    required = ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM")
    missing = [name for name in required if not os.environ.get(name)]

    if missing:
        raise ValueError(f"Missing SMTP settings: {', '.join(missing)}")

    try:
        port = int(os.environ.get("SMTP_PORT", str(DEFAULT_SMTP_PORT)))
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be an integer between 1 and 65535.") from exc

    if not 1 <= port <= 65535:
        raise ValueError("SMTP_PORT must be between 1 and 65535.")

    return SmtpConfig(
        host=os.environ["SMTP_HOST"],
        port=port,
        username=os.environ["SMTP_USERNAME"],
        password=os.environ["SMTP_PASSWORD"],
        sender=os.environ["SMTP_FROM"],
        timeout=_positive_number(timeout, "smtp_timeout"),
    )
