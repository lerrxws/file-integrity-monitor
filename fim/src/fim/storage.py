from pathlib import Path
import sqlite3


def initialize_database(path: str | Path) -> sqlite3.Connection:
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS baselines "
                "(path TEXT PRIMARY KEY NOT NULL, sha256 TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS approved_versions "
                "(path TEXT PRIMARY KEY NOT NULL, sha256 TEXT)"
            )
    except BaseException:
        connection.close()
        raise

    return connection


def get_baseline(connection: sqlite3.Connection) -> dict[str, str]:
    return dict(connection.execute("SELECT path, sha256 FROM baselines"))


def get_expected_hashes(connection: sqlite3.Connection) -> dict[str, str]:
    hashes = get_baseline(connection)

    for path, sha256 in connection.execute("SELECT path, sha256 FROM approved_versions"):
        if sha256 is None:
            hashes.pop(path, None)
        else:
            hashes[path] = sha256

    return hashes


def save_approved_version(connection: sqlite3.Connection, path: str, sha256: str | None) -> None:
    """Record one approved state; a null hash records approved absence."""
    with connection:
        connection.execute(
            "INSERT INTO approved_versions (path, sha256) VALUES (?, ?) "
            "ON CONFLICT(path) DO UPDATE SET sha256 = excluded.sha256",
            (path, sha256),
        )


def save_baseline(connection: sqlite3.Connection, hashes: dict[str, str]) -> None:
    if not hashes:
        raise ValueError("Cannot create a baseline for an empty website.")

    with connection:
        connection.execute("BEGIN IMMEDIATE")

        if connection.execute("SELECT 1 FROM baselines LIMIT 1").fetchone() is not None:
            raise ValueError("A baseline already exists; it will not be overwritten.")

        connection.executemany(
            "INSERT INTO baselines (path, sha256) VALUES (?, ?)", hashes.items()
        )
