from __future__ import annotations

from scripts.kaggle_job import kaggle_status_value


def test_kaggle_status_value_ignores_cli_warning_lines() -> None:
    output = "\n".join(
        [
            "Warning: Looks like you're using an outdated `kaggle` version",
            "ready",
        ]
    )

    assert kaggle_status_value(output) == "ready"

