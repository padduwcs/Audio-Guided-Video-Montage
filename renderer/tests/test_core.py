"""Unit tests for renderer.core."""

import os
import pytest
from renderer.core import render_timeline

SAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/samples"))

def test_render_timeline_preview(tmp_path):
    timeline_path = os.path.join(SAMPLES_DIR, "timeline_sample.json")
    output_path = tmp_path / "preview.mp4"
    render_timeline(
        timeline_path,
        str(output_path),
        preview=True
    )
    assert output_path.exists()
    assert output_path.stat().st_size > 0

def test_render_timeline_overlay(tmp_path):
    timeline_path = os.path.join(SAMPLES_DIR, "timeline_sample.json")
    overlay_path = os.path.join(SAMPLES_DIR, "hcmus_logo.png")
    output_path = tmp_path / "overlay.mp4"
    render_timeline(
        timeline_path,
        str(output_path),
        overlay_image=overlay_path,
        overlay_pos="top-left",
        preview=True
    )
    assert output_path.exists()
    assert output_path.stat().st_size > 0

def test_render_timeline_invalid_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        render_timeline("nonexistent.json", str(tmp_path / "fail.mp4"), preview=True)