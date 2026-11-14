# File Integrity Monitor

Three components have separate source directories and Docker build contexts:

- **`fim/`** reads website files, compares SHA-256 hashes with a SQLite baseline,
  writes logs, and sends email alerts. It never changes the website.
- **`publisher/`** fetches the name day and generates `index.html` on startup and
  at local midnight. It has no baseline database or SMTP dependency.
- **`web/`** owns the public files and the Nginx image that serves them in Docker.

One root `compose.yaml` starts the components together.

## Setup

Requires Python 3.10 or newer. FIM needs an SMTP account supporting STARTTLS.
Run the following commands from the repository root.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r fim/requirements.txt
cp .env.example .env
chmod 600 .env
```

Fill in SMTP settings in the root `.env`. FIM loads this shared file and validates
its settings at startup. Existing environment variables take precedence.
Recipient addresses belong in FIM's notification groups, configured below.
The previous `SMTP_TO` variable is no longer used; move its address into a group.
Publisher uses only the Python standard library and does not read `.env` or
require SMTP credentials.

## Configuration

FIM uses `fim/config/config.json`:

```json
{
  "website_dir": "../web/public",
  "database_path": "data/fim.db",
  "log_file": "logs/fim.log",
  "scan_interval": 5,
  "smtp_timeout": 10,
  "notifications": {
    "group": "web_admin",
    "groups": {
      "web_admin": [
        "admin@example.com",
        "backup@example.com"
      ]
    }
  }
}
```

`notifications.group` selects the group that receives every integrity alert.
Add groups under `notifications.groups` and replace the example addresses with
your actual contacts. Each group must contain at least one bare email address.
Groups and addresses are validated at startup; duplicate addresses within a group
are removed. Restart FIM after changing the selection or addresses.

Each recipient gets an individual email. Delivery state is tracked per recipient,
so a failure for one address does not resend the same alert to successful recipients.
All selected recipients receive a new alert when the file content changes again.

The scanner returns file differences without handling email or recipients.
The notifier owns the selected group's delivery state, retries, and recovery;
the application loop assesses differences through a change policy before passing
incidents to it.

## Change policies

`fim/src/fim/policy.py` defines the authorization boundary:

- `ChangePolicy` is a `Protocol` with `assess(path, difference)`.
- `ChangeAssessment` is an immutable result containing `decision` and `reason`.
- `ChangeDecision` contains `APPROVED` and `INCIDENT`.
- `ReportAllChangesPolicy` is wired into the CLI and keeps every difference
  reportable because trusted approval evidence is not configured yet.

Policies classify observed paths, operations, and hashes. They do not send email
or write the database. The application records approved versions and logs the
approval reason; the notifier handles incident delivery and retries.

Approved versions are stored separately in SQLite's `approved_versions` table.
The original `baselines` rows stay unchanged. Only the approved path becomes a
new expected state, so a later rollback to the original content is detected.
Approved deletions also persist without losing the original baseline's initialized
status. Existing databases receive the additional table at startup.

Unverifiable paths always remain incidents. Policy failures or failure to store
an approval leave the previous expected state intact and keep the change reportable.
Publisher changes continue to alert with the default policy. `PublisherChangePolicy`
and `AuthorizedUserChangePolicy` will be added when their trusted evidence
mechanisms are defined; there is no automatic approval based on time or file ownership.

Publisher uses `publisher/config/config.json`:

```json
{
  "website_dir": "../web/public",
  "staging_dir": "../web/.staging",
  "template_path": "templates/index.html",
  "timezone": "Europe/Bratislava",
  "retry_interval": 5,
  "name_day_api": {
    "url": "https://nameday.abalin.net/api/V2/date",
    "country": "sk",
    "timeout": 5
  }
}
```

Paths are relative to each component's root, regardless of the current working
directory or config file location. Absolute paths also work. FIM stores its
database at `fim/data/fim.db` and logs at `fim/logs/fim.log`. Publisher reads
`publisher/templates/index.html`. Both programs receive immutable typed settings.
Intervals and timeouts are positive seconds. The database, logs, templates, and
staging directory stay outside `web/public`. Publisher creates its staging
directory when needed.

## Run without Docker

Generate the initial page before establishing the first trusted baseline:

```bash
.venv/bin/python publisher/src/main.py --once
```

Start FIM:

```bash
.venv/bin/python fim/src/main.py
```

Run Publisher in another terminal for startup updates, midnight updates, and retries:

```bash
.venv/bin/python publisher/src/main.py
```

Serve only the public directory in another terminal:

```bash
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory web/public
```

Open http://127.0.0.1:8000. Refresh the browser to see changed content.
Both programs accept `--config /path/to/settings.json` and stop with **Ctrl+C**.
An existing SQLite baseline is always retained.

## Monitoring behavior

- First startup saves hashes of the current public files. Initial content is
  assumed trusted. Later startups load the baseline plus approved versions and
  scan immediately against that expected state.
- Scans detect added, modified, deleted, and unverifiable files, including
  subdirectories. Renames appear as a deletion and an addition.
- Successful alerts are deduplicated in memory by path, change type, hash, and
  recipient. Returning to the expected state clears that path's state for everyone.
  Restarting can resend unresolved alerts. Failed recipients are retried on the
  next scan while other group members continue to receive their alerts.
- Logs append to the configured file and also appear in the terminal.
- FIM needs website read access and database/log write access. Publisher needs
  write access to the public and staging directories and read access to its template.
- Publisher changes still produce integrity alerts with the current policy.
  Publisher never modifies the baseline or the approved-version records.

Polling can miss changes reverted between scans. Files replaced while FIM is
offline cannot always be reconstructed later. Scanning and SMTP delivery take
time, so the configured interval is a pause between scans.

Existing baseline tables remain compatible. Relative keys such as `index.html`
and `style.css` stay the same after moving files into `web/public`. To establish
a new baseline, stop FIM, review the site, and deliberately move its database aside.

## Publisher behavior

Publisher uses the [Abalin Nameday API](https://nameday.abalin.net/docs/api).
The endpoint accepts `day` and `month` and returns the configured country under
`data`, for example `data.sk`. No API key or extra Python dependency is required.

A successful lookup and publication runs once per local date, then Publisher
sleeps until midnight in the configured timezone. API failures produce today's
date and a temporary-unavailable message. Publisher retries after `retry_interval`;
recovery restores the name. Repeated identical pages are not rewritten.
`--once` publishes one page and exits, including a valid fallback page on API failure.
A filesystem/template failure makes a one-shot run exit unsuccessfully.

Temporary files are written in `web/.staging`, then atomically moved into
`web/public/index.html`. These directories must share a filesystem. FIM and
Nginx see only `public/`, avoiding partial pages and temporary-file alerts.

Edit `publisher/templates/index.html`, retaining `$name_day`, `$current_date`, and
`$status_hidden`. API text is escaped before rendering. Use
`web/public/style.css` for styling. Direct edits to generated `index.html`
are replaced by the next publication. OS scheduling and API requests can still
delay publication, but SMTP and FIM scans no longer block it.

## Docker deployment

Requires Docker Engine and Compose supporting named-volume subpath mounts.
Configure `.env` for the monitor, then run:

```bash
docker compose up -d --build
```

The three long-running services use persistent storage:

- `publisher` has write access to the website volume and read-only config/template
  mounts. It receives no SMTP credentials or baseline volume.
- `monitor` mounts only the public subdirectory, read-only. Its database and log
  volumes remain writable.
- `web` serves the same public subdirectory through Nginx, read-only.

Each component has its own Dockerfile and build context. Build them separately:

```bash
docker build -t file-integrity-monitor:local ./fim
docker build -t file-integrity-publisher:local ./publisher
docker build -t file-integrity-web:local ./web
```

Both Python images run as non-root users. Secrets, local databases, logs, and
staging files are excluded from their build contexts. The web image includes
the public assets for Nginx and a seed tree at `/opt/website` with `public/` and
`.staging/` owned by UID/GID 10001.

Compose first runs `website-init` from the web image with `/bin/true`. Docker
copies the seed into an empty website volume; nonempty volumes remain untouched.
Publisher starts after initialization completes and mounts the full website
volume with copying disabled. Compose then waits for Publisher's first completed
page before starting FIM and Nginx. An API fallback page counts as ready. The
readiness marker is kept in a temporary filesystem and recreated after Publisher
restarts. Once running, FIM and Nginx continue if Publisher is stopped.

Only `monitor` receives `.env`, including SMTP credentials. Its public files are
mounted at `/app/web/public`, while its writable database and log volumes are at
`/app/fim/data` and `/app/fim/logs`. Publisher has read-only config and template
mounts and writes the shared website at `/app/web`. Nginx mounts only `public/`
at `/usr/share/nginx/html`, read-only.

Open http://127.0.0.1:8000. Set `WEB_BIND_ADDRESS` and `WEB_PORT` in `.env` to
change the published address and port. Set the address to `0.0.0.0` for access
from other machines.

```bash
docker compose logs -f monitor publisher
docker compose cp web/public/style.css publisher:/app/web/public/style.css
docker compose down
```

The copy command publishes a changed stylesheet; FIM detects it. Website, baseline,
and log volumes survive container recreation and `docker compose down`.
Rebuilding images does not overwrite an existing website volume. The volume keys
remain `website`, `baseline`, and `logs`. The three long-running services use
`restart: unless-stopped`; `website-init` exits after initialization. Both Python
programs handle SIGINT for clean shutdown.

### Upgrading the earlier flat website volume

The previous Docker layout stored `index.html` and `style.css` directly in the
website volume. Stop that deployment and build the new images first:

```bash
docker compose down
docker compose build
```

For an existing flat volume, move its files into `public/` before starting the
new services. This command refuses to overwrite files and leaves the baseline
volume untouched:

```bash
docker compose run --rm --no-deps -T publisher python - <<'PY'
from pathlib import Path

root = Path("/app/web")
public = root / "public"
public.mkdir(exist_ok=True)
files = [path for path in root.iterdir() if path.name not in {"public", ".staging"}]

if any((public / path.name).exists() for path in files):
    raise SystemExit("Refusing to overwrite existing public files.")

for path in files:
    path.rename(public / path.name)
PY

docker compose up -d
```

This migration is unnecessary for fresh Docker volumes. Local website files have
already moved to `web/public`. The existing local database and logs have moved to
`fim/data` and `fim/logs`; database contents and relative baseline keys are unchanged.

## Code layout

```text
compose.yaml                 # shared deployment
.env.example                 # root SMTP and web binding settings
fim/
  Dockerfile
  requirements.txt           # FIM dependencies
  config/config.json         # FIM settings
  data/                      # local SQLite baseline, ignored by Git
  logs/                      # local FIM logs, ignored by Git
  tests/                     # monitoring and notification group checks
  src/
    main.py                  # FIM entry point
    fim/
      __main__.py            # CLI, logging, resource lifecycle
      config.py              # FIM and SMTP settings
      app.py                 # scan loop and baseline initialization
      monitor.py             # file differences and ChangeType enum
      policy.py              # assessment contract and default incident policy
      hashing.py             # SHA-256 snapshots
      storage.py             # original baseline and approved expected versions
      notifications.py       # recipient delivery state, retries, and SMTP alerts
publisher/
  Dockerfile
  config/config.json         # Publisher settings
  templates/index.html       # source HTML
  src/
    main.py                  # Publisher entry point
    publisher/
      __main__.py            # independent CLI
      config.py              # publishing settings
      app.py                 # startup, midnight schedule, retries
      page.py                # API lookup and atomic page generation
web/
  Dockerfile                 # Nginx image and shared-volume seed
  public/                    # published and monitored files
  .staging/                  # temporary files, ignored by Git
```

Run the policy, storage, and notification integration checks with:

```bash
.venv/bin/python -m unittest discover -s fim/tests -v
```

These checks use temporary files and mocked SMTP; they send no real emails.
