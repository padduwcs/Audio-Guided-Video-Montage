"""CLI entrypoint for Stage 8 Renderer."""

import argparse
import sys
from renderer.validate import validate_timeline

def main():
    parser = argparse.ArgumentParser(description="Stage 8 Renderer CLI")
    parser.add_argument("--timeline", type=str, required=True, help="Path to timeline.json")
    parser.add_argument("--output", type=str, required=False, default="data/final/final_video.mp4", help="Output video path")
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

    # Call render pipeline
    from renderer.core import render_timeline
    render_timeline(args.timeline, args.output, log_path=args.log_path)

if __name__ == "__main__":
    main()
