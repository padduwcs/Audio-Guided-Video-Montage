from __future__ import annotations

import argparse
from pathlib import Path

from shared import read_json, repo_root, write_json
from timeline_planner.planner import TimelinePlanningError, build_timeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build timeline.json from intermediate pipeline artifacts.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=repo_root() / "data" / "intermediate",
        help="Directory containing upstream JSON files (default: data/intermediate).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output timeline path (default: <input-dir>/timeline.json).",
    )
    parser.add_argument(
        "--log-output",
        type=Path,
        default=None,
        help="Optional planning log path (default: <input-dir>/timeline_planning_log.json).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir
    output_path = args.output or (input_dir / "timeline.json")
    log_path = args.log_output or (input_dir / "timeline_planning_log.json")

    try:
        media_metadata = read_json(input_dir / "media_metadata.json")
        audio_segments = read_json(input_dir / "audio_segments.json")
        clip_metadata = read_json(input_dir / "clip_metadata.json")
        matching_candidates = read_json(input_dir / "matching_candidates.json")
        timeline, planning_log = build_timeline(
            media_metadata,
            audio_segments,
            clip_metadata,
            matching_candidates,
        )
    except (TimelinePlanningError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1

    write_json(output_path, timeline)
    write_json(log_path, planning_log)
    print(f"OK: wrote timeline to {output_path}")
    print(f"OK: wrote planning log to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
