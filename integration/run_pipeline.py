from __future__ import annotations

import argparse
from pathlib import Path

from shared import read_json, repo_root, run_validate, write_json
from integration.sample_data import copy_sample_contracts
from integration.stages import STAGE_BY_NUMBER, stage_numbers
from timeline_planner.planner import TimelinePlanningError, build_timeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Audio-Guided Video Montage pipeline.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=repo_root() / "data" / "intermediate",
        help="Directory for intermediate JSON artifacts.",
    )
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=repo_root() / "docs" / "samples",
        help="Directory containing *_sample.json files.",
    )
    parser.add_argument("--from-stage", type=int, default=1, choices=sorted(STAGE_BY_NUMBER))
    parser.add_argument("--to-stage", type=int, default=6, choices=sorted(STAGE_BY_NUMBER))
    parser.add_argument("--use-sample-data", action="store_true", help="Copy docs/samples into input-dir for stages 1-5.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing intermediate JSON files.")
    parser.add_argument("--validate-only", action="store_true", help="Validate artifacts and exit.")
    parser.add_argument("--skip-ui", action="store_true", help="Skip Review UI stage when in range.")
    return parser.parse_args()


def _copy_samples(*, input_dir: Path, samples_dir: Path, overwrite: bool) -> None:
    copied = copy_sample_contracts(samples_dir=samples_dir, output_dir=input_dir, overwrite=overwrite)
    print(f"  copied {len(copied)} sample JSON files into {input_dir}")


def _run_timeline_planner(input_dir: Path) -> None:
    try:
        timeline, planning_log = build_timeline(
            read_json(input_dir / "media_metadata.json"),
            read_json(input_dir / "audio_segments.json"),
            read_json(input_dir / "clip_metadata.json"),
            read_json(input_dir / "matching_candidates.json"),
        )
    except (TimelinePlanningError, ValueError, OSError) as exc:
        raise RuntimeError(f"Timeline Planner failed: {exc}") from exc

    write_json(input_dir / "timeline.json", timeline)
    write_json(input_dir / "timeline_planning_log.json", planning_log)
    print(f"  wrote {input_dir / 'timeline.json'}")


def _run_stage(stage_number: int, *, input_dir: Path) -> None:
    stage = STAGE_BY_NUMBER[stage_number]
    print(f"[stage {stage_number}] {stage.description}")

    if stage_number == 6:
        _run_timeline_planner(input_dir)
        return

    if stage_number in {7, 8}:
        print("  not implemented in week 1 sample pipeline")
        return

    raise RuntimeError(f"Unsupported stage: {stage_number}")


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)

    if args.from_stage > args.to_stage:
        print("ERROR: --from-stage must be <= --to-stage")
        return 1

    if args.validate_only:
        return run_validate(input_dir=input_dir)

    selected = stage_numbers(args.from_stage, args.to_stage)
    if args.skip_ui:
        selected = [number for number in selected if number != 7]

    samples_copied = False
    for stage_number in selected:
        if stage_number <= 5:
            stage = STAGE_BY_NUMBER[stage_number]
            print(f"[stage {stage_number}] {stage.description}")
            if args.use_sample_data:
                if not samples_copied:
                    _copy_samples(input_dir=input_dir, samples_dir=args.samples_dir, overwrite=args.overwrite)
                    samples_copied = True
                else:
                    print("  using sample artifacts copied for stage 1")
            else:
                print("  skipped (module not implemented; use --use-sample-data)")
            continue

        _run_stage(stage_number, input_dir=input_dir)

    if args.to_stage >= 6:
        print("Validating runtime artifacts...")
        return run_validate(input_dir=input_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
