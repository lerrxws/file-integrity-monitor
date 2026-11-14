"""Publish a page and its approved hash under one filesystem lock."""

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile

from publisher.src.helpers.files import read_existing_bytes


FILE_MODE = 0o644


def _stage_bytes(directory: Path, content: bytes) -> Path:
    temporary = NamedTemporaryFile(mode="wb", dir=directory, delete=False)
    path = Path(temporary.name)

    try:
        with temporary:
            temporary.write(content)
        path.chmod(FILE_MODE)
    except BaseException:
        path.unlink(missing_ok=True)
        raise

    return path


@contextmanager
def publication_lock(manifest_path: Path | None):
    if manifest_path is None:
        yield
        return

    directory = manifest_path.parent

    if directory.is_symlink():
        raise ValueError("The manifest directory must not be a symlink.")

    try:
        directory.mkdir(parents=True, mode=0o755)
    except FileExistsError:
        created = False
    else:
        created = True

    if not stat.S_ISDIR(directory.lstat().st_mode):
        raise ValueError("The manifest directory must be a directory, not a symlink.")

    if created:
        directory.chmod(0o755)

    lock_path = manifest_path.with_suffix(".lock")
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK

    try:
        descriptor = os.open(lock_path, flags | os.O_CREAT | os.O_EXCL, FILE_MODE)
    except FileExistsError:
        descriptor = os.open(lock_path, flags)
        created = False
    else:
        created = True

    with os.fdopen(descriptor, "a+b") as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise ValueError("The publication lock must be a regular file.")

        if created:
            os.fchmod(lock.fileno(), FILE_MODE)

        fcntl.flock(lock, fcntl.LOCK_EX)

        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def publish_page(
    target: Path,
    content: bytes,
    staging_dir: Path,
    manifest_path: Path | None = None,
) -> bool:
    if manifest_path is None and read_existing_bytes(target) == content:
        return False

    website_dir = target.parent.resolve()

    if staging_dir.resolve().is_relative_to(website_dir):
        raise ValueError("staging_dir must be outside website_dir.")

    if manifest_path is not None and manifest_path == manifest_path.with_suffix(".lock"):
        raise ValueError("manifest_path must differ from its .lock path.")

    if manifest_path is not None and any(
        manifest_path.parent.resolve().is_relative_to(directory)
        for directory in (website_dir, staging_dir.resolve())
    ):
        raise ValueError("manifest_path must be outside website_dir and staging_dir.")

    staged_page = _stage_bytes(staging_dir, content)

    try:
        with publication_lock(manifest_path):
            changed = read_existing_bytes(target) != content

            if manifest_path is not None:
                approval = {"version": 1, "files": {target.name: hashlib.sha256(content).hexdigest()}}
                manifest = (json.dumps(approval, indent=2) + "\n").encode("utf-8")

                if read_existing_bytes(manifest_path) != manifest:
                    staged_manifest = _stage_bytes(manifest_path.parent, manifest)

                    try:
                        staged_manifest.replace(manifest_path)
                    finally:
                        staged_manifest.unlink(missing_ok=True)

            if changed:
                staged_page.replace(target)

            return changed
    finally:
        staged_page.unlink(missing_ok=True)
