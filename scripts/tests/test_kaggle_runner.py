from __future__ import annotations

import importlib.util
from pathlib import Path


def load_runner_module():
    runner_path = Path(__file__).resolve().parents[2] / "kaggle" / "runner.py"
    spec = importlib.util.spec_from_file_location("audio_montage_kaggle_runner", runner_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


find_kaggle_config_candidates = load_runner_module().find_kaggle_config_candidates


def test_find_kaggle_config_candidates_supports_legacy_one_level_mount(tmp_path) -> None:
    config = tmp_path / "audio-guided-video-montage-input" / "kaggle_job_config.json"
    config.parent.mkdir(parents=True)
    config.write_text("{}", encoding="utf-8")

    assert find_kaggle_config_candidates(tmp_path) == [config]


def test_find_kaggle_config_candidates_supports_nested_dataset_mount(tmp_path) -> None:
    config = (
        tmp_path
        / "datasets"
        / "padalgoacademy"
        / "audio-guided-video-montage-input"
        / "kaggle_job_config.json"
    )
    config.parent.mkdir(parents=True)
    config.write_text("{}", encoding="utf-8")

    assert find_kaggle_config_candidates(tmp_path) == [config]
