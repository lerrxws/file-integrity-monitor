# File Integrity Monitor

A small Python program that monitors website files against SHA-256 hashes stored
in SQLite. It reads configuration at startup, writes a log file, and sends email
alerts. It also generates today's date and Slovak name day in `web/index.html`.

## Setup

Requires Python 3.10 or newer and an SMTP account supporting STARTTLS.

Run from the project root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

Fill in the SMTP settings in `.env`. They are validated once at startup.
The file is ignored by Git. Existing environment variables take precedence.

Edit `config/config.json` to configure the monitor:

```json
{
  "website_dir": "web",
  "database_path": "data/fim.db",
  "log_file": "logs/fim.log",
  "template_path": "templates/index.html",
  "scan_interval": 5,
  "timezone": "Europe/Bratislava",
  "name_day_api": {
    "url": "https://nameday.abalin.net/api/V2/date",
    "country": "sk",
    "timeout": 5
  },
  "smtp_timeout": 10
}
```

Paths in this file are relative to the project root; absolute paths also work.
The database, log, and source template must be outside the monitored directory.
The scan interval and network timeouts must be positive numbers of seconds.
SMTP connection settings and credentials stay in `.env`; `SMTP_PORT` defaults
to 587 when omitted. JSON settings and environment values are validated once
and passed to application code as immutable typed configuration objects.

## Run

Start the monitor:

```bash
.venv/bin/python src/main.py
```

Use `--config /path/to/settings.json` to select another configuration file.
Stop with **Ctrl+C**.

Serve the website in another terminal:

```bash
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory web
```

Open http://127.0.0.1:8000. Refresh the browser to see updated content.
On a web server, configure its document root to use the monitored directory.
The monitor needs permission to read website files, replace `index.html`, and
write its database and log.

## Monitoring behavior

- On the first run, the program tries to generate `index.html`, then saves the
  website's hashes as the baseline. If the name-day API is unavailable, it uses
  the existing website files. Initial files are assumed trusted.
- Later runs load the existing baseline and check files immediately.
  The baseline is never automatically overwritten.
- Every scan detects added, modified, and deleted files, including subdirectories.
  Renaming a file appears as a deletion and an addition.
- Unreadable files, symlinks, and special files produce an `unverifiable` alert.
  Other readable files are still checked. Temporary errors are retried.
- Successful alerts are deduplicated in memory using the path, change type,
  and hash. A new hash triggers another alert. Returning to the baseline clears
  that file's alert state. Restarting can resend unresolved alerts.
- Failed emails are logged and retried on the next scan.
- Logs go to the terminal and the configured file, including timestamps and
  timezone offsets. The file is appended across runs.

Polling can miss changes that are reverted between scans. Scanning and SMTP
delivery take time, so the interval is a pause between scans, not a strict
detection deadline.

Existing databases from the earlier SQLAlchemy implementation remain compatible.
Old notification records are retained but ignored. To establish a new trusted
baseline, stop the monitor, review the website, and move the old database aside.

## Daily page update

The program owns `index.html`: it fetches the Slovak name day from the
[Abalin Nameday API](https://nameday.abalin.net/docs/api) and generates the page
on startup and at local midnight while running. The API URL, country code, and
timeout come from configuration. The endpoint must accept `day` and `month`
parameters and return the Abalin response format. The configured country selects
the result from `data`, for example `data.sk`. Existing URL query parameters are
preserved. No API key or extra Python package is required.

A successful update is performed once per local date. The default API timeout
is five seconds. If the API fails or returns invalid data, the error is logged, the
existing page stays unchanged, and the next scan retries. File monitoring
continues during an API outage. There is no bundled calendar or offline fallback.

The program wakes for midnight even when the scan interval would otherwise
extend past it. Operating-system delays, scans, email delivery, or API requests
can delay the update. An interrupted process catches up when restarted.

Edit `templates/index.html` to change the generated HTML, retaining the
`$name_day` and `$current_date` placeholders. API text is escaped before rendering.
Use `web/style.css` for appearance. Direct edits to the generated `web/index.html`
are replaced by the next generated page. An empty name displays "No name day".

Daily updates are checked against the fixed baseline and can produce
`modified` alerts. They do not automatically approve any website changes.

## Code layout

The application uses one Python package with relative imports and modules grouped
by responsibility. The existing launch command uses a small compatibility wrapper:

```text
config/config.json       # deployment settings
templates/index.html     # source HTML template
src/
  main.py                # launch wrapper
  fim/
    __init__.py
    __main__.py          # CLI, logging, dependency wiring, cleanup
    config.py            # typed configuration and startup validation
    app.py               # polling loop and daily update coordination
    monitor.py           # comparisons, ChangeType enum, alert suppression
    hashing.py           # SHA-256 hashing and file collection
    storage.py           # SQLite baseline storage
    notifications.py     # SMTP delivery and alert logging
    daily_update.py      # API lookup, template rendering, midnight timing
```

Deployment choices belong in configuration. The four integrity change types use
`ChangeType`; fixed implementation values such as the hash buffer size use local
named constants. SQL schema names and HTTP protocol fields stay with their code.
The source layout keeps the original project-relative database and log locations.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests use temporary files and databases. Name-day API requests and SMTP delivery
are mocked; tests need no internet connection and send no real emails.
