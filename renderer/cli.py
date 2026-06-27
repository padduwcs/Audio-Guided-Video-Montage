"""CLI entrypoint for Stage 8 Renderer."""

import argparse
import sys
from renderer.validate import validate_timeline

def main():
    parser = argparse.ArgumentParser(description="Stage 8 Renderer CLI")
    parser.add_argument("--timeline", type=str, required=True, help="Path to timeline.json")
    parser.add_argument("--output", type=str, required=False, default="data/final/final_video.mp4", help="Output video path")
    parser.add_argument("--format", type=str, required=False, default=None, help="Output video format (e.g. mp4, mov, webm)")
    parser.add_argument("--video-codec", type=str, required=False, default=None, help="Video codec (e.g. libx264, libx265, vp9)")
    parser.add_argument("--video-bitrate", type=str, required=False, default=None, help="Video bitrate (e.g. 2M, 800k)")
    parser.add_argument("--audio-codec", type=str, required=False, default=None, help="Audio codec (e.g. aac, mp3, opus)")
    parser.add_argument("--audio-bitrate", type=str, required=False, default=None, help="Audio bitrate (e.g. 128k)")
    parser.add_argument("--hwaccel", type=str, required=False, default=None, help="Hardware acceleration (e.g. videotoolbox, cuda, vaapi)")
    parser.add_argument("--overlay-image", type=str, required=False, default=None, help="Path to overlay image (logo/watermark)")
    parser.add_argument("--overlay-pos", type=str, required=False, default="top-right", help="Overlay position: top-left, top-right, bottom-left, bottom-right")
    parser.add_argument("--preview", action="store_true", help="Render only the first segment at low resolution/bitrate for quick preview")
    parser.add_argument("--config", type=str, required=False, default=None, help="YAML/JSON config file for batch rendering")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not render")
    parser.add_argument("--log-path", type=str, required=False, default=None, help="Path to render_log.json")
    args = parser.parse_args()

    # Validate timeline
    try:
        validate_timeline(args.timeline)
        print("Timeline validation: OK")
    except Exception as e:
        print(f"[FATAL] Timeline validation failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("Dry-run mode: validation only. Exiting.")
        sys.exit(0)

    # Batch mode: load config file if specified
    if args.config:
        import json, yaml
        with open(args.config, "r", encoding="utf-8") as f:
            if args.config.endswith(".yaml") or args.config.endswith(".yml"):
                jobs = yaml.safe_load(f)
            else:
                jobs = json.load(f)
        from renderer.core import render_timeline
        for job in jobs:
            print(f"Batch render: {job.get('output', 'output.mp4')}")
            render_timeline(
                job["timeline"],
                job.get("output", "data/final/batch_output.mp4"),
                log_path=job.get("log_path"),
                out_format=job.get("format"),
                video_codec=job.get("video_codec"),
                video_bitrate=job.get("video_bitrate"),
                audio_codec=job.get("audio_codec"),
                audio_bitrate=job.get("audio_bitrate"),
                hwaccel=job.get("hwaccel"),
                overlay_image=job.get("overlay_image"),
                overlay_pos=job.get("overlay_pos", "top-right"),
                preview=job.get("preview", False)
            )
    else:
        from renderer.core import render_timeline
        render_timeline(
            args.timeline,
            args.output,
            log_path=args.log_path,
            out_format=args.format,
            video_codec=args.video_codec,
            video_bitrate=args.video_bitrate,
            audio_codec=args.audio_codec,
            audio_bitrate=args.audio_bitrate,
            hwaccel=args.hwaccel,
            overlay_image=args.overlay_image,
            overlay_pos=args.overlay_pos,
            preview=args.preview
        )
if __name__ == "__main__":
    main()