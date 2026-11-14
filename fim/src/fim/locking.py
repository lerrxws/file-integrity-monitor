from contextlib import contextmanager
import fcntl
from pathlib import Path
import stat

from helpers.files import open_regular_file


@contextmanager
def scan_lock(path: Path | None):
    if path is None:
        yield
        return

    if not stat.S_ISDIR(path.parent.lstat().st_mode):
        raise ValueError("Scan lock directory must not be a symlink.")

    with open_regular_file(path) as file:
        fcntl.flock(file, fcntl.LOCK_SH)

        yield
