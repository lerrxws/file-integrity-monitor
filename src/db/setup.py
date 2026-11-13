from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

from db.baseline import Base


def initialize_database(path: str | Path) -> Engine:
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(database_path)))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            Base.metadata.create_all(connection)
    except BaseException:
        engine.dispose()
        raise
    return engine
