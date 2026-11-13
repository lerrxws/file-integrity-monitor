from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db.baseline import Baseline


def baseline_exists(engine: Engine) -> bool:
    with Session(engine) as session:
        return session.scalar(select(Baseline.path).limit(1)) is not None


def get_baseline_hash(engine: Engine, path: str) -> str | None:
    with Session(engine) as session:
        return session.scalar(select(Baseline.sha256).where(Baseline.path == path))


def save_baseline(engine: Engine, hashes: dict[str, str]) -> None:
    if not hashes:
        raise ValueError("Cannot create a baseline for an empty website.")

    with Session(engine) as session, session.begin():
        session.execute(text("BEGIN IMMEDIATE"))
        if session.scalar(select(Baseline.path).limit(1)) is not None:
            raise ValueError("A baseline already exists; it will not be overwritten.")
        session.add_all(
            Baseline(path=path, sha256=digest) for path, digest in hashes.items()
        )
