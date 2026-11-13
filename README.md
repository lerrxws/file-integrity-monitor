# File Integrity Monitor

A File Integrity Monitoring system for detecting unauthorized changes to files on a web server.

## Initial scope

- Configuration file
- File integrity verification
- Baseline storage
- Logging
- Change detection
- Alerting
- Daily update of `index.html`

## Run the website

Run from the project root. Create the virtual environment once if needed:

```bash
python3 -m venv .venv
```

Start the local server:

```bash
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory web
```

Open http://127.0.0.1:8000 in your browser. Stop the server with **Ctrl+C**.

## Update the website

Edit the name and date in `web/index.html`:

```html
<h1>Name day of <span id="name-day">Stanislav</span></h1>
<p id="current-date">13 November 2026</p>
```

Keep the IDs unchanged. Edit `web/style.css` to change the appearance.
Save your changes and refresh the browser; no server restart is needed.
Date and name-day updates are manual for now.

## Watch for file changes

In another terminal, run from the project root:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/main.py
```

Edit and save a file in `web/` to see a message. The watcher prints file creation,
modification, deletion, and move events, including files in subdirectories.
One save may produce several events. Stop the watcher with **Ctrl+C**.

Startup, file events, and shutdown are logged to the terminal and `logs/fim.log`.
Each entry includes the timestamp, timezone offset, level, and logger name.
New entries are appended to the log file across runs.

## Baseline

At startup, the app initializes `data/fim.db`. If no baseline records exist,
it saves the paths and SHA-256 hashes of files in `web/`. The first startup
assumes those files are trusted. Later startups preserve the existing baseline.
Database or hashing errors stop startup. Created and modified files are compared
with the saved hashes: matching content sends no email; added or changed files
trigger alerts. Deletions alert only for baseline paths. Moves check the old
path as a deletion and compare the destination as an added or modified file;
this can produce two alerts. Only paths inside `web/` are checked. The baseline
stays unchanged.

## Email notifications

Use an SMTP server supporting STARTTLS, normally on port 587.
Copy `.env.example` to `.env`, fill in your settings, and run `chmod 600 .env`.
The app loads `.env` automatically. The standalone sender test below loads it
into your shell explicitly. `.env` is ignored by Git.

To load the settings and send a test email:

```bash
set -a
source .env
set +a
PYTHONPATH=src .venv/bin/python -c "from notifications.email import send_notification; send_notification('FIM test', 'This is a test notification.')"
```

The app loads `.env` automatically at startup. Run `.venv/bin/python src/main.py`,
then change a file's content in `web/` to receive an email with the change type
and file path.
One save may produce multiple emails. Delivery failures are logged without
stopping the watcher.

## Code layout

`main.py` loads settings, configures logging, and manages the database engine.
`app.py` coordinates baseline setup, comparison, and alerts.
`watching/` detects filesystem events; `integrity/` collects and compares hashes.
`notifications/alerts.py` formats and logs alerts and handles delivery failures;
`notifications/email.py` sends email. `repositories/` handles database queries,
`db/` defines the database, `events/` holds file event data, and `logger/` configures logging.
