import hashlib
from os import stat_result
from pathlib import Path
import stat


HASH_CHUNK_SIZE = 1024 * 1024


def calculate_sha256(path: Path) -> str:
    before = path.lstat()

    if not stat.S_ISREG(before.st_mode):
        raise ValueError("Symlinks and special files are unsupported.")

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(HASH_CHUNK_SIZE):
            digest.update(chunk)

    after = path.lstat()

    if _file_state(before) != _file_state(after):
        raise ValueError("File changed while calculating its hash.")

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


def collect_hashes(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    hashes: dict[str, str] = {}
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
                    hashes[relative_path] = calculate_sha256(path)
            except (OSError, ValueError) as exc:
                errors[relative_path] = f"{type(exc).__name__}: {exc}"

    return hashes, errors
