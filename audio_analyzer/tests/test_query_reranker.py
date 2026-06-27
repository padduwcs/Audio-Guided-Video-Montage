from __future__ import annotations

import unittest
import os
import sys
import types
from unittest.mock import patch

from audio_analyzer.bilingual_keywords import BilingualKeywordExtractor
from audio_analyzer.bilingual_query import BilingualQueryBuilder
from audio_analyzer.query_reranker import (
    QueryReranker,
    QueryRerankerError,
    SentenceTransformerQueryReranker,
)


class FakeSentenceModel:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors
        self.encode_calls: list[list[str]] = []

    def encode(self, texts, **kwargs):
        self.encode_calls.append(list(texts))
        return [self.vectors[text] for text in texts]


class LastCandidateReranker(QueryReranker):
    @property
    def backend_name(self) -> str:
        return "fake-reranker"

    @property
    def model_name(self) -> str:
        return "fixed-vectors"

    def select_many(self, source_texts, candidate_groups):
        return [candidates[-1] for candidates in candidate_groups]


class QueryRerankerTests(unittest.TestCase):
    def test_real_loader_disables_tensorflow_before_sentence_transformers_import(self) -> None:
        calls: list[tuple[str, str]] = []

        class FakeSentenceTransformer:
            def __init__(self, model_name: str, *, device: str) -> None:
                calls.append((model_name, device))

        fake_module = types.ModuleType("sentence_transformers")
        fake_module.SentenceTransformer = FakeSentenceTransformer
        reranker = SentenceTransformerQueryReranker(model="fake-model")

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("USE_TF", None)
            with patch.dict(sys.modules, {"sentence_transformers": fake_module}):
                reranker._load_model()
            self.assertEqual(os.environ["USE_TF"], "0")

        self.assertEqual(calls, [("fake-model", "cpu")])

    def test_model_is_loaded_lazily_and_batch_encoded_once(self) -> None:
        source = "thiết kế thuật toán bằng các bước logic"
        concise = "thiết kế thuật toán"
        unrelated = "đăng ký kênh"
        fake_model = FakeSentenceModel(
            {
                source: [1.0, 0.0],
                concise: [0.96, 0.28],
                unrelated: [0.5, 0.866],
            }
        )
        load_calls: list[str] = []

        def load(model_name: str):
            load_calls.append(model_name)
            return fake_model

        reranker = SentenceTransformerQueryReranker(
            model="fake-model",
            min_similarity=0.72,
            brevity_weight=0.3,
            model_loader=load,
        )

        self.assertEqual(load_calls, [])
        selected = reranker.select_many(
            [source],
            [[source, concise, unrelated]],
        )

        self.assertEqual(selected, [concise])
        self.assertEqual(load_calls, ["fake-model"])
        self.assertEqual(len(fake_model.encode_calls), 1)

        reranker.select_many([source], [[source, concise]])
        self.assertEqual(len(fake_model.encode_calls), 1)

    def test_low_similarity_candidate_falls_back_to_source(self) -> None:
        source = "thiết kế thuật toán"
        unrelated = "đăng ký kênh"
        fake_model = FakeSentenceModel(
            {source: [1.0, 0.0], unrelated: [0.0, 1.0]}
        )
        reranker = SentenceTransformerQueryReranker(
            model_loader=lambda _: fake_model,
            min_similarity=0.8,
        )

        self.assertEqual(
            reranker.select_many([source], [[source, unrelated]]),
            [source],
        )
        evaluations = reranker.last_diagnostics[0]
        self.assertTrue(evaluations[0]["selected"])
        self.assertFalse(evaluations[1]["accepted"])
        self.assertEqual(
            evaluations[1]["rejection_reasons"],
            ["semantic_similarity_below_threshold"],
        )

    def test_source_is_fallback_not_a_competing_candidate(self) -> None:
        source = "thiết kế thuật toán bằng các bước logic rõ ràng"
        concise = "thiết kế thuật toán bằng các bước logic"
        fake_model = FakeSentenceModel(
            {source: [1.0, 0.0], concise: [0.8, 0.6]}
        )
        reranker = SentenceTransformerQueryReranker(
            model_loader=lambda _: fake_model,
            min_similarity=0.75,
            brevity_weight=0.0,
        )

        selected = reranker.select_many([source], [[source, concise]])

        self.assertEqual(selected, [concise])
        evaluations = reranker.last_diagnostics[0]
        self.assertFalse(evaluations[0]["accepted"])
        self.assertTrue(evaluations[1]["accepted"])
        self.assertTrue(evaluations[1]["selected"])

    def test_primary_safe_candidate_uses_bounded_similarity_margin(self) -> None:
        source = "CP không xây dựng sản phẩm mà giải toán dưới áp lực thời gian"
        primary = "CP giải toán áp lực thời gian"
        other = "xây dựng sản phẩm"
        fake_model = FakeSentenceModel(
            {
                source: [1.0, 0.0],
                primary: [0.70, 0.714142],
                other: [0.69, 0.723809],
            }
        )
        reranker = SentenceTransformerQueryReranker(
            model_loader=lambda _: fake_model,
            min_similarity=0.72,
            primary_similarity_margin=0.05,
        )

        selected = reranker.select_many(
            [source],
            [[source, primary, other]],
        )

        self.assertEqual(selected, [primary])
        evaluations = reranker.last_diagnostics[0]
        self.assertTrue(evaluations[1]["accepted"])
        self.assertEqual(evaluations[1]["required_similarity"], 0.67)
        self.assertFalse(evaluations[2]["accepted"])

    def test_source_only_group_skips_model_loading(self) -> None:
        def unexpected_load(_: str):
            raise AssertionError("source-only group must not load the model")

        reranker = SentenceTransformerQueryReranker(model_loader=unexpected_load)

        self.assertEqual(
            reranker.select_many(["Đây là phần cân não nhất."], [["Đây là phần cân não nhất."]]),
            ["Đây là phần cân não nhất."],
        )
        self.assertEqual(
            reranker.last_diagnostics[0][0]["rejection_reasons"],
            ["no_shortened_candidate"],
        )

    def test_model_load_error_is_clear(self) -> None:
        def fail(_: str):
            raise RuntimeError("model unavailable")

        reranker = SentenceTransformerQueryReranker(model_loader=fail)

        with self.assertRaisesRegex(QueryRerankerError, "failed to load"):
            reranker.select_many(["source text"], [["source text", "source"]])

    def test_query_builder_accepts_injected_reranker(self) -> None:
        text = (
            "Bạn thiết kế thuật toán, máy tính thực thi từng bước logic, "
            "dữ liệu đầu vào tạo ra kết quả đầu ra cụ thể."
        )
        extraction = BilingualKeywordExtractor().extract(text)
        builder = BilingualQueryBuilder(reranker=LastCandidateReranker())

        query, _ = builder.build(text, extraction)

        self.assertTrue(query)
        self.assertNotEqual(query, text)

    def test_builder_preserves_already_concise_fallback_reason(self) -> None:
        text = "Lập trình tạo ra app, web và phần mềm."
        extraction = BilingualKeywordExtractor().extract(text)
        builder = BilingualQueryBuilder(reranker=LastCandidateReranker())

        decision = builder.build_many_detailed([text], [extraction])[0]

        self.assertEqual(decision.query, text)
        self.assertEqual(decision.fallback_reason, "source_already_concise")


if __name__ == "__main__":
    unittest.main()
