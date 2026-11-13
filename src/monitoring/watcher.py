from collections.abc import Callable
import logging
from os import fsdecode
from pathlib import Path
import time

from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileSystemMovedEvent
from watchdog.observers import Observer

from events.file_change import FileChange


logger = logging.getLogger(__name__)


class WebsiteChangeHandler(FileSystemEventHandler):
    def __init__(self, on_change: Callable[[FileChange], None]) -> None:
        super().__init__()
        self.on_change = on_change

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory or event.event_type not in {"created", "modified", "deleted", "moved"}:
            return
        change = FileChange(
            event_type=event.event_type,
            src_path=fsdecode(event.src_path),
            dest_path=fsdecode(event.dest_path) if isinstance(event, FileSystemMovedEvent) else None,
        )
        self.on_change(change)


def watch_directory(website_dir: Path, on_change: Callable[[FileChange], None]) -> None:
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
