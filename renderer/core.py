"""Core rendering logic for Stage 8 Renderer."""

import json
import os
import subprocess
import tempfile
import shutil

def extract_segment_ffmpeg(source_path, start, end, output_path):
    """Extract a video segment using ffmpeg."""
    duration = end - start
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-i", source_path,
        "-t", str(duration),
        "-c", "copy",
        output_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")

def render_timeline(timeline_path, output_path, log_path=None):
    # Load timeline
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    segments = timeline.get("items", [])
    print(f"Rendering {len(segments)} segments (MVP ffmpeg).")

    temp_dir = tempfile.mkdtemp(prefix="render_segments_")
    segment_files = []

    try:
        for idx, item in enumerate(segments):
            # For MVP: use the first visual_item of each segment
            visual_items = item.get("visual_items", [])
            if not visual_items:
                print(f"Warning: No visual_items for segment {item.get('segment_id')}, skipping.")
                continue
            vi = visual_items[0]
            source_path = vi.get("source_path")
            clip_start = vi.get("clip_start")
            clip_end = vi.get("clip_end")
            if not (source_path and clip_start is not None and clip_end is not None):
                print(f"Warning: Missing source_path/clip_start/clip_end for segment {item.get('segment_id')}, skipping.")
                continue
            abs_source = os.path.abspath(source_path)
            if not os.path.exists(abs_source):
                print(f"Warning: Source file not found: {abs_source}, skipping.")
                continue
            seg_out = os.path.join(temp_dir, f"segment_{idx+1}.mp4")
            extract_segment_ffmpeg(abs_source, clip_start, clip_end, seg_out)
            segment_files.append(seg_out)
            print(f"Extracted segment {idx+1}: {seg_out}")

        if not segment_files:
            print("No segments extracted. Nothing to render.")
            return

        # Create a concat file for ffmpeg
        concat_file = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_file, "w") as cf:
            for seg in segment_files:
                cf.write(f"file '{seg}'\n")

        # Concatenate segments
        concat_cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path
        ]
        result = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr.decode()}")
        print(f"Output video saved to: {output_path}")

        # Optionally write a render log
        if log_path:
            log_data = {
                "status": "success",
                "segments": [item.get("segment_id") for item in segments],
                "output": output_path
            }
            with open(log_path, "w", encoding="utf-8") as lf:
                json.dump(log_data, lf, indent=2)
            print(f"Render log written to: {log_path}")

    finally:
        shutil.rmtree(temp_dir)