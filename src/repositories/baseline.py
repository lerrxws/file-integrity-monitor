from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from db.baseline import Baseline
from db.setup import initialize_database


def save_baseline(database_path: str | Path, hashes: dict[str, str]) -> None:
    if not hashes:
        raise ValueError("Cannot create a baseline for an empty website.")

    initialize_database(database_path)
    engine = create_engine(URL.create("sqlite", database=str(database_path)))
    try:
        with Session(engine) as session, session.begin():
            session.execute(text("BEGIN IMMEDIATE"))
            if session.scalar(select(Baseline.path).limit(1)) is not None:
                raise ValueError("A baseline already exists; it will not be overwritten.")
            session.add_all(
                Baseline(path=path, sha256=digest) for path, digest in hashes.items()
            )
    finally:
        engine.dispose()
