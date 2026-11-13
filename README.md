# File Integrity Monitor

A File Integrity Monitoring system for detecting unauthorized changes to files on a web server.

## Initial scope

- Configuration file
- File integrity verification
- Baseline storage
- Logging
- Incident detection
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
