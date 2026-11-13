import logging
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

from app import run
from db.setup import initialize_database
from logger.setup import setup_logging


logger = logging.getLogger(__name__)


def main() -> None:
    project_dir = Path(__file__).resolve().parent.parent
    load_dotenv(project_dir / ".env")
    try:
        setup_logging(project_dir / "logs" / "fim.log")
    except OSError as exc:
        raise SystemExit(f"Cannot initialize logging: {exc}") from exc

    website_dir = project_dir / "web"
    database_path = project_dir / "data" / "fim.db"
    try:
        engine = initialize_database(database_path)
    except (OSError, ValueError, SQLAlchemyError) as exc:
        logger.error("Cannot initialize database: %s", exc)
        raise SystemExit("Cannot initialize database. Check the log for details.") from exc

    try:
        run(website_dir, engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
