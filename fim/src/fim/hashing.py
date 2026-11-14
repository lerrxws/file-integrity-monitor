from dataclasses import dataclass
import hashlib
import os
from os import stat_result
from pathlib import Path
import stat


HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class FileObservation:
    sha256: str
    size: int
    mtime_ns: int
    mode: int
    owner_uid: int


def calculate_sha256(path: Path) -> str:
    return observe_file(path).sha256


def observe_file(path: Path) -> FileObservation:
    before = path.lstat()

    if not stat.S_ISREG(before.st_mode):
        raise ValueError("Symlinks and special files are unsupported.")

    digest = hashlib.sha256()

    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)

    with os.fdopen(descriptor, "rb") as file:
        if _file_state(before) != _file_state(os.fstat(file.fileno())):
            raise ValueError("File changed before calculating its hash.")

        while chunk := file.read(HASH_CHUNK_SIZE):
            digest.update(chunk)

        after_read = os.fstat(file.fileno())

    after = path.lstat()

    if _file_state(before) != _file_state(after_read) or _file_state(before) != _file_state(after):
        raise ValueError("File changed while calculating its hash.")

    return FileObservation(
        digest.hexdigest(), after.st_size, after.st_mtime_ns, after.st_mode, after.st_uid,
    )


def _file_state(metadata: stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        metadata.st_uid,
        metadata.st_gid,
    )


def collect_hashes(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    files, errors = collect_observations(root)

    return {path: file.sha256 for path, file in files.items()}, errors


def collect_observations(root: Path) -> tuple[dict[str, FileObservation], dict[str, str]]:
    files: dict[str, FileObservation] = {}
    errors: dict[str, str] = {}
    directories = [root]

    while directories:
        directory = directories.pop()

        try:
            if not stat.S_ISDIR(directory.lstat().st_mode):
                raise ValueError("Expected a directory; symlinks are unsupported.")

            children = list(directory.iterdir())
        except (OSError, ValueError) as exc:
            errors[directory.relative_to(root).as_posix()] = f"{type(exc).__name__}: {exc}"
            continue

        for path in children:
            relative_path = path.relative_to(root).as_posix()

            try:
                if stat.S_ISDIR(path.lstat().st_mode):
                    directories.append(path)
                else:
                    files[relative_path] = observe_file(path)
            except (OSError, ValueError) as exc:
                errors[relative_path] = f"{type(exc).__name__}: {exc}"

    return files, errors
