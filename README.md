# File Integrity Monitor

Checks website files against trusted SHA-256 hashes in SQLite and emails the
configured recipients when files change. `index.html` must match today's approved
page in `Europe/Bratislava`. Website updates are manual.

## Setup

Requires Python 3.10+. Run from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r fim/requirements.txt
cp .env.example .env
chmod 600 .env
```

Set SMTP credentials in `.env` and recipient addresses in
`fim/config/config.json`. Configuration paths are relative to `fim/`.

## Prepare hashes

`web/namedays/2026/namedays.json` contains all 366 dates from the
[Slovak official calendar](https://www.culture.gov.sk/storage/2020/03/Oficialne-kalendarium_2025.pdf).
Names use `MM-DD` keys, comma-separated names, and `No name day` for unassigned dates.

```bash
.venv/bin/python tools/seed_expected.py --calendar web/namedays/2026/namedays.json --year 2026
```

The script stores date-specific page hashes from `web/templates/index.html` and
approved static file hashes in SQLite. Repeat for additional years. When changing
the trusted template or static files, stop FIM, back up the database, and prepare
a fresh one.

For manual page updates, copy the template to `web/public/index.html` and replace
`$name_day` with the HTML-escaped name and `$current_date` with `YYYY-MM-DD`.
Preserve UTF-8 encoding and all other bytes. Wrong dates, missing expectations,
and unexpected file changes trigger alerts; yesterday's page alerts after midnight.

## Run

Start the monitor and web server in separate terminals:

```bash
.venv/bin/python -m fim
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory web/public
```

Open http://127.0.0.1:8000. Logs are in `fim/logs/fim.log`.
