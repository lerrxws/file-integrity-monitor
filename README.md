# File Integrity Monitor

A small File Integrity Monitoring (FIM) application written in Go. It creates
a trusted SHA-256 baseline for a configured file, watches the file for changes,
and reports integrity incidents through structured logs and alerts.

## Current scope

- YAML configuration
- SHA-256 file hashing
- Baseline persistence
- Continuous file watching
- Integrity incident detection
- Structured console and file logging
- Console alerts
- Graceful shutdown

## How it works

1. The application loads and validates `config/config.yaml`.
2. It creates the configured data directory when it does not exist.
3. It opens the database and initializes the baseline storage.
4. If no baseline exists for the monitored file, the current SHA-256 hash is
   stored as the initial trusted baseline.
5. The current file hash is compared with the stored baseline.
6. The application starts watching the file for write events.
7. After every write event, the hash is calculated again:
   - matching hashes produce a `file integrity OK` log entry;
   - different hashes create an integrity incident and send a console alert.
8. The stored baseline is not changed automatically after an incident.
9. `Ctrl+C` or `SIGTERM` stops the watcher and closes the application cleanly.

The main runtime flow is:

```text
configuration
    ↓
baseline lookup or creation
    ↓
initial integrity check
    ↓
file watcher
    ↓
hash comparison
    ├── unchanged → integrity OK
    └── modified  → incident → alert
```

## Project structure

```text
file-integrity-monitor/
├── cmd/
│   └── fim/
│       └── main.go
├── config/
│   └── config.yaml
├── internal/
│   ├── alert/
│   │   └── console.go
│   ├── baseline/
│   │   └── repository.go
│   ├── config/
│   │   └── config.go
│   ├── filesystem/
│   │   ├── hasher.go
│   │   └── watcher.go
│   ├── logging/
│   │   └── logging.go
│   └── monitor/
│       ├── model.go
│       ├── ports.go
│       └── service.go
├── web/
│   └── index.html
├── go.mod
└── README.md
```

Package responsibilities:

- `cmd/fim` is the composition root. It initializes resources, connects the
  implementations to the monitor, and handles process signals.
- `internal/monitor` contains the core FIM workflow, models, and interfaces.
- `internal/filesystem` provides SHA-256 hashing and filesystem watching.
- `internal/baseline` persists and retrieves trusted file hashes.
- `internal/alert` sends integrity alerts.
- `internal/config` loads and validates YAML configuration.
- `internal/logging` creates the structured console and file logger.

The core `monitor` package depends only on its own interfaces. Filesystem,
baseline, and alert implementations are connected in `cmd/fim/main.go`.

## Configuration

The default configuration is located at `config/config.yaml`:

```yaml
monitor:
  file: "./web/index.html"

storage:
  data_dir: "./data"

database:
  driver: "sqlite"
  path: "./data/fim.db"

logging:
  path: "./data/fim.log"

alert:
  type: "console"
```

All paths are resolved relative to the directory from which the application is
started. Run the application from the repository root when using the default
configuration.

## Running the application

Go 1.26.5 or newer is required:

```bash
go version
```

Download the dependencies and start the monitor from the repository root:

```bash
go mod download
go run ./cmd/fim
```

To use a different configuration file:

```bash
go run ./cmd/fim -config ./path/to/config.yaml
```

Typical output:

```text
level=INFO msg="baseline created" path=./web/index.html
level=INFO msg="file integrity OK" path=./web/index.html
level=INFO msg="watching file" path=./web/index.html
```

When the monitored file changes:

```text
level=WARN msg="integrity incident detected" path=./web/index.html
level=WARN msg="alert sent" message="File integrity violation detected: ./web/index.html"
```

Stop the monitor with `Ctrl+C`.

## Runtime data

The application creates runtime files in the configured data directory:

```text
data/
├── fim.db
└── fim.log
```

The `data` directory is excluded from Git.
