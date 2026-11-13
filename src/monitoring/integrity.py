import hashlib
from os import stat_result
from pathlib import Path


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
        raise ValueError(f"File changed while creating the baseline: {path}")
    return digest
