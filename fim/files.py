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


def read_json_file(path: Path, *, regular_only: bool = False) -> Any:
    reader = open_regular_file(path) if regular_only else path.open(encoding="utf-8")

    with reader as file:
        return json.load(file)


