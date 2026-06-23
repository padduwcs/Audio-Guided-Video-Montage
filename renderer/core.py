"""Core rendering logic for Stage 8 Renderer."""

import json
import os
import subprocess
import tempfile
import shutil
from tqdm import tqdm

def extract_segment_ffmpeg(source_path, start, end, output_path, video_codec=None, video_bitrate=None, audio_codec=None, audio_bitrate=None, hwaccel=None):
    """Extract a video segment using ffmpeg."""
    duration = end - start
    cmd = [
        "ffmpeg",
        "-y",
    ]
    if hwaccel:
        cmd += ["-hwaccel", hwaccel]
    cmd += [
        "-ss", str(start),
        "-i", source_path,
        "-t", str(duration),
    ]
    if video_codec:
        cmd += ["-c:v", video_codec]
    else:
        cmd += ["-c:v", "copy"]
    if video_bitrate:
        cmd += ["-b:v", video_bitrate]
    if audio_codec:
        cmd += ["-c:a", audio_codec]
    else:
        cmd += ["-c:a", "copy"]
    if audio_bitrate:
        cmd += ["-b:a", audio_bitrate]
    cmd.append(output_path)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")

def get_transition_type(visual_item, default_transition="cut"):
    """Get the transition type for a visual item, fallback to default."""
    return visual_item.get("transition") or default_transition

def render_timeline(
    timeline_path,
    output_path,
    log_path=None,
    out_format=None,
    video_codec=None,
    video_bitrate=None,
    audio_codec=None,
    audio_bitrate=None,
    hwaccel=None,
    overlay_image=None,
    overlay_pos="top-right",
    preview=False,
    voice_over_path=None
):
    # Load timeline
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    segments = timeline.get("items", [])
    render_settings = timeline.get("render_settings", {})
    default_transition = render_settings.get("default_transition", "cut")
    if preview:
        print("Preview mode: rendering only the first segment at low resolution/bitrate.")
        segments = segments[:1]
        video_bitrate = "400k"
        audio_bitrate = "64k"
        video_codec = video_codec or "libx264"
        out_format = out_format or "mp4"
    print(f"Rendering {len(segments)} segments (MVP ffmpeg, transitions supported).")

    temp_dir = tempfile.mkdtemp(prefix="render_segments_")
    segment_files = []
    transitions = []

    try:
        for idx, item in enumerate(tqdm(segments, desc="Extracting segments", unit="seg")):
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
            extract_segment_ffmpeg(
                abs_source, clip_start, clip_end, seg_out,
                video_codec=video_codec, video_bitrate=video_bitrate,
                audio_codec=audio_codec, audio_bitrate=audio_bitrate,
                hwaccel=hwaccel
            )
            segment_files.append(seg_out)
            # Determine transition to next segment
            if idx < len(segments) - 1:
                next_vi = segments[idx + 1].get("visual_items", [{}])[0]
                transition = get_transition_type(next_vi, default_transition)
                transitions.append(transition)
        if not segment_files:
            print("No segments extracted. Nothing to render.")
            return

        # If all transitions are "cut", use concat. Otherwise, use filter_complex for transitions.
        if all(t == "cut" for t in transitions):
            # Create a concat file for ffmpeg
            concat_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file, "w") as cf:
                for seg in segment_files:
                    cf.write(f"file '{seg}'\n")
            concat_cmd = [
                "ffmpeg",
                "-y",
            ]
            if hwaccel:
                concat_cmd += ["-hwaccel", hwaccel]
            concat_cmd += [
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
            ]
            if overlay_image:
                concat_cmd += ["-i", overlay_image]
                # Determine overlay position
                pos_map = {
                    "top-left": "10:10",
                    "top-right": "main_w-overlay_w-10:10",
                    "bottom-left": "10:main_h-overlay_h-10",
                    "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10"
                }
                overlay_expr = pos_map.get(overlay_pos, "main_w-overlay_w-10:10")

            # Add voiceover if provided
            if voice_over_path and os.path.exists(voice_over_path):
                concat_cmd += ["-i", voice_over_path]

            # Build mapping options
            if overlay_image:
                if voice_over_path and os.path.exists(voice_over_path):
                    concat_cmd += [
                        "-filter_complex", f"[0:v][1:v]overlay={overlay_expr}[v]",
                        "-map", "[v]", "-map", "2:a"
                    ]
                else:
                    concat_cmd += [
                        "-filter_complex", f"[0:v][1:v]overlay={overlay_expr}[v]",
                        "-map", "[v]", "-map", "0:a?"
                    ]
            else:
                if voice_over_path and os.path.exists(voice_over_path):
                    concat_cmd += [
                        "-map", "0:v", "-map", "1:a"
                    ]
                else:
                    concat_cmd += [
                        "-map", "0:v?", "-map", "0:a?"
                    ]

            if out_format:
                concat_cmd += ["-f", out_format]
            if overlay_image:
                # Must re-encode video when using filter_complex (overlay)
                concat_cmd += ["-c:v", video_codec or "libx264"]
            elif video_codec:
                concat_cmd += ["-c:v", video_codec]
            else:
                concat_cmd += ["-c:v", "copy"]
            if video_bitrate:
                concat_cmd += ["-b:v", video_bitrate]

            if voice_over_path and os.path.exists(voice_over_path):
                concat_cmd += ["-c:a", audio_codec or "aac", "-shortest"]
            elif audio_codec:
                concat_cmd += ["-c:a", audio_codec]
            else:
                concat_cmd += ["-c:a", "copy"]
            if audio_bitrate:
                concat_cmd += ["-b:a", audio_bitrate]

            concat_cmd.append(output_path)
            result = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg concat failed: {result.stderr.decode()}")
            print(f"Output video saved to: {output_path}")
        else:
            # Use filter_complex for transitions (MVP: only support fade/crossfade between segments)
            filter_complex = ""
            input_args = []
            for i, seg in enumerate(segment_files):
                input_args += ["-i", seg]
            
            if voice_over_path and os.path.exists(voice_over_path):
                voice_idx = len(segment_files)
                input_args += ["-i", voice_over_path]
                # MVP: only support crossfade between first two segments
                if len(segment_files) == 2 and transitions[0] in ("fade", "crossfade"):
                    filter_complex = "[0:v][1:v]xfade=transition=fade:duration=1:offset=4[v]"
                    cmd = ["ffmpeg", "-y"] + input_args + [
                        "-filter_complex", filter_complex,
                        "-map", "[v]", "-map", f"{voice_idx}:a", "-c:a", audio_codec or "aac", "-shortest", output_path
                    ]
                else:
                    print("Complex transitions for more than 2 segments not yet implemented.")
                    return
            else:
                # No voiceover path
                if len(segment_files) == 2 and transitions[0] in ("fade", "crossfade"):
                    filter_complex = (
                        "[0:v][1:v]xfade=transition=fade:duration=1:offset=4[v];"
                        "[0:a][1:a]acrossfade=d=1[a]"
                    )
                    cmd = ["ffmpeg", "-y"] + input_args + [
                        "-filter_complex", filter_complex,
                        "-map", "[v]", "-map", "[a]", output_path
                    ]
                else:
                    print("Complex transitions for more than 2 segments not yet implemented.")
                    return

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg filter_complex failed: {result.stderr.decode()}")
            print(f"Output video with transitions saved to: {output_path}")

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