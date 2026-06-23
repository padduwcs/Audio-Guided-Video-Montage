"""Build meaning-preserving extractive queries from bilingual transcripts."""

from __future__ import annotations

import re

from dataclasses import dataclass

from audio_analyzer.bilingual_keywords import KeywordExtraction, is_call_to_action
from audio_analyzer.query_reranker import QueryReranker


_WORD_PATTERN = re.compile(r"O\([^)]{1,8}\)|[^\W_]+", re.UNICODE)


def _word_count(text: str) -> int:
    return len(_WORD_PATTERN.findall(text))


_LEADING_FILLER_PATTERN = re.compile(
    r"^(?:(?:ờ|ừm|ừ|à|ờm|uh|um|erm)\s*[,.:;!?…-]?\s*)+",
    re.IGNORECASE | re.UNICODE,
)
_LEADING_TRANSITION_PATTERN = re.compile(
    r"^(?:(?:sau đó|tiếp theo|hãy nghĩ|nhìn chung|rồi|vậy|hoặc|hay|then|next|or)\s*[,.:;-]?\s*)+",
    re.IGNORECASE | re.UNICODE,
)
_DEPENDENT_CLAUSE_PATTERN = re.compile(
    r"^(?:còn|nhưng|mà|vì|nên|tuy nhiên|do đó|và|hay|hoặc|là|tức là|dưới|kèm theo|and|or|but|however|because)\b",
    re.IGNORECASE | re.UNICODE,
)
_TRAILING_CONNECTOR_PATTERN = re.compile(
    r"\b(?:và|hay|hoặc|nhưng|mà|and|or|but)\s*[,;:]?\s*$",
    re.IGNORECASE | re.UNICODE,
)
_FRAGMENT_START_PATTERN = re.compile(
    r"^(?:gọi là|nhanh nhất|tối ưu nhất|đúng nhưng|quá chậm|called)\b",
    re.IGNORECASE | re.UNICODE,
)
_PREDICATE_PATTERN = re.compile(
    r"\b(?:là|như|có|dùng|giúp|nhận|tạo|xây dựng|giải|thiết kế|xác định|tìm|chạy|trả|thực thi|diễn ra|quan trọng|is|are|uses?|creates?|builds?|solves?|designs?|runs?|returns?)\b",
    re.IGNORECASE | re.UNICODE,
)
_CLAUSE_PATTERN = re.compile(r"[^.!?;…]+(?:[.!?;…]+|$)", re.UNICODE)
_COMMA_UNIT_PATTERN = re.compile(r"[^,]+(?:,|$)", re.UNICODE)
_ACTION_QUERY_MARKERS = (
    "thiết kế thuật toán",
    "đọc hiểu",
    "xác định",
    "thực hiện",
    "tìm kiếm",
    "design an algorithm",
)
_NEGATION_PATTERN = re.compile(
    r"\b(?:không|chưa|chẳng|not|never)\b",
    re.IGNORECASE | re.UNICODE,
)
_NEGATION_BOUNDARY_PATTERN = re.compile(
    r",|[.!?;…]|\b(?:mà\s+là|mà\s+còn|but\s+rather)\b",
    re.IGNORECASE | re.UNICODE,
)
_EXPLICIT_CONTRAST_PATTERN = re.compile(
    r"\b(?:không\s+phải.+?mà\s+là|không\s+chỉ.+?mà\s+còn|not.+?but\s+rather)\b",
    re.IGNORECASE | re.UNICODE,
)
_METAPHOR_KEYWORDS = frozenset(
    {
        "bệ phóng", "cân não", "phần cân não nhất", "rèn giũa",
        "rèn rũa", "vũ khí",
    }
)
_GENERIC_FRAME_WORDS = frozenset({"lần"})
_GENERIC_RETRIEVAL_KEYWORDS = frozenset(
    {
        "diễn ra", "quan trọng", "tạo ra sản phẩm", "tối ưu nhất",
        "xây dựng gì", "important", "happens",
    }
)
_VAGUE_QUERY_PATTERNS = (
    re.compile(r"\bdiễn ra như (?:thế này|sau)\b", re.IGNORECASE | re.UNICODE),
    re.compile(r"^đây là (?:phần|điều)\b", re.IGNORECASE | re.UNICODE),
    re.compile(r"\btại sao\b.+\bquan trọng\b", re.IGNORECASE | re.UNICODE),
    re.compile(r"\b(?:hẹn gặp lại|phần sau|video tiếp theo)\b", re.IGNORECASE | re.UNICODE),
)


@dataclass(frozen=True)
class _Clause:
    text: str
    position: int


@dataclass(frozen=True)
class _QueryPhrase:
    text: str
    start: int
    end: int
    score: float


@dataclass(frozen=True)
class QueryBuildDecision:
    """Internal query decision details for logging and safe fallback."""

    query: str
    is_generic: bool
    candidates: tuple[str, ...]
    strategy: str
    fallback_reason: str | None
    visual_suitability: float
    candidate_evaluations: tuple[dict[str, object], ...] = ()


def _clean_query(text: str) -> str:
    """Remove only unambiguous leading speech fillers, never content words."""

    normalized = " ".join(text.split()).strip()
    without_filler = _LEADING_FILLER_PATTERN.sub("", normalized).strip()
    return without_filler or normalized


def _clauses(text: str) -> list[_Clause]:
    clauses: list[_Clause] = []
    for position, match in enumerate(_CLAUSE_PATTERN.finditer(text)):
        clause = _clean_query(match.group(0))
        if clause:
            clauses.append(_Clause(clause, position))
    return clauses


def _remove_safe_transition(text: str) -> str:
    shortened = _LEADING_TRANSITION_PATTERN.sub("", text).strip()
    return shortened or text


def _comma_units(text: str) -> list[str]:
    return [
        match.group(0).strip()
        for match in _COMMA_UNIT_PATTERN.finditer(text)
        if match.group(0).strip()
    ]


def _trim_span(text: str) -> str:
    return _remove_safe_transition(text.strip().strip(",").strip())


def _is_independent_span(text: str) -> bool:
    return (
        not _DEPENDENT_CLAUSE_PATTERN.match(text)
        and not _TRAILING_CONNECTOR_PATTERN.search(text)
        and not _FRAGMENT_START_PATTERN.match(text)
    )


def _contains_keyword(text: str, keyword: str) -> bool:
    return " ".join(keyword.casefold().split()) in " ".join(text.casefold().split())


def _clause_score(
    clause: str,
    extraction: KeywordExtraction,
    *,
    source_word_count: int,
) -> float:
    keyword_score = 0.0
    for keyword in extraction.keywords:
        if _contains_keyword(clause, keyword):
            keyword_score += 1.5 + min(_word_count(keyword), 5)
    score = keyword_score
    for phrase in extraction.ranked_phrases:
        if phrase.protected and _contains_keyword(clause, phrase.text):
            score += 4.0
    lowered = clause.casefold()
    if any(marker in lowered for marker in _ACTION_QUERY_MARKERS):
        score += 5.0
    count = _word_count(clause)
    score += keyword_score / max(count, 1)
    score += max(source_word_count - count, 0) * 0.12
    score -= max(count - 12, 0) * 0.15
    return score


def _candidate_spans(text: str) -> list[tuple[int, str]]:
    """Return contiguous sentence/clause spans; never join disconnected text."""

    sentences = _clauses(text)
    candidates: list[tuple[int, str]] = []
    for sentence in sentences:
        if is_call_to_action(sentence.text):
            continue

        whole_sentence = _trim_span(sentence.text)
        if _is_independent_span(whole_sentence):
            candidates.append((sentence.position * 100, whole_sentence))

        units = _comma_units(sentence.text)
        if len(units) <= 1:
            continue
        for start in range(len(units)):
            for end in range(start + 1, min(start + 3, len(units)) + 1):
                span = _trim_span(" ".join(units[start:end]))
                if span and _is_independent_span(span):
                    candidates.append((sentence.position * 100 + start, span))

    unique: dict[str, tuple[int, str]] = {}
    for position, candidate in candidates:
        normalized = " ".join(candidate.casefold().split())
        unique.setdefault(normalized, (position, candidate))
    return list(unique.values())


def _is_informative_span(text: str, extraction: KeywordExtraction) -> bool:
    matched_keywords = sum(
        _contains_keyword(text, keyword) for keyword in extraction.keywords
    )
    if matched_keywords == 0:
        return False
    if _PREDICATE_PATTERN.search(text):
        return True
    return matched_keywords >= 3


def _preserves_local_protected_terms(
    candidate: str,
    source: str,
    extraction: KeywordExtraction,
) -> bool:
    source_sentence = next(
        (clause.text for clause in _clauses(source) if candidate in clause.text),
        source,
    )
    return not any(
        phrase.protected
        and _contains_keyword(source_sentence, phrase.text)
        and not _contains_keyword(candidate, phrase.text)
        for phrase in extraction.ranked_phrases
    )


def _keyword_bounded_span(
    text: str,
    extraction: KeywordExtraction,
) -> str | None:
    """Crop only a low-value prefix; preserve the grammatical tail."""

    lowered = text.casefold()
    matches: list[tuple[int, int]] = []
    for keyword in extraction.keywords:
        start = lowered.find(keyword.casefold())
        if start >= 0:
            matches.append((start, start + len(keyword)))
    if len(matches) < 2:
        return None
    start = min(match[0] for match in matches)
    cropped = _trim_span(text[start:])
    return cropped if cropped and _is_independent_span(cropped) else None


def _breaks_paired_relation(candidate: str, source: str) -> bool:
    start = source.find(candidate)
    if start < 0:
        return False
    remainder = source[start + len(candidate) :].lstrip()
    lowered = candidate.casefold()
    if "không phải" in lowered and re.match(r"^,?\s*mà\b", remainder, re.IGNORECASE):
        return True
    if "không chỉ" in lowered and re.match(
        r"^,?\s*mà\s+còn\b", remainder, re.IGNORECASE
    ):
        return True
    return False


def _negated_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for match in _NEGATION_PATTERN.finditer(text):
        boundary = _NEGATION_BOUNDARY_PATTERN.search(text, match.end())
        ranges.append((match.start(), boundary.start() if boundary else len(text)))
    return ranges


def _overlaps_range(
    start: int,
    end: int,
    ranges: list[tuple[int, int]],
) -> bool:
    return any(start < range_end and range_start < end for range_start, range_end in ranges)


def _is_protected_keyword(keyword: str, extraction: KeywordExtraction) -> bool:
    return any(
        phrase.protected and phrase.normalized == " ".join(keyword.casefold().split())
        for phrase in extraction.ranked_phrases
    )


def _phrase_score(keyword: str, extraction: KeywordExtraction) -> float:
    normalized = " ".join(keyword.casefold().split())
    if normalized in _METAPHOR_KEYWORDS or normalized in _GENERIC_RETRIEVAL_KEYWORDS:
        return -10.0
    normalized_words = set(normalized.split())
    if normalized_words & _GENERIC_FRAME_WORDS:
        return -10.0
    word_count = _word_count(keyword)
    score = 2.0 + min(max(word_count - 2, 0), 4) * 0.4 if word_count > 1 else 0.5
    if _is_protected_keyword(keyword, extraction):
        score += 7.0
    if _PREDICATE_PATTERN.search(keyword):
        score += 3.0
    if any(marker in normalized for marker in _ACTION_QUERY_MARKERS):
        score += 4.0
    return score


def _semantic_phrases(
    text: str,
    extraction: KeywordExtraction,
) -> list[_QueryPhrase]:
    lowered = text.casefold()
    negated = _negated_ranges(text)
    phrases: list[_QueryPhrase] = []
    search_offsets: dict[str, int] = {}
    for keyword in extraction.keywords:
        normalized = keyword.casefold()
        start = lowered.find(normalized, search_offsets.get(normalized, 0))
        if start < 0:
            continue
        end = start + len(keyword)
        search_offsets[normalized] = end
        if _overlaps_range(start, end, negated):
            continue
        score = _phrase_score(keyword, extraction)
        if score <= 0:
            continue
        phrases.append(_QueryPhrase(keyword, start, end, score))
    return phrases


def _build_semantic_query(
    text: str,
    extraction: KeywordExtraction,
    *,
    min_words: int,
    max_words: int,
    min_reduction_ratio: float,
) -> tuple[str, tuple[str, ...]] | None:
    # Do not combine phrases from separate sentences; an independent sentence
    # candidate is safer in that case.
    if len(_clauses(text)) != 1 or is_call_to_action(text):
        return None

    ranked = sorted(
        _semantic_phrases(text, extraction),
        key=lambda phrase: (-phrase.score, phrase.start, -len(phrase.text)),
    )
    selected: list[_QueryPhrase] = []
    word_total = 0
    for phrase in ranked:
        words = _word_count(phrase.text)
        if word_total + words > max_words:
            continue
        selected.append(phrase)
        word_total += words

    if len(selected) < 2 or word_total < min_words:
        return None
    source_words = _word_count(text)
    if word_total > int(source_words * (1.0 - min_reduction_ratio)):
        return None

    selected.sort(key=lambda phrase: phrase.start)
    query = ", ".join(phrase.text for phrase in selected)
    return query, tuple(phrase.text for phrase in selected)


def _keyword_coverage(query: str, keywords: tuple[str, ...]) -> int:
    return sum(_contains_keyword(query, keyword) for keyword in keywords)


def _semantic_coverage_score(
    query: str,
    keywords: tuple[str, ...],
    extraction: KeywordExtraction,
) -> float:
    return sum(
        _phrase_score(keyword, extraction)
        for keyword in keywords
        if _contains_keyword(query, keyword)
    )


def _is_vague_query(text: str) -> bool:
    return any(pattern.search(text) for pattern in _VAGUE_QUERY_PATTERNS)


def _visual_suitability(
    query: str,
    extraction: KeywordExtraction,
) -> float:
    """Estimate whether a grounded query contains retrievable visual concepts."""

    if is_call_to_action(query) or _is_vague_query(query):
        return 0.0
    matched = [
        keyword
        for keyword in extraction.keywords
        if _contains_keyword(query, keyword)
        and " ".join(keyword.casefold().split()) not in _GENERIC_RETRIEVAL_KEYWORDS
    ]
    if not matched:
        return 0.1 if _PREDICATE_PATTERN.search(query) else 0.0
    score = 0.35
    score += min(len(matched), 3) * 0.12
    if any(_word_count(keyword) >= 2 for keyword in matched):
        score += 0.12
    if any(_is_protected_keyword(keyword, extraction) for keyword in matched):
        score += 0.12
    if _PREDICATE_PATTERN.search(query):
        score += 0.08
    return round(min(score, 1.0), 3)


def _is_generic_result(
    query: str,
    extraction: KeywordExtraction,
    *,
    min_words: int,
) -> bool:
    contains_keyword = any(
        _contains_keyword(query, keyword) for keyword in extraction.keywords
    )
    return (
        _word_count(query) < min_words
        or extraction.is_generic
        or is_call_to_action(query)
        or _is_vague_query(query)
        or not contains_keyword
        or _visual_suitability(query, extraction) < 0.35
    )


class BilingualQueryBuilder:
    """Return a grammatical query while preserving transcript meaning and order."""

    def __init__(
        self,
        *,
        max_words: int = 20,
        min_words: int = 4,
        min_reduction_ratio: float = 0.15,
        min_source_words_for_reduction: int = 13,
        reranker: QueryReranker | None = None,
    ) -> None:
        if min_source_words_for_reduction < 1:
            raise ValueError("min_source_words_for_reduction must be positive")
        self.max_words = max_words
        self.min_words = min_words
        self.min_reduction_ratio = min_reduction_ratio
        self.min_source_words_for_reduction = min_source_words_for_reduction
        self.reranker = reranker

    def _build_rule_result(
        self,
        text: str,
        extraction: KeywordExtraction,
    ) -> QueryBuildDecision:
        cleaned_text = _clean_query(text)
        query = cleaned_text
        source_words = _word_count(cleaned_text)
        # Short factual sentences are already concise.  Compressing them tends
        # to discard useful examples (for example "app, web, phần mềm") for no
        # meaningful retrieval gain.  Explicit contrast/negation is the one
        # exception because retaining its negative side can invert the intent.
        allow_reduction = (
            source_words >= self.min_source_words_for_reduction
            or _NEGATION_PATTERN.search(cleaned_text) is not None
            or _EXPLICIT_CONTRAST_PATTERN.search(cleaned_text) is not None
        )
        if not allow_reduction:
            is_generic = _is_generic_result(
                cleaned_text,
                extraction,
                min_words=self.min_words,
            )
            return QueryBuildDecision(
                query=cleaned_text,
                is_generic=is_generic,
                candidates=(cleaned_text,),
                strategy="rules",
                fallback_reason=(
                    "no_visual_query" if is_generic else "source_already_concise"
                ),
                visual_suitability=_visual_suitability(cleaned_text, extraction),
            )
        maximum_candidate_words = min(
            self.max_words,
            int(source_words * (1.0 - self.min_reduction_ratio)),
        )
        candidates: list[tuple[float, int, str]] = []
        safe_candidates: list[str] = []
        raw_candidates = _candidate_spans(cleaned_text)
        bounded_candidates = [
            (position, bounded)
            for position, candidate in raw_candidates
            if (bounded := _keyword_bounded_span(candidate, extraction)) is not None
        ]
        for position, candidate in raw_candidates + bounded_candidates:
            candidate_words = _word_count(candidate)
            if not self.min_words <= candidate_words <= maximum_candidate_words:
                continue
            if _breaks_paired_relation(candidate, cleaned_text):
                continue
            if not _preserves_local_protected_terms(
                candidate,
                cleaned_text,
                extraction,
            ):
                continue
            if not _is_informative_span(candidate, extraction):
                continue
            safe_candidates.append(candidate)
            candidates.append(
                (
                    _clause_score(
                        candidate,
                        extraction,
                        source_word_count=source_words,
                    ),
                    position,
                    candidate,
                )
            )
        if candidates:
            _, _, query = max(candidates, key=lambda item: (item[0], -item[1]))

        semantic = _build_semantic_query(
            cleaned_text,
            extraction,
            min_words=self.min_words,
            max_words=self.max_words,
            min_reduction_ratio=self.min_reduction_ratio,
        )
        if semantic is not None:
            semantic_query, semantic_keywords = semantic
            safe_candidates.append(semantic_query)
            current_coverage = _keyword_coverage(query, semantic_keywords)
            semantic_coverage = len(semantic_keywords)
            current_semantic_score = _semantic_coverage_score(
                query,
                semantic_keywords,
                extraction,
            )
            semantic_score = _semantic_coverage_score(
                semantic_query,
                semantic_keywords,
                extraction,
            )
            if (
                query == cleaned_text
                or semantic_coverage >= current_coverage + 2
                or semantic_score >= current_semantic_score + 2.0
                or (
                    semantic_coverage > current_coverage
                    and _EXPLICIT_CONTRAST_PATTERN.search(cleaned_text)
                )
            ):
                query = semantic_query

        candidate_pool = tuple(
            dict.fromkeys((cleaned_text, query, *safe_candidates))
        )
        is_generic = _is_generic_result(
            query,
            extraction,
            min_words=self.min_words,
        )
        fallback_reason = None
        if query == cleaned_text:
            fallback_reason = (
                "no_visual_query" if is_generic else "no_safe_reduction"
            )
        return QueryBuildDecision(
            query=query,
            is_generic=is_generic,
            candidates=candidate_pool,
            strategy="rules",
            fallback_reason=fallback_reason,
            visual_suitability=_visual_suitability(query, extraction),
        )

    def build_many_detailed(
        self,
        texts: list[str],
        extractions: list[KeywordExtraction],
    ) -> list[QueryBuildDecision]:
        """Build safe queries and retain internal diagnostics for the log."""

        if len(texts) != len(extractions):
            raise ValueError("texts and extractions must have equal length")
        rule_results = [
            self._build_rule_result(text, extraction)
            for text, extraction in zip(texts, extractions)
        ]
        if self.reranker is None or not rule_results:
            return rule_results

        cleaned_texts = [_clean_query(text) for text in texts]
        selected = self.reranker.select_many(
            cleaned_texts,
            [decision.candidates for decision in rule_results],
        )
        rerank_diagnostics = self.reranker.last_diagnostics
        if len(rerank_diagnostics) != len(rule_results):
            rerank_diagnostics = tuple(() for _ in rule_results)
        results: list[QueryBuildDecision] = []
        for query, source, extraction, decision, evaluations in zip(
            selected,
            cleaned_texts,
            extractions,
            rule_results,
            rerank_diagnostics,
        ):
            if query not in decision.candidates:
                raise ValueError("query reranker selected a query outside its candidate group")
            generic = _is_generic_result(
                query,
                extraction,
                min_words=self.min_words,
            )
            fallback_reason = None
            if query == source:
                if decision.fallback_reason in {
                    "no_visual_query",
                    "source_already_concise",
                }:
                    fallback_reason = decision.fallback_reason
                else:
                    fallback_reason = (
                        "no_visual_query" if generic else "semantic_threshold_fallback"
                    )
            results.append(
                QueryBuildDecision(
                    query=query,
                    is_generic=generic,
                    candidates=decision.candidates,
                    strategy=self.reranker.backend_name,
                    fallback_reason=fallback_reason,
                    visual_suitability=_visual_suitability(query, extraction),
                    candidate_evaluations=evaluations,
                )
            )
        return results

    def build_many(
        self,
        texts: list[str],
        extractions: list[KeywordExtraction],
    ) -> list[tuple[str, bool]]:
        return [
            (decision.query, decision.is_generic)
            for decision in self.build_many_detailed(texts, extractions)
        ]

    def build(self, text: str, extraction: KeywordExtraction) -> tuple[str, bool]:
        return self.build_many([text], [extraction])[0]
