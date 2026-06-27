"""Core rendering logic for Stage 8 Renderer."""

import json
import os
import subprocess
import tempfile
import shutil
import time
from datetime import datetime, timezone
from tqdm import tqdm

def has_audio_stream(source_path):
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", source_path],
            capture_output=True, text=True
        )
        return "audio" in probe.stdout
    except:
        return False

def extract_segment_ffmpeg(
    source_path, start, end, output_path,
    speed=1.0, width=None, height=None, fps=None, crop_mode="center_crop",
    video_codec="libx264", video_bitrate=None,
    audio_codec="aac", audio_bitrate=None,
    hwaccel=None,
    keep_original_audio=False, original_audio_volume=0.0, volume=None
):
    """Extract a video segment using ffmpeg with speed and crop filters."""
    duration = end - start
    cmd = ["ffmpeg", "-y"]
    if hwaccel:
        cmd += ["-hwaccel", hwaccel]
        
    cmd += ["-ss", str(start), "-i", source_path]
    cmd += ["-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    
    has_audio = has_audio_stream(source_path)
    effective_vol = volume if volume is not None else original_audio_volume
    use_original_audio = has_audio and keep_original_audio and effective_vol > 0.0

    cmd += ["-map", "0:v:0"]
    if use_original_audio:
        cmd += ["-map", "0:a:0"]
    else:
        cmd += ["-map", "1:a:0"]
        
    vf = []
    af = []
    
    if speed != 1.0:
        vf.append(f"setpts={1.0/speed}*PTS")
        if use_original_audio:
            af.append(f"atempo={speed}")
            
    if width and height:
        if crop_mode == "fit":
            vf.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
        elif crop_mode == "fill":
            vf.append(f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}")
        elif crop_mode == "blur_background":
            vf.append(f"split[a][b];[a]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=20:20[b_bg];[b]scale={width}:{height}:force_original_aspect_ratio=decrease[fg];[b_bg][fg]overlay=(W-w)/2:(H-h)/2")
        else: # center_crop
            vf.append(f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}")
            
    if fps:
        vf.append(f"fps={fps}")
        
    if use_original_audio and effective_vol != 1.0:
        af.append(f"volume={effective_vol}")
        
    if vf:
        cmd += ["-vf", ",".join(vf)]
    if af:
        cmd += ["-af", ",".join(af)]
        
    cmd += ["-c:v", video_codec]
    if video_bitrate:
        cmd += ["-b:v", video_bitrate]
        
    # Enforce standard audio format so concat demuxer doesn't fail
    cmd += ["-c:a", audio_codec, "-ar", "44100", "-ac", "2"]
    if audio_bitrate:
        cmd += ["-b:a", audio_bitrate]
        
    cmd += ["-t", str(duration)]
    cmd.append(output_path)
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")

def get_transition_type(visual_item, default_transition="cut"):
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
    voice_over_path=None,
    progress_callback=None
):
    start_time = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    errors = []
    warnings = []
    
    try:
        with open(timeline_path, "r", encoding="utf-8") as f:
            timeline = json.load(f)
    except Exception as e:
        _write_log(log_path, "1.0", "unknown", started_at, "failed", output_path, 0, 0, [], [f"Failed to load timeline: {e}"])
        raise

    project_id = timeline.get("project_id", "unknown")
    segments = timeline.get("items", [])
    render_settings = timeline.get("render_settings", {})
    
    width = render_settings.get("width")
    height = render_settings.get("height")
    fps = render_settings.get("fps")
    default_crop_mode = render_settings.get("crop_mode", "center_crop")
    keep_original_audio = render_settings.get("keep_original_audio", False)
    original_audio_volume = render_settings.get("original_audio_volume", 0.0)
    default_transition = render_settings.get("default_transition", "cut")
    out_format = out_format or render_settings.get("format", "mp4")

    if preview:
        segments = segments[:1]
        video_bitrate = "400k"
        audio_bitrate = "64k"
        video_codec = video_codec or "libx264"
        
    temp_dir = tempfile.mkdtemp(prefix="render_segments_")
    segment_files = []
    transitions = []

    try:
        total_segs = len(segments)
        for idx, item in enumerate(tqdm(segments, desc="Extracting segments", unit="seg")):
            seg_id = item.get("segment_id", f"seg_{idx}")
            if progress_callback:
                progress_callback(idx / (total_segs + 1), f"Đang trích xuất segment {idx+1}/{total_segs}...")
            
            visual_items = item.get("visual_items", [])
            if not visual_items:
                err_msg = f"Missing visual_items for segment {seg_id}"
                errors.append(err_msg)
                raise ValueError(err_msg)
                
            # MVP: Use first visual item
            vi = visual_items[0]
            source_path = vi.get("source_path")
            clip_start = vi.get("clip_start")
            clip_end = vi.get("clip_end")
            
            if not (source_path and clip_start is not None and clip_end is not None):
                err_msg = f"Missing source_path/clip_start/clip_end for segment {seg_id}"
                errors.append(err_msg)
                raise ValueError(err_msg)
                
            abs_source = os.path.abspath(source_path)
            if not os.path.exists(abs_source):
                err_msg = f"Source file not found: {abs_source} for segment {seg_id}"
                errors.append(err_msg)
                raise ValueError(err_msg)
                
            seg_out = os.path.join(temp_dir, f"segment_{idx+1}.mp4")
            
            speed = vi.get("speed", 1.0)
            crop_mode = vi.get("crop_mode") or default_crop_mode
            volume = vi.get("volume")
            
            try:
                extract_segment_ffmpeg(
                    abs_source, clip_start, clip_end, seg_out,
                    speed=speed, width=width, height=height, fps=fps, crop_mode=crop_mode,
                    video_codec=video_codec or "libx264", video_bitrate=video_bitrate,
                    audio_codec=audio_codec or "aac", audio_bitrate=audio_bitrate,
                    hwaccel=hwaccel,
                    keep_original_audio=keep_original_audio,
                    original_audio_volume=original_audio_volume,
                    volume=volume
                )
                segment_files.append(seg_out)
            except Exception as e:
                err_msg = f"Segment {seg_id} failed to extract: {e}"
                errors.append(err_msg)
                raise ValueError(err_msg)
                
            if idx < len(segments) - 1:
                next_vi = segments[idx + 1].get("visual_items", [{}])[0]
                transitions.append(get_transition_type(next_vi, default_transition))
                
        if not segment_files:
            raise ValueError("No segments extracted. Nothing to render.")

        if progress_callback:
            progress_callback(total_segs / (total_segs + 1), "Đang ghép nối các phân đoạn và lồng âm thanh thuyết minh...")

        if all(t == "cut" for t in transitions):
            concat_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file, "w") as cf:
                for seg in segment_files:
                    cf.write(f"file '{seg}'\n")
                    
            concat_cmd = ["ffmpeg", "-y"]
            if hwaccel:
                concat_cmd += ["-hwaccel", hwaccel]
            concat_cmd += ["-f", "concat", "-safe", "0", "-i", concat_file]
            
            if voice_over_path and os.path.exists(voice_over_path):
                concat_cmd += ["-i", voice_over_path]
                # Map video from concat, mix audio if needed
                concat_cmd += ["-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first[aout]", "-map", "0:v", "-map", "[aout]"]
            else:
                warnings.append("No valid voice_over_path provided, resulting video will only have original audio if any.")
                concat_cmd += ["-map", "0:v", "-map", "0:a?"]

            concat_cmd += ["-c:v", "copy" if not overlay_image else video_codec or "libx264"]
            concat_cmd += ["-c:a", audio_codec or "aac", "-shortest", output_path]
            
            result = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                err_msg = f"ffmpeg concat failed: {result.stderr.decode()}"
                errors.append(err_msg)
                raise RuntimeError(err_msg)
        else:
            warnings.append("Transitions other than 'cut' are not fully supported for multi-segment in MVP. Fallback to cut is recommended.")
            # Basic fallback if complex is needed (skipped for brevity)
            raise NotImplementedError("Complex transitions not implemented completely.")

        render_time = time.time() - start_time
        _write_log(log_path, "1.0", project_id, started_at, "success", output_path, sum(item.get("duration", 0) for item in segments), render_time, warnings, errors)

        if progress_callback:
            progress_callback(1.0, "Hoàn tất render video!")

    except Exception as e:
        render_time = time.time() - start_time
        _write_log(log_path, "1.0", project_id, started_at, "failed", output_path, 0, render_time, warnings, errors)
        raise e
    finally:
        shutil.rmtree(temp_dir)

def _write_log(log_path, schema_version, project_id, started_at, status, output_path, duration, render_time, warnings, errors):
    if not log_path:
        return
    log_data = {
        "schema_version": schema_version,
        "project_id": project_id,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "output_path": output_path,
        "duration": duration,
        "render_time": render_time,
        "warnings": warnings,
        "errors": errors
    }
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as lf:
        json.dump(log_data, lf, indent=2)