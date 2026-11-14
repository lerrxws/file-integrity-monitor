from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class NameDayApiConfig:
    url: str
    country: str
    timeout: float


@dataclass(frozen=True)
class PublisherConfig:
    website_dir: Path
    staging_dir: Path
    template_path: Path
    timezone: ZoneInfo
    retry_interval: float
    name_day_api: NameDayApiConfig


def _positive_number(value: object, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be a finite positive number of seconds.")

    return float(value)


def load_config(path: Path, project_dir: Path) -> PublisherConfig:
    with path.open(encoding="utf-8") as file:
        settings = json.load(file)

    paths = {}

    for key in ("website_dir", "staging_dir", "template_path"):
        if not isinstance(settings[key], str) or not settings[key].strip():
            raise ValueError(f"{key} must be a nonempty path.")

        paths[key] = Path(os.path.abspath(project_dir / settings[key]))

    website_dir = paths["website_dir"]

    if website_dir.is_symlink() or not website_dir.is_dir():
        raise ValueError("website_dir must be an existing directory, not a symlink.")

    for key in ("staging_dir", "template_path"):
        if paths[key].resolve().is_relative_to(website_dir.resolve()):
            raise ValueError(f"{key} must be outside website_dir.")

    if not paths["template_path"].is_file():
        raise ValueError("template_path must point to an existing HTML template.")

    staging_dir = paths["staging_dir"]

    if staging_dir.is_symlink():
        raise ValueError("staging_dir must be a directory, not a symlink.")

    staging_dir.mkdir(parents=True, exist_ok=True)

    if staging_dir.stat().st_dev != website_dir.stat().st_dev:
        raise ValueError("staging_dir and website_dir must share a filesystem for atomic publishing.")

    api = settings["name_day_api"]
    url = api["url"]

    if not isinstance(url, str) or not url.strip():
        raise ValueError("name_day_api.url must be a nonempty HTTP(S) URL.")

    parsed_url = urlsplit(url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc or parsed_url.fragment:
        raise ValueError("name_day_api.url must be an HTTP(S) URL without a fragment.")

    country = api["country"]

    if (
        not isinstance(country, str)
        or len(country) != 2
        or not country.isascii()
        or not country.isalpha()
    ):
        raise ValueError("name_day_api.country must be a two-letter country code.")

    return PublisherConfig(
        **paths,
        timezone=ZoneInfo(settings["timezone"]),
        retry_interval=_positive_number(settings["retry_interval"], "retry_interval"),
        name_day_api=NameDayApiConfig(
            url=url,
            country=country.lower(),
            timeout=_positive_number(api["timeout"], "name_day_api.timeout"),
        ),
    )
