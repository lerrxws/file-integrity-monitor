from collections.abc import Iterator
from contextlib import contextmanager
import json
import os
from pathlib import Path, PurePosixPath
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


def read_json_file(path: Path, *, regular_only: bool = False) -> Any:
    reader = open_regular_file(path) if regular_only else path.open(encoding="utf-8")

    with reader as file:
        return json.load(file)


def relative_file_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise ValueError("Managed paths must be normalized relative file paths.")

    path = PurePosixPath(value)

    if path.is_absolute() or ".." in path.parts or str(path) != value or value == ".":
        raise ValueError(f"Invalid relative file path: {value!r}.")

    return value
