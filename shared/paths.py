from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(relative: str | Path, *, base: Path | None = None) -> Path:
    path = Path(relative)
    if path.is_absolute():
        raise ValueError(f"Expected relative path, got absolute: {path}")
    root = base or repo_root()
    return (root / path).resolve()


def ensure_dir(path: str | Path, *, base: Path | None = None) -> Path:
    directory = resolve_path(path, base=base) if not Path(path).is_absolute() else Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
