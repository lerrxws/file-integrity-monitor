from dataclasses import dataclass, field
from email.errors import HeaderParseError
from email.headerregistry import Address
import json
import math
import os
from pathlib import Path

from .incidents import HashMismatchIncidentRule, IncidentRule, PublisherAwareIncidentRule
from .incidents.publisher_aware import relative_file_path


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
    incident_rule: IncidentRule = field(default_factory=HashMismatchIncidentRule)
    scan_lock_path: Path | None = None


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


def _load_incident_rule(
    settings: object, project_dir: Path, website_dir: Path, lock_path: Path | None,
) -> IncidentRule:
    if not isinstance(settings, dict):
        raise ValueError("incident_rule must be an object.")

    rule_type = settings.get("type")

    if not isinstance(rule_type, str):
        raise ValueError("incident_rule.type must be a rule name.")

    if rule_type in {"any_change", "hash_mismatch"}:
        if set(settings) != {"type"}:
            raise ValueError("Baseline incident rules must contain only a type field.")

        return HashMismatchIncidentRule()

    if rule_type != "publisher_aware":
        raise ValueError(f"Unknown incident_rule.type: {rule_type!r}.")

    if set(settings) != {"type", "paths", "manifest_path"}:
        raise ValueError("publisher_aware requires only paths and manifest_path.")

    paths = settings["paths"]

    if not isinstance(paths, list) or not paths:
        raise ValueError("publisher_aware.paths must be a nonempty list.")

    value = settings["manifest_path"]

    if not isinstance(value, str) or not value.strip():
        raise ValueError("publisher_aware.manifest_path must be a nonempty path.")

    manifest = Path(os.path.abspath(project_dir / value))

    if manifest.resolve().is_relative_to(website_dir.resolve()) or manifest.suffix == ".lock":
        raise ValueError("Publisher manifest must be outside website_dir and differ from its lock.")

    if lock_path is None or lock_path.resolve() != manifest.with_suffix(".lock").resolve():
        raise ValueError("publisher_aware requires scan_lock_path to match the manifest's .lock file.")

    return PublisherAwareIncidentRule(
        manifest, tuple(dict.fromkeys(relative_file_path(path) for path in paths)),
    )


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

    lock_path = None

    if settings.get("scan_lock_path") is not None:
        value = settings["scan_lock_path"]

        if not isinstance(value, str) or not value.strip():
            raise ValueError("scan_lock_path must be a nonempty path or null.")

        lock_path = Path(os.path.abspath(project_dir / value))

        if lock_path.resolve().is_relative_to(website_dir.resolve()):
            raise ValueError("scan_lock_path must be outside website_dir.")

        if lock_path.resolve() in {paths["database_path"].resolve(), paths["log_file"].resolve()}:
            raise ValueError("Scan lock must not overlap the database or log file.")

    return AppConfig(
        **paths,
        scan_interval=_positive_number(settings["scan_interval"], "scan_interval"),
        smtp_timeout=_positive_number(settings["smtp_timeout"], "smtp_timeout"),
        notifications=_load_notifications(settings["notifications"]),
        incident_rule=_load_incident_rule(
            settings.get("incident_rule", {"type": "hash_mismatch"}), project_dir, website_dir, lock_path,
        ),
        scan_lock_path=lock_path,
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
