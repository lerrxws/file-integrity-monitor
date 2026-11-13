import logging
from pathlib import Path


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S%z",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8", errors="backslashreplace"),
        ],
        force=True,
    )
