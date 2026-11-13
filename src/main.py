from pathlib import Path

from logger.setup import setup_logging
from monitoring.watcher import watch_directory


def main() -> None:
    project_dir = Path(__file__).resolve().parent.parent
    try:
        setup_logging(project_dir / "logs" / "fim.log")
    except OSError as exc:
        raise SystemExit(f"Cannot initialize logging: {exc}") from exc
    watch_directory(project_dir / "web")


if __name__ == "__main__":
    main()
