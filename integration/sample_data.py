from __future__ import annotations

import shutil
from pathlib import Path

from shared import repo_root
from integration.stages import SAMPLE_TO_RUNTIME


def copy_sample_contracts(
    *,
    samples_dir: Path | None = None,
    output_dir: Path,
    overwrite: bool = False,
) -> list[Path]:
    source_dir = samples_dir or (repo_root() / "docs" / "samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for sample_name, runtime_name in SAMPLE_TO_RUNTIME.items():
        source = source_dir / sample_name
        target = output_dir / runtime_name
        if not source.exists():
            raise FileNotFoundError(f"Missing sample file: {source}")
        if target.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite existing file: {target}")
        shutil.copy2(source, target)
        copied.append(target)
    return copied
