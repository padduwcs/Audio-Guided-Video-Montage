"""Deterministic NLP enrichment for internal audio segments."""

from __future__ import annotations

import re
from collections.abc import Iterable

from audio_analyzer.bilingual_keywords import BilingualKeywordExtractor, KeywordExtraction
from audio_analyzer.bilingual_query import BilingualQueryBuilder
from audio_analyzer.models import AudioSegment, EnrichedAudioSegment


ALLOWED_SEGMENT_TYPES = frozenset(
    {"description", "action", "transition", "abstract", "unknown"}
)

_WORD_PATTERN = re.compile(r"[^\W\d_]+", re.UNICODE)
_STOPWORDS = frozenset(
    {
        "à",
        "ạ",
        "các",
        "cái",
        "cho",
        "chúng",
        "của",
        "đã",
        "đang",
        "đây",
        "đó",
        "được",
        "là",
        "mà",
        "một",
        "này",
        "những",
        "ở",
        "rất",
        "sẽ",
        "ta",
        "thì",
        "trong",
        "và",
        "với",
    }
)
_GENERIC_WORDS = frozenset(
    {"điều", "nơi", "mọi", "người", "tiếp", "tục", "thứ", "việc"}
)
_ABSTRACT_MARKERS = (
    "cảm thấy",
    "cảm xúc",
    "đáng nhớ",
    "hy vọng",
    "ý nghĩa",
    "ấn tượng",
    "kỷ niệm",
    "tuyệt vời",
    "bệ phóng",
    "tư duy",
)
_TRANSITION_MARKERS = (
    "sau đó",
    "tiếp theo",
    "chuyển sang",
    "di chuyển sang",
    "rời khỏi",
    "cuối cùng",
)
_ACTION_MARKERS = (
    "di chuyển",
    "tham quan",
    "trải nghiệm",
    "khám phá",
    "thực hiện",
    "bước vào",
    "đi vào",
    "chạy",
    "mở",
    "đóng",
    "xây dựng",
    "đọc hiểu",
    "giải toán",
    "thiết kế thuật toán",
    "xác định bài toán",
    "tìm ra quy luật",
)
_DESCRIPTION_MARKERS = (
    "đây là",
    "bên trong",
    "bên ngoài",
    "khu vực",
    "bao gồm",
    "gồm có",
    "nằm ở",
    "có nhiều",
    "được xây",
    "đầu vào",
    "đầu ra",
    "kết quả",
    "lời giải",
    "mô tả logic",
    "thuật toán",
    "trận đấu",
    "bộ môn",
    "môn thể thao",
    "lập trình",
    "olympic tin học",
    "phỏng vấn kỹ thuật",
)
_UNCLEAR_MARKERS = (
    "không nghe rõ",
    "không rõ",
    "[inaudible]",
    "[unknown]",
)
_PLACE_CUE_PATTERN = re.compile(
    r"\b(?:thành phố|tỉnh|quận|huyện|phường|xã)\s+[^\W\d_]+",
    re.IGNORECASE | re.UNICODE,
)


def _words(text: str) -> list[str]:
    return [match.group(0) for match in _WORD_PATTERN.finditer(text)]


def _content_words(text: str) -> list[str]:
    return [word for word in _words(text) if word.casefold() not in _STOPWORDS]


def _classify(text: str) -> str:
    lowered = text.casefold()
    if any(marker in lowered for marker in _ABSTRACT_MARKERS):
        return "abstract"
    if any(marker in lowered for marker in _TRANSITION_MARKERS):
        return "transition"
    if any(marker in lowered for marker in _ACTION_MARKERS):
        return "action"
    if any(marker in lowered for marker in _DESCRIPTION_MARKERS):
        return "description"
    return "unknown"


def _has_uncertain_proper_name_or_place(
    text: str,
    extraction: KeywordExtraction,
) -> bool:
    """Flag likely proper names because ASR has no token-level certainty here."""

    if _PLACE_CUE_PATTERN.search(text):
        return True

    for match in _WORD_PATTERN.finditer(text):
        word = match.group(0)
        if not word[0].isupper():
            continue
        ascii_letters = "".join(character for character in word if character.isalpha())
        if (
            2 <= len(ascii_letters) <= 10
            and ascii_letters.isascii()
            and ascii_letters.isupper()
        ):
            continue
        if any(
            phrase.protected
            and phrase.start <= match.start()
            and match.end() <= phrase.end
            for phrase in extraction.ranked_phrases
        ):
            continue
        prefix = text[: match.start()].rstrip()
        is_sentence_start = not prefix or prefix[-1] in ".!?…"
        if not is_sentence_start:
            return True
    return False


def _is_hard_to_understand(text: str) -> bool:
    lowered = text.casefold()
    return len(_words(text)) < 2 or any(marker in lowered for marker in _UNCLEAR_MARKERS)


def _enrich_with_extraction(
    segment: AudioSegment,
    extraction: KeywordExtraction,
    query_builder: BilingualQueryBuilder,
) -> EnrichedAudioSegment:
    query, query_too_generic = query_builder.build(segment.text, extraction)
    segment_type = _classify(segment.text)
    review_reasons: list[str] = []
    if segment.confidence is not None and segment.confidence < 0.65:
        review_reasons.append("low_asr_confidence")
    if segment.timestamp_estimated:
        review_reasons.append("estimated_timestamp")
    if segment.duration < 2.0 or segment.duration > 8.0:
        review_reasons.append("duration_out_of_range")
    if query_too_generic:
        review_reasons.append("generic_query")
    if _is_hard_to_understand(segment.text):
        review_reasons.append("transcript_hard_to_understand")
    if segment_type in {"abstract", "unknown"}:
        review_reasons.append("abstract_or_unknown")
    if _has_uncertain_proper_name_or_place(segment.text, extraction):
        review_reasons.append("uncertain_proper_name_or_place")

    return EnrichedAudioSegment(
        segment=segment,
        query=query,
        keywords=extraction.keywords,
        segment_type=segment_type,
        needs_review=bool(review_reasons),
        review_reasons=tuple(review_reasons),
        translated_query=None,
    )


def enrich_segment(segment: AudioSegment) -> EnrichedAudioSegment:
    """Add safe, deterministic metadata without changing transcript text."""

    if not isinstance(segment, AudioSegment):
        raise TypeError("segment must be an AudioSegment")
    extractor = BilingualKeywordExtractor()
    return _enrich_with_extraction(
        segment,
        extractor.extract(segment.text),
        BilingualQueryBuilder(),
    )


def enrich_segments(segments: Iterable[AudioSegment]) -> list[EnrichedAudioSegment]:
    segment_list = list(segments)
    if not all(isinstance(segment, AudioSegment) for segment in segment_list):
        raise TypeError("all segments must be AudioSegment instances")
    extractor = BilingualKeywordExtractor()
    query_builder = BilingualQueryBuilder()
    extractions = extractor.extract_many([segment.text for segment in segment_list])
    return [
        _enrich_with_extraction(segment, extraction, query_builder)
        for segment, extraction in zip(segment_list, extractions)
    ]
