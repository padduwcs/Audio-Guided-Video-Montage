"""CLI entrypoint for Review UI (Stage 7).

Usage:
    python -m review_ui.cli --project-id ... --timeline ... --matching-candidates ... --clip-metadata ... --audio-segments ... --media-metadata ... [--host ...] [--port ...] [--readonly] [--no-backup] [--log-path ...]
"""

import argparse
import sys

from review_ui.loader import load_project_data
from review_ui.validator import validate_project_data

def _maybe_import_app():
    try:
        from review_ui.app import launch_review_ui
        return launch_review_ui
    except ImportError:
        return None

def main():
    """Entrypoint for Review UI CLI."""
    parser = argparse.ArgumentParser(description="Review UI (Stage 7) CLI")
    parser.add_argument("--project-id", type=str, required=False, help="Project ID (validate match)")
    parser.add_argument("--timeline", type=str, required=True, help="Path to timeline.json")
    parser.add_argument("--matching-candidates", type=str, required=True, help="Path to matching_candidates.json")
    parser.add_argument("--clip-metadata", type=str, required=True, help="Path to clip_metadata.json")
    parser.add_argument("--audio-segments", type=str, required=True, help="Path to audio_segments.json")
    parser.add_argument("--media-metadata", type=str, required=True, help="Path to media_metadata.json")
    parser.add_argument("--readonly", action="store_true", help="Open in readonly mode")
    parser.add_argument("--no-backup", action="store_true", help="Do not create backup timeline.before_review.json")
    parser.add_argument("--log-path", type=str, default=None, help="Path to review_ui_log.json")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for UI server (future)")
    parser.add_argument("--port", type=int, default=7860, help="Port for UI server (future)")
    parser.add_argument("--ui", action="store_true", help="Launch Gradio UI MVP")
    args = parser.parse_args()

    if args.ui:
        launch_review_ui = _maybe_import_app()
        if not launch_review_ui:
            print("[FATAL] Gradio or app.py not available. Cannot launch UI.", file=sys.stderr)
            sys.exit(1)
        launch_review_ui(
            timeline_path=args.timeline,
            matching_candidates_path=args.matching_candidates,
            clip_metadata_path=args.clip_metadata,
            audio_segments_path=args.audio_segments,
            media_metadata_path=args.media_metadata,
            project_id=args.project_id,
            readonly=args.readonly,
            no_backup=args.no_backup,
            log_path=args.log_path,
            host=args.host,
            port=args.port,
        )
        return

    try:
        project_data = load_project_data(
            timeline_path=args.timeline,
            matching_candidates_path=args.matching_candidates,
            clip_metadata_path=args.clip_metadata,
            audio_segments_path=args.audio_segments,
            media_metadata_path=args.media_metadata,
            project_id=args.project_id,
        )
    except Exception as e:
        print(f"[FATAL] Failed to load project data: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate
    msgs = validate_project_data(project_data, mode="edit_save")
    errors = [m for m in msgs if m.level == "error"]
    warnings = [m for m in msgs if m.level == "warning"]
    if errors:
        print("Validation errors:")
        for m in errors:
            print("  ", m)
        sys.exit(2)
    if warnings:
        print("Validation warnings:")
        for m in warnings:
            print("  ", m)

    # Placeholder: print segment list and candidates
    print(f"Loaded project: {project_data.timeline.get('project_id')}")
    print(f"Segments in timeline: {len(project_data.timeline.get('items', []))}")
    for item in project_data.timeline.get("items", []):
        print(f"  Segment {item['segment_id']}: {item.get('text')[:40]}...")
        print(f"    Visual items: {len(item.get('visual_items', []))}")
        print(f"    Candidates ref: {item.get('candidates_ref')}")
    print("Review UI CLI ready. (UI server not implemented in this CLI MVP)")

if __name__ == "__main__":
    main()
