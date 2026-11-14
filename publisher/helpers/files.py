from collections.abc import Iterator
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
from typing import Any, BinaryIO


@contextmanager
def open_regular_file(path: Path) -> Iterator[BinaryIO]:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)

    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"Expected a regular file: {path}.")

        with os.fdopen(descriptor, "rb", closefd=False) as file:
            yield file
    finally:
        os.close(descriptor)


def read_json_file(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_existing_bytes(path: Path) -> bytes | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None

    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"Expected a regular file, not a symlink or special file: {path}")

    with open_regular_file(path) as file:
        return file.read()
