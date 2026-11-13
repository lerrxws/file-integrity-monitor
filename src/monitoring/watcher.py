from collections.abc import Callable
import logging
from pathlib import Path
import time

from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileSystemMovedEvent
from watchdog.observers import Observer


logger = logging.getLogger(__name__)


class WebsiteChangeHandler(FileSystemEventHandler):
    def __init__(self, on_change: Callable[[str], None]) -> None:
        super().__init__()
        self.on_change = on_change

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory or event.event_type not in {"created", "modified", "deleted", "moved"}:
            return
        message = f"{event.event_type.upper()}: {event.src_path!r}"
        if isinstance(event, FileSystemMovedEvent):
            message += f" -> {event.dest_path!r}"
        logger.info(message)
        self.on_change(message)


def watch_directory(website_dir: Path, on_change: Callable[[str], None]) -> None:
    if not website_dir.is_dir():
        raise SystemExit(f"Website directory not found: {website_dir}")

    observer = Observer()
    observer.schedule(WebsiteChangeHandler(on_change), str(website_dir), recursive=True)
    observer.start()
    logger.info("Watching %s. Press Ctrl+C to stop.", website_dir)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
    logger.info("Stopped watching.")
