from pathlib import Path
import stat

from integrity.hashing import calculate_stable_sha256


def collect_baseline(website_dir: str | Path) -> dict[str, str]:
    root = Path(website_dir)
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("The website path must be a directory, not a symlink or file.")
    return _collect_file_hashes(root.resolve())


def _collect_file_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    directories = [root]
    while directories:
        for path in directories.pop().iterdir():
            before = path.lstat()
            if stat.S_ISDIR(before.st_mode):
                directories.append(path)
            elif stat.S_ISREG(before.st_mode):
                relative_path = path.relative_to(root).as_posix()
                hashes[relative_path] = calculate_stable_sha256(path, before)
            else:
                raise ValueError(f"Symlinks and special files are unsupported: {path}")
    return hashes
