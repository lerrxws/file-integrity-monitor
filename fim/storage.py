from collections.abc import Mapping
from datetime import date
from pathlib import Path, PurePosixPath
import re
import sqlite3


def _validate_schema(connection: sqlite3.Connection) -> None:
    tables = {
        "baselines": ({"path", "sha256"}, ("path",)),
        "expected_pages": ({"path", "expected_date", "sha256"}, ("path", "expected_date")),
    }
    for table, (names, primary_key) in tables.items():
        columns = connection.execute(f"PRAGMA table_info({table})").fetchall()
        actual_key = tuple(row[1] for row in sorted(columns, key=lambda row: row[5]) if row[5])
        if {row[1] for row in columns} != names or actual_key != primary_key:
            raise ValueError(f"Incompatible database schema for {table}; prepare a new database.")


def _validate_hashes(hashes: Mapping[str, str]) -> None:
    for path, digest in hashes.items():
        relative = PurePosixPath(path)
        if (not path or path == "." or "\\" in path or "\0" in path
                or relative.is_absolute() or ".." in relative.parts or str(relative) != path):
            raise ValueError(f"Invalid expected file path: {path!r}.")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"Invalid SHA-256 for {path!r}.")


def _get_static_hashes(connection: sqlite3.Connection) -> dict[str, str]:
    hashes = dict(connection.execute("SELECT path, sha256 FROM baselines"))
    if "index.html" in hashes:
        raise ValueError("Legacy database contains a live index.html baseline; prepare a new database.")
    _validate_hashes(hashes)
    return hashes


def seed_database(
    path: Path, static_hashes: Mapping[str, str], pages: Mapping[date, str],
) -> None:
    """Explicitly approve static files and dated pages in one transaction."""
    _validate_hashes(static_hashes)
    if "index.html" in static_hashes or not pages:
        raise ValueError("Supply dated index.html hashes separately from static files.")
    for day, digest in pages.items():
        if type(day) is not date:
            raise ValueError("Expected page dates must be calendar dates.")
        _validate_hashes({"index.html": digest})

    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS baselines "
                "(path TEXT PRIMARY KEY NOT NULL, sha256 TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS expected_pages "
                "(path TEXT NOT NULL, expected_date TEXT NOT NULL, sha256 TEXT NOT NULL, "
                "PRIMARY KEY (path, expected_date))"
            )
            _validate_schema(connection)
            existing_static = _get_static_hashes(connection)
            prepared = connection.execute("SELECT 1 FROM expected_pages LIMIT 1").fetchone() is not None
            if (prepared or existing_static) and existing_static != dict(static_hashes):
                raise ValueError("Static files differ from their approved baseline; it will not be overwritten.")
            connection.executemany(
                "INSERT OR IGNORE INTO baselines (path, sha256) VALUES (?, ?)", static_hashes.items(),
            )
            for day, digest in pages.items():
                existing = connection.execute(
                    "SELECT sha256 FROM expected_pages WHERE path = 'index.html' AND expected_date = ?",
                    (day.isoformat(),),
                ).fetchone()
                if existing is not None and existing[0] != digest:
                    raise ValueError(f"An approved page already exists for {day}; it will not be overwritten.")
                connection.execute(
                    "INSERT OR IGNORE INTO expected_pages (path, expected_date, sha256) VALUES ('index.html', ?, ?)",
                    (day.isoformat(), digest),
                )
    finally:
        connection.close()


def open_database(path: Path) -> sqlite3.Connection:
    """Open existing expectations read-only; monitoring never establishes trust."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected database is missing or not a regular file; run tools/seed_expected.py first.")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        _validate_schema(connection)
        _get_static_hashes(connection)
        if connection.execute("SELECT 1 FROM expected_pages WHERE path = 'index.html' LIMIT 1").fetchone() is None:
            raise ValueError("No expected pages exist; run tools/seed_expected.py first.")
    except BaseException:
        connection.close()
        raise
    return connection


def get_expected_hashes(connection: sqlite3.Connection, today: date) -> dict[str, str]:
    _validate_schema(connection)
    expected = _get_static_hashes(connection)
    expected.update(connection.execute(
        "SELECT path, sha256 FROM expected_pages WHERE path = 'index.html' AND expected_date = ?",
        (today.isoformat(),),
    ))
    _validate_hashes(expected)
    return expected
