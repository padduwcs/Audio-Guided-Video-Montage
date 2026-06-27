"""Command-line entry point for Audio Analyzer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from audio_analyzer.asr import ASRBackend, FasterWhisperBackend
from audio_analyzer.pipeline import PipelineError, run_pipeline
from audio_analyzer.query_reranker import (
    DEFAULT_QUERY_MODEL,
    QueryReranker,
    SentenceTransformerQueryReranker,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Audio Analyzer with the faster-whisper ASR backend."
        )
    )
    parser.add_argument(
        "--media-metadata",
        required=True,
        type=Path,
        help="Path to media_metadata.json.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory reserved for later Audio Analyzer outputs.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing audio_segments.json output.",
    )
    parser.add_argument(
        "--model",
        default="base",
        help="faster-whisper model name or local model path (default: base).",
    )
    parser.add_argument(
        "--language",
        choices=("auto", "vi", "en"),
        default="auto",
        help=(
            "Language mode: auto for detection/code-switching, vi for Vietnamese, "
            "or en for English (default: auto)."
        ),
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Inference device such as cpu or cuda (default: cpu).",
    )
    parser.add_argument(
        "--compute-type",
        default="int8",
        help="CTranslate2 compute type (default: int8).",
    )
    parser.add_argument(
        "--query-backend",
        choices=("rules", "local-embedding"),
        default="rules",
        help=(
            "Query selection backend: deterministic rules or local multilingual "
            "embedding reranking (default: rules)."
        ),
    )
    parser.add_argument(
        "--query-model",
        default=DEFAULT_QUERY_MODEL,
        help="Sentence Transformers model used by local-embedding query reranking.",
    )
    parser.add_argument(
        "--query-min-similarity",
        type=float,
        default=0.72,
        help="Minimum source/candidate cosine similarity in [0,1] (default: 0.72).",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    project_root: Path | None = None,
    asr_backend: ASRBackend | None = None,
    query_reranker: QueryReranker | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    root = (project_root or Path.cwd()).resolve()
    backend = asr_backend or FasterWhisperBackend(
        model=args.model,
        language=args.language,
        device=args.device,
        compute_type=args.compute_type,
    )
    reranker = query_reranker
    if reranker is None and args.query_backend == "local-embedding":
        reranker = SentenceTransformerQueryReranker(
            model=args.query_model,
            min_similarity=args.query_min_similarity,
        )

    try:
        result = run_pipeline(
            media_metadata_path=args.media_metadata,
            output_dir=args.output_dir,
            asr_backend=backend,
            overwrite=args.overwrite,
            language=args.language,
            query_reranker=reranker,
            project_root=root,
        )
    except PipelineError as exc:
        print(f"Audio Analyzer error: {exc}", file=sys.stderr)
        return 1

    print(f"Created {result.audio_segments_path} ({result.segment_count} segments).")
    print(f"Created {result.analysis_log_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
