import argparse
import logging
from pathlib import Path

from .app import run
from .config import load_config


PROJECT_DIR = Path(__file__).resolve().parents[2]
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S%z"

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish today's date and name day.")
    parser.add_argument("--config", type=Path, default=PROJECT_DIR / "config" / "config.json")
    parser.add_argument("--once", action="store_true", help="Publish one page, then exit.")
    parser.add_argument("--ready-file", type=Path, help="Create a readiness marker after publishing.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    try:
        settings = load_config(args.config, PROJECT_DIR)
        run(settings, once=args.once, ready_file=args.ready_file)

    except KeyboardInterrupt:
        logger.info("Stopped publisher.")

    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.error("Cannot run publisher: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
