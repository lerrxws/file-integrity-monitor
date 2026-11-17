"""Prepare trusted hashes from a reviewed local calendar without publishing pages."""

import argparse
from calendar import monthrange
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import sqlite3
from string import Template
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1] / "fim"
sys.path.insert(0, str(PROJECT_DIR.parent))

from fim.hashing import collect_hashes
from fim.storage import seed_database


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    values = {}
    for key, value in pairs:
        if key in values:
            raise ValueError(f"Duplicate calendar key: {key!r}.")
        values[key] = value
    return values


def load_calendar(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as file:
        values = json.load(file, object_pairs_hook=_unique_keys)
    if not isinstance(values, dict) or not values:
        raise ValueError("Calendar must be a nonempty object mapping MM-DD dates to name strings.")
    names = {}
    for key, name in values.items():
        if re.fullmatch(r"[0-9]{2}-[0-9]{2}", key) is None:
            raise ValueError(f"Invalid calendar date: {key!r}; use MM-DD.")
        date.fromisoformat("2000-" + key)
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Calendar name for {key!r} must be a nonempty string.")
        names[key] = name.strip()
    return names


def render_page(template: str, today: date, name: str) -> bytes:
    placeholders = {
        match.group("named") or match.group("braced")
        for match in Template.pattern.finditer(template)
    }
    if not {"name_day", "current_date"}.issubset(placeholders):
        raise ValueError("Template must contain $name_day and $current_date placeholders.")
    return Template(template).substitute(
        name_day=escape(name), current_date=today.isoformat(),
    ).encode("utf-8")


def seed(config_path: Path, calendar_path: Path, year: int) -> int:
    if not 1 <= year <= 9999:
        raise ValueError("Year must be between 1 and 9999.")
    with config_path.open(encoding="utf-8") as file:
        settings = json.load(file)
    paths = {}
    for key in ("website_dir", "database_path", "template_path"):
        value = settings[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a nonempty path.")
        paths[key] = (PROJECT_DIR / value).absolute()
    website = paths["website_dir"]
    database = paths["database_path"]
    template_path = paths["template_path"]
    if website.is_symlink() or not website.is_dir():
        raise ValueError("website_dir must be an existing directory, not a symlink.")
    if database.resolve().is_relative_to(website.resolve()):
        raise ValueError("database_path must be outside website_dir.")
    if database.is_symlink():
        raise ValueError("database_path must not be a symlink.")
    for source in (calendar_path, template_path):
        if database.resolve() == source.resolve() or (database.exists() and database.samefile(source)):
            raise ValueError("database_path must not replace the calendar or template.")
    if template_path.resolve().is_relative_to(website.resolve()):
        raise ValueError("template_path must be outside website_dir.")

    names = load_calendar(calendar_path)
    template = template_path.read_text(encoding="utf-8")
    pages = {}
    for month in range(1, 13):
        for day in range(1, monthrange(year, month)[1] + 1):
            today = date(year, month, day)
            key = today.strftime("%m-%d")
            if key not in names:
                raise ValueError(f"Calendar is missing {key} for year {year}.")
            pages[today] = sha256(render_page(template, today, names[key])).hexdigest()

    static_hashes, errors = collect_hashes(website)
    static_hashes.pop("index.html", None)
    if errors:
        raise ValueError(f"Cannot prepare static expectations: {errors}")
    seed_database(database, static_hashes, pages)
    return len(pages)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PROJECT_DIR / "config/config.json")
    parser.add_argument("--calendar", type=Path, required=True, help="Reviewed JSON mapping MM-DD to name strings.")
    parser.add_argument("--year", type=int, required=True, help="Prepare every date in this year.")
    args = parser.parse_args()
    try:
        count = seed(args.config, args.calendar, args.year)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        parser.exit(1, f"Cannot prepare expected hashes: {exc}\n")
    print(f"Prepared {count} date-specific hashes for {args.year}. Website files were not changed.")


if __name__ == "__main__":
    main()
