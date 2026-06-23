"""Optional local semantic reranking for deterministic query candidates."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any


DEFAULT_QUERY_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# The local reranker is intentionally PyTorch-only.  This must be configured
# when the module is imported, before ASR or another dependency has a chance to
# import Transformers and discover an incompatible TensorFlow/Keras runtime.
os.environ["USE_TF"] = "0"


class QueryRerankerError(RuntimeError):
    """Raised when a query reranker cannot load or run its local model."""


class QueryReranker(ABC):
    """Select one safe query from each prevalidated candidate group."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @property
    def last_diagnostics(self) -> tuple[tuple[dict[str, Any], ...], ...]:
        """Candidate evaluations from the most recent batch, when available."""

        return ()

    @abstractmethod
    def select_many(
        self,
        source_texts: Sequence[str],
        candidate_groups: Sequence[Sequence[str]],
    ) -> list[str]:
        raise NotImplementedError


class SentenceTransformerQueryReranker(QueryReranker):
    """Batch-rerank candidates with a multilingual sentence embedding model."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_QUERY_MODEL,
        min_similarity: float = 0.72,
        brevity_weight: float = 0.12,
        primary_candidate_bonus: float = 0.10,
        primary_similarity_margin: float = 0.05,
        model_loader: Callable[[str], Any] | None = None,
    ) -> None:
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be in [0.0, 1.0]")
        if brevity_weight < 0.0:
            raise ValueError("brevity_weight must be greater than or equal to 0")
        if primary_candidate_bonus < 0.0:
            raise ValueError("primary_candidate_bonus must be greater than or equal to 0")
        if not 0.0 <= primary_similarity_margin <= min_similarity:
            raise ValueError(
                "primary_similarity_margin must be in [0.0, min_similarity]"
            )
        self._model_name = model
        self.min_similarity = min_similarity
        self.brevity_weight = brevity_weight
        self.primary_candidate_bonus = primary_candidate_bonus
        self.primary_similarity_margin = primary_similarity_margin
        self._model_loader = model_loader
        self._model: Any | None = None
        self._embedding_cache: dict[str, tuple[float, ...]] = {}
        self._last_diagnostics: tuple[tuple[dict[str, Any], ...], ...] = ()

    @property
    def backend_name(self) -> str:
        return "sentence-transformers"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def last_diagnostics(self) -> tuple[tuple[dict[str, Any], ...], ...]:
        return self._last_diagnostics

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            if self._model_loader is not None:
                self._model = self._model_loader(self._model_name)
            else:
                # Repeat the process-local setting defensively in case a host
                # application changed it after importing this module.
                os.environ["USE_TF"] = "0"
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self._model_name, device="cpu")
        except ImportError as exc:
            raise QueryRerankerError(
                "local query reranking requires sentence-transformers; "
                "install project requirements first"
            ) from exc
        except Exception as exc:
            raise QueryRerankerError(
                f"failed to load local query model '{self._model_name}': {exc}"
            ) from exc
        return self._model

    def _embed_missing(self, texts: Sequence[str]) -> None:
        missing = list(dict.fromkeys(text for text in texts if text not in self._embedding_cache))
        if not missing:
            return
        model = self._load_model()
        try:
            vectors = model.encode(
                missing,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise QueryRerankerError(f"local query embedding failed: {exc}") from exc
        if len(vectors) != len(missing):
            raise QueryRerankerError("local query model returned an unexpected vector count")
        for text, vector in zip(missing, vectors):
            self._embedding_cache[text] = tuple(float(value) for value in vector)

    @staticmethod
    def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        if len(left) != len(right) or not left:
            raise QueryRerankerError("query embedding dimensions do not match")
        # Embeddings are normalized by the model, so dot product is cosine.
        return sum(a * b for a, b in zip(left, right))

    @staticmethod
    def _word_count(text: str) -> int:
        return len(text.split())

    def select_many(
        self,
        source_texts: Sequence[str],
        candidate_groups: Sequence[Sequence[str]],
    ) -> list[str]:
        if len(source_texts) != len(candidate_groups):
            raise ValueError("source_texts and candidate_groups must have equal length")
        for candidates in candidate_groups:
            if not candidates:
                raise ValueError("each candidate group must be non-empty")

        alternatives_by_group = [
            list(dict.fromkeys(candidate for candidate in candidates if candidate != source))
            for source, candidates in zip(source_texts, candidate_groups)
        ]
        all_texts: list[str] = []
        for source, alternatives in zip(source_texts, alternatives_by_group):
            if alternatives:
                all_texts.append(source)
                all_texts.extend(alternatives)
        if all_texts:
            self._embed_missing(all_texts)

        selected: list[str] = []
        diagnostic_groups: list[tuple[dict[str, Any], ...]] = []
        for source, candidates, alternatives in zip(
            source_texts,
            candidate_groups,
            alternatives_by_group,
        ):
            source_words = max(self._word_count(source), 1)
            fallback = source if source in candidates else candidates[0]
            best_candidate: str | None = None
            best_key = (-float("inf"), -float("inf"), 0)
            diagnostics: list[dict[str, Any]] = [
                {
                    "text": fallback,
                    "role": "source_fallback",
                    "semantic_similarity": 1.0 if fallback == source else None,
                    "compression_ratio": 0.0,
                    "score": None,
                    "accepted": False,
                    "selected": False,
                    "rejection_reasons": ["source_reserved_for_fallback"],
                }
            ]
            if not alternatives:
                diagnostics[0]["selected"] = True
                diagnostics[0]["rejection_reasons"] = ["no_shortened_candidate"]
                selected.append(fallback)
                diagnostic_groups.append(tuple(diagnostics))
                continue

            source_vector = self._embedding_cache[source]
            for index, candidate in enumerate(alternatives):
                similarity = self._cosine(
                    source_vector,
                    self._embedding_cache[candidate],
                )
                reduction = max(
                    0.0,
                    1.0 - self._word_count(candidate) / source_words,
                )
                is_primary = index == 0
                required_similarity = self.min_similarity - (
                    self.primary_similarity_margin if is_primary else 0.0
                )
                score = (
                    similarity
                    + self.brevity_weight * reduction
                    + (self.primary_candidate_bonus if is_primary else 0.0)
                )
                accepted = similarity >= required_similarity
                diagnostics.append(
                    {
                        "text": candidate,
                        "role": "shortened_candidate",
                        "primary_candidate": is_primary,
                        "semantic_similarity": round(similarity, 6),
                        "required_similarity": round(required_similarity, 6),
                        "compression_ratio": round(reduction, 6),
                        "score": round(score, 6),
                        "accepted": accepted,
                        "selected": False,
                        "rejection_reasons": (
                            [] if accepted else ["semantic_similarity_below_threshold"]
                        ),
                    }
                )
                if not accepted:
                    continue
                key = (score, reduction, -index)
                if key > best_key:
                    best_key = key
                    best_candidate = candidate
            chosen = best_candidate or fallback
            if best_candidate is None:
                diagnostics[0]["selected"] = True
                diagnostics[0]["rejection_reasons"] = [
                    "no_candidate_met_semantic_threshold"
                ]
            else:
                for diagnostic in diagnostics[1:]:
                    diagnostic["selected"] = diagnostic["text"] == chosen
            selected.append(chosen)
            diagnostic_groups.append(tuple(diagnostics))
        self._last_diagnostics = tuple(diagnostic_groups)
        return selected
