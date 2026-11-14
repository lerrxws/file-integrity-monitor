from datetime import date, datetime, time, timedelta
from html import escape
import json
from pathlib import Path
import stat
from string import Template
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import NameDayApiConfig


HTTP_USER_AGENT = "WebsitePublisher/1.0"
INDEX_FILENAME = "index.html"
PAGE_FILE_MODE = 0o644


def fetch_name_day(today: date, settings: NameDayApiConfig) -> str:
    query = urlencode({"day": today.day, "month": today.month})
    separator = "&" if "?" in settings.url else "?"
    request = Request(
        f"{settings.url}{separator}{query}",
        headers={"User-Agent": HTTP_USER_AGENT, "Accept": "application/json"},
    )

    with urlopen(request, timeout=settings.timeout) as response:
        result = json.load(response)

    if not isinstance(result, dict) or result.get("success") is not True:
        raise ValueError("The name-day API returned an unsuccessful response.")

    data = result.get("data")

    if not isinstance(data, dict) or not isinstance(data.get(settings.country), str):
        raise ValueError(f"The name-day API response is missing the name for {settings.country!r}.")

    return data[settings.country].strip() or "No name day"


def update_index(
    website_dir: Path,
    today: date,
    name_day: str | None,
    template_path: Path,
    staging_dir: Path,
) -> bool:
    if not stat.S_ISDIR(website_dir.lstat().st_mode):
        raise ValueError("The website path must be a directory, not a symlink.")

    path = website_dir / INDEX_FILENAME

    if path.is_symlink():
        raise ValueError("Cannot update a symlinked index.html.")

    content = Template(template_path.read_text(encoding="utf-8")).substitute(
        name_day=escape(name_day) if name_day is not None else "—",
        current_date=today.isoformat(),
        status_hidden="hidden" if name_day is not None else "",
    )

    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False

    if staging_dir.resolve().is_relative_to(website_dir.resolve()):
        raise ValueError("staging_dir must be outside website_dir.")

    temporary = NamedTemporaryFile(mode="w", encoding="utf-8", dir=staging_dir, delete=False)
    temporary_path = Path(temporary.name)

    try:
        with temporary:
            temporary.write(content)

        temporary_path.chmod(PAGE_FILE_MODE)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return True


def seconds_until_midnight(now: datetime) -> float:
    midnight = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=now.tzinfo)
    return midnight.timestamp() - now.timestamp()
