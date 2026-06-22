from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from shared.paths import repo_root


def run_validate(
    *,
    input_dir: Path | None = None,
    samples_dir: Path | None = None,
) -> int:
    if input_dir is not None and samples_dir is not None:
        raise ValueError("Use only one of input_dir or samples_dir")

    command = [sys.executable, str(repo_root() / "scripts" / "validate_json.py")]
    if input_dir is not None:
        command.extend(["--input-dir", str(input_dir)])
    elif samples_dir is not None:
        command.extend(["--samples-dir", str(samples_dir)])

    result = subprocess.run(command, cwd=repo_root(), check=False)
    return int(result.returncode)
