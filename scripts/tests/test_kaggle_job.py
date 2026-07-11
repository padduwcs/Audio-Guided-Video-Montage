from __future__ import annotations

from scripts.kaggle_job import (
    _read_kaggle_log_file,
    is_kaggle_auth_error,
    is_kaggle_forbidden,
    is_dataset_status_ready,
    kaggle_permission_help,
    kaggle_status_value,
    missing_dataset_file_groups,
)


def test_kaggle_status_value_ignores_cli_warning_lines() -> None:
    output = "\n".join(
        [
            "Warning: Looks like you're using an outdated `kaggle` version",
            "ready",
        ]
    )

    assert kaggle_status_value(output) == "ready"


def test_is_dataset_status_ready_requires_successful_ready_status() -> None:
    ready_output = "\n".join(
        [
            "Warning: Looks like you're using an outdated `kaggle` version",
            "ready",
        ]
    )
    forbidden_output = "403 Client Error: Forbidden for url: https://api.kaggle.com"

    assert is_dataset_status_ready(0, ready_output)
    assert not is_dataset_status_ready(1, forbidden_output)


def test_is_kaggle_forbidden_detects_api_403() -> None:
    output = "403 Client Error: Forbidden for url: https://www.kaggle.com/api/v1/datasets"

    assert is_kaggle_forbidden(output)


def test_is_kaggle_auth_error_detects_api_401() -> None:
    output = "401 Client Error: Unauthorized for url: https://api.kaggle.com/v1/blobs.BlobApiService/StartBlobUpload"

    assert is_kaggle_auth_error(output)


def test_kaggle_permission_help_mentions_same_account() -> None:
    message = kaggle_permission_help("user/audio-guided-video-montage-input")

    assert "same Kaggle account" in message
    assert "401 Unauthorized" in message
    assert "403 Forbidden" in message


def test_read_kaggle_json_log_file_extracts_data_lines(tmp_path) -> None:
    log_path = tmp_path / "runner.log"
    log_path.write_text(
        '[{"stream_name":"stderr","data":"Traceback line\\\\n"},'
        '{"stream_name":"stdout","data":"Final line\\\\n"}]',
        encoding="utf-8",
    )

    assert _read_kaggle_log_file(log_path) == "Traceback line\nFinal line"


def test_missing_dataset_file_groups_accepts_zip_uploads() -> None:
    output = """
    kaggle_job_config.json
    raw.zip
    project_source_123.zip
    """
    groups = [
        ["kaggle_job_config.json"],
        ["raw.zip", "raw/video.mp4", "raw/audio.mp3"],
        ["project_source_123.zip", "project_source_123/integration/run_pipeline.py"],
    ]

    assert missing_dataset_file_groups(output, groups) == []


def test_missing_dataset_file_groups_accepts_extracted_paths() -> None:
    output = """
    kaggle_job_config.json
    raw/video.mp4
    raw/audio.mp3
    project_source_123/requirements-kaggle.txt
    project_source_123/integration/run_pipeline.py
    """
    groups = [
        ["kaggle_job_config.json"],
        ["raw.zip", "raw/video.mp4", "raw/audio.mp3"],
        ["project_source_123.zip", "project_source_123/integration/run_pipeline.py"],
    ]

    assert missing_dataset_file_groups(output, groups) == []


def test_missing_dataset_file_groups_reports_missing_group() -> None:
    output = """
    kaggle_job_config.json
    raw/video.mp4
    """
    groups = [
        ["kaggle_job_config.json"],
        ["raw.zip", "raw/video.mp4"],
        ["project_source_123.zip", "project_source_123/integration/run_pipeline.py"],
    ]

    assert missing_dataset_file_groups(output, groups) == [
        "project_source_123.zip or project_source_123/integration/run_pipeline.py"
    ]

