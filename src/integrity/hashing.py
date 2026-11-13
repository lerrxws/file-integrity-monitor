import hashlib
from os import stat_result
from pathlib import Path
import stat
from typing import Literal


def compare_file(path: Path, baseline_hash: str | None) -> Literal["added", "modified"] | None:
    current_hash = calculate_file_hash(path)
    if baseline_hash is None:
        return "added"
    if current_hash != baseline_hash:
        return "modified"
    return None


def calculate_file_hash(path: Path) -> str:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"Expected a regular file: {path}")
    return calculate_stable_sha256(path, metadata)


def calculate_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _file_state(metadata: stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def calculate_stable_sha256(path: Path, initial_stat: stat_result) -> str:
    digest = calculate_sha256(path)
    if _file_state(initial_stat) != _file_state(path.lstat()):
        raise ValueError(f"File changed while calculating its hash: {path}")
    return digest
