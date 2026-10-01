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

## Running the application

Make sure Go 1.26.5 or newer is installed:

```bash
go version
```

From the repository root, download the dependencies and run the application:

```bash
cd src
go mod download
go run ./cmd/fim
```

On the first run, the application creates the SQLite database and stores the
current hash of `web/index.html` as the baseline:

```text
Baseline created
```

On subsequent runs, it compares the current file with the stored baseline and
prints one of the following messages:

```text
File integrity OK
File modified
```
