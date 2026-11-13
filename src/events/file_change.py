from dataclasses import dataclass


@dataclass(frozen=True)
class FileChange:
    event_type: str
    src_path: str
    dest_path: str | None = None
