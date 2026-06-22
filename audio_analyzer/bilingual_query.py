"""Build meaning-preserving extractive queries from bilingual transcripts."""

from __future__ import annotations

import re

from dataclasses import dataclass

from audio_analyzer.bilingual_keywords import KeywordExtraction, is_call_to_action


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


@dataclass(frozen=True)
class _Clause:
    text: str
    position: int


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


class BilingualQueryBuilder:
    """Return a grammatical query while preserving transcript meaning and order."""

    def __init__(
        self,
        *,
        max_words: int = 16,
        min_words: int = 4,
        min_reduction_ratio: float = 0.15,
    ) -> None:
        self.max_words = max_words
        self.min_words = min_words
        self.min_reduction_ratio = min_reduction_ratio

    def build(self, text: str, extraction: KeywordExtraction) -> tuple[str, bool]:
        cleaned_text = _clean_query(text)
        query = cleaned_text
        source_words = _word_count(cleaned_text)
        maximum_candidate_words = min(
            self.max_words,
            int(source_words * (1.0 - self.min_reduction_ratio)),
        )
        candidates: list[tuple[float, int, str]] = []
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

        contains_keyword = any(
            _contains_keyword(query, keyword) for keyword in extraction.keywords
        )
        is_generic = _word_count(query) < self.min_words or (
            not contains_keyword and is_call_to_action(query)
        )
        return query, is_generic
