from pathlib import Path
import stat

from repositories.baseline import save_baseline
from monitoring.integrity import calculate_stable_sha256

def create_baseline(website_dir: str | Path, database_path: str | Path) -> int:
    root, database = _validate_paths(website_dir, database_path)
    hashes = _collect_file_hashes(root)
    save_baseline(database, hashes)
    return len(hashes)


def _validate_paths(website_dir: str | Path, database_path: str | Path) -> tuple[Path, Path]:
    root = Path(website_dir)
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("The website path must be a directory, not a symlink or file.")
    root = root.resolve()
    database_path = Path(database_path).resolve()
    if database_path.is_relative_to(root):
        raise ValueError("The database must be outside the website directory.")
    return root, database_path


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

