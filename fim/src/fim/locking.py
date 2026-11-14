from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat


@contextmanager
def scan_lock(path: Path | None):
    if path is None:
        yield
        return

    if not stat.S_ISDIR(path.parent.lstat().st_mode):
        raise ValueError("Scan lock directory must not be a symlink.")

    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)

    with os.fdopen(descriptor, "rb") as file:
        if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
            raise ValueError("Scan lock must be a regular file.")

        fcntl.flock(file, fcntl.LOCK_SH)

        yield
