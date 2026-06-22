"""Extract exact Vietnamese-English keyphrases without external NLP models."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


_TOKEN_PATTERN = re.compile(
    r"O\([^)]{1,8}\)|[^\W\d_]+(?:[-'’][^\W\d_]+)*",
    re.UNICODE,
)
_VI_STOPWORDS = frozenset(
    {
        "à", "ạ", "ai", "bạn", "bằng", "bị", "cả", "các", "cái", "cho",
        "chúng", "có", "của", "cũng", "đã", "đang", "đây", "để", "đó",
        "được", "hay", "hoặc", "không", "khi", "là", "lại", "lên", "mà", "mỗi",
        "một", "này", "nếu", "như", "những", "nhưng", "ở", "qua", "rất",
        "sau", "sẽ", "theo", "thì", "trên", "trong", "từ", "và", "vào",
        "với", "vì", "vậy",
    }
)
_EN_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
        "from", "if", "in", "into", "is", "it", "of", "on", "or", "that",
        "the", "then", "this", "to", "was", "were", "when", "with", "you",
    }
)
_STOPWORDS = _VI_STOPWORDS | _EN_STOPWORDS
_KEYWORD_CONNECTORS = frozenset({"vào"})
_KEYWORD_BOUNDARY_WORDS = _STOPWORDS | frozenset(
    {"bên", "đến", "dưới", "tại", "upon", "under"}
)
_EDGE_STOPWORDS = _KEYWORD_BOUNDARY_WORDS - _KEYWORD_CONNECTORS
_PHRASE_BREAK_WORDS = frozenset(
    {
        "à", "ạ", "ờ", "ừm", "nhưng", "và", "hay", "hoặc",
        "and", "but", "or", "then",
    }
)
_UNSAFE_KEYWORD_WORDS = frozenset({"không", "chưa", "chẳng", "phải"})
_DISCOURSE_STARTERS = frozenset(
    {"còn", "hãy", "rồi", "sau", "tiếp", "then", "next"}
)
_VI_COMPOUND_STARTERS = frozenset(
    {
        "bệ", "bộ", "công", "dữ", "đầu", "hệ", "kết", "kỳ", "lời",
        "môn", "phản", "thuật", "thời", "trí", "tư", "vòng",
    }
)
_MEANINGFUL_START_PHRASES = (
    "đọc hiểu",
    "phản xạ",
    "thiết kế",
    "tìm ra",
    "xác định",
)
_CLAUSE_VERBS = frozenset(
    {"có", "được", "gọi", "là", "nhận", "tạo", "trả", "sử", "dùng"}
)
_GENERIC_WORDS = frozenset(
    {
        "bài", "bước", "đầu", "điều", "giải", "giây", "hàng", "hệ", "lần",
        "người", "nơi", "phần", "thống", "thứ", "việc", "video", "thing",
        "something",
    }
)
_LOW_VALUE_PHRASES = frozenset(
    {
        "bước đầu", "bước đầu tiên", "đầu tiên", "hàng chục", "hệ thống",
        "quan trọng", "vài giây", "yêu cầu", "next step", "a few seconds",
    }
)
_CTA_MARKERS = (
    "bật thông báo",
    "đăng ký kênh",
    "follow kênh",
    "hẹn gặp lại",
    "không bỏ lỡ",
    "subscribe",
    "theo dõi kênh",
    "video tiếp theo",
)
_SENTENCE_PATTERN = re.compile(r"[^.!?;…]+(?:[.!?;…]+|$)", re.UNICODE)


@dataclass(frozen=True)
class TokenSpan:
    text: str
    start: int
    end: int

    @property
    def normalized(self) -> str:
        return self.text.casefold()


@dataclass(frozen=True)
class RankedPhrase:
    text: str
    start: int
    end: int
    score: float
    protected: bool = False

    @property
    def normalized(self) -> str:
        return " ".join(self.text.casefold().split())


@dataclass(frozen=True)
class KeywordExtraction:
    keywords: tuple[str, ...]
    ranked_phrases: tuple[RankedPhrase, ...]
    is_generic: bool


def is_call_to_action(text: str) -> bool:
    """Return whether one text span is a call to action."""

    lowered = text.casefold()
    return any(marker in lowered for marker in _CTA_MARKERS)


def _cta_ranges(text: str) -> list[tuple[int, int]]:
    return [
        (match.start(), match.end())
        for match in _SENTENCE_PATTERN.finditer(text)
        if is_call_to_action(match.group(0))
    ]


def _overlaps_ranges(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < range_end and range_start < end for range_start, range_end in ranges)


def _tokens(text: str) -> list[TokenSpan]:
    return [TokenSpan(match.group(0), match.start(), match.end()) for match in _TOKEN_PATTERN.finditer(text)]


def _is_acronym(token: str) -> bool:
    letters = "".join(character for character in token if character.isalpha())
    return 2 <= len(letters) <= 10 and letters.isascii() and letters.isupper()


def _is_title_word(token: str) -> bool:
    return len(token) >= 2 and token[0].isupper() and token[1:].islower()


def _is_english_title_token(token: str) -> bool:
    return token.isascii() and _is_title_word(token)


def _protected_phrases(text: str, tokens: list[TokenSpan]) -> list[RankedPhrase]:
    phrases: list[RankedPhrase] = []
    for index, token in enumerate(tokens):
        previous_gap = text[: token.start].rstrip()
        at_sentence_start = not previous_gap or previous_gap[-1] in ".!?…"
        if (
            _is_acronym(token.text)
            or token.text.startswith("O(")
            or (_is_english_title_token(token.text) and not at_sentence_start)
        ):
            phrases.append(RankedPhrase(token.text, token.start, token.end, 0.0, True))

    index = 0
    while index < len(tokens):
        if not (_is_title_word(tokens[index].text) or _is_acronym(tokens[index].text)):
            index += 1
            continue
        end_index = index + 1
        while end_index < len(tokens):
            previous = tokens[end_index - 1]
            current = tokens[end_index]
            gap = text[previous.end : current.start]
            if not gap.isspace() or not (
                _is_title_word(current.text) or _is_acronym(current.text)
            ):
                break
            end_index += 1
        if end_index - index >= 2:
            # Complete a mixed-case proper name such as
            # "Olympic Tin Học Quốc tế" without swallowing a conjunction.
            while end_index < len(tokens) and end_index - index < 8:
                previous = tokens[end_index - 1]
                current = tokens[end_index]
                gap = text[previous.end : current.start]
                if (
                    not gap.isspace()
                    or current.normalized in _STOPWORDS
                    or any(character in gap for character in ",.!?…;:")
                ):
                    break
                end_index += 1
            start = tokens[index].start
            end = tokens[end_index - 1].end
            phrases.append(RankedPhrase(text[start:end], start, end, 0.0, True))
        index = end_index
    return phrases


def _candidate_phrases(text: str) -> list[RankedPhrase]:
    tokens = _tokens(text)
    candidates = _protected_phrases(text, tokens)
    content_runs: list[list[TokenSpan]] = []
    run: list[TokenSpan] = []
    for token in tokens:
        if token.normalized in _PHRASE_BREAK_WORDS:
            if run:
                content_runs.append(run)
                run = []
            continue
        if run:
            gap = text[run[-1].end : token.start]
            if any(character in gap for character in ",.!?…;:"):
                content_runs.append(run)
                run = []
        run.append(token)
    if run:
        content_runs.append(run)

    for content_run in content_runs:
        for size in range(1, min(8, len(content_run)) + 1):
            for start_index in range(0, len(content_run) - size + 1):
                group = content_run[start_index : start_index + size]
                if (
                    group[0].normalized in _EDGE_STOPWORDS
                    or group[-1].normalized in _EDGE_STOPWORDS
                ):
                    continue
                if any(
                    token.normalized in _KEYWORD_BOUNDARY_WORDS
                    and token.normalized not in _KEYWORD_CONNECTORS
                    for token in group[1:-1]
                ):
                    continue
                if any(token.normalized in _UNSAFE_KEYWORD_WORDS for token in group):
                    continue
                start = group[0].start
                end = group[-1].end
                candidates.append(RankedPhrase(text[start:end], start, end, 0.0, False))

    unique: dict[tuple[int, int, str], RankedPhrase] = {}
    for candidate in candidates:
        key = (candidate.start, candidate.end, candidate.normalized)
        existing = unique.get(key)
        if existing is None or candidate.protected:
            unique[key] = candidate
    cta_ranges = _cta_ranges(text)
    return [
        candidate
        for candidate in unique.values()
        if not _overlaps_ranges(candidate.start, candidate.end, cta_ranges)
    ]


def _score_phrase(
    phrase: RankedPhrase,
    *,
    text: str,
    document_frequency: Counter[str],
    corpus_size: int,
) -> float:
    phrase_tokens = _tokens(phrase.text)
    normalized_tokens = [token.normalized for token in phrase_tokens]
    score = 0.0
    if phrase.protected:
        score += 8.0
    if any(_is_acronym(token.text) or token.text.startswith("O(") for token in phrase_tokens):
        score += 5.0
    if len(phrase_tokens) > 1:
        score += 2.2 * min(len(phrase_tokens) - 1, 3)
    else:
        score -= 2.0
    if all(token.text.isascii() for token in phrase_tokens) and len(phrase_tokens) > 1:
        score += 2.0
    score += sum(0.25 for token in phrase_tokens if len(token.text) >= 4)
    starts_compound = bool(
        normalized_tokens and normalized_tokens[0] in _VI_COMPOUND_STARTERS
    )
    starts_meaningful = any(
        phrase.normalized == starter or phrase.normalized.startswith(f"{starter} ")
        for starter in _MEANINGFUL_START_PHRASES
    )
    if (
        not phrase.protected
        and len(phrase_tokens) > 5
        and not starts_compound
        and not starts_meaningful
    ):
        score -= 2.5 * (len(phrase_tokens) - 5)
    if starts_compound and len(phrase_tokens) > 4:
        score += min(len(phrase_tokens) - 4, 3) * 0.8
    if len(normalized_tokens) == 1 and normalized_tokens[0] in _GENERIC_WORDS:
        score -= 6.0
    if all(token in _GENERIC_WORDS for token in normalized_tokens):
        score -= 4.0
    if normalized_tokens and normalized_tokens[0] in _DISCOURSE_STARTERS:
        score -= 8.0
    if starts_compound:
        score += 3.0
    if starts_meaningful:
        score += 3.0
    if any(token in _CLAUSE_VERBS for token in normalized_tokens[1:]):
        score -= 4.0
    df = document_frequency[phrase.normalized]
    score += min(math.log1p(df), 1.5)
    score += math.log((corpus_size + 1) / (df + 1)) * 0.15
    score += max(0.0, 1.0 - phrase.start / max(len(text), 1)) * 0.35
    return score


def _overlaps(left: RankedPhrase, right: RankedPhrase) -> bool:
    return left.start < right.end and right.start < left.end


def _token_overlap(left: RankedPhrase, right: RankedPhrase) -> float:
    left_tokens = {token.normalized for token in _tokens(left.text)}
    right_tokens = {token.normalized for token in _tokens(right.text)}
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))


def _select_keywords(ranked: list[RankedPhrase], limit: int = 5) -> tuple[str, ...]:
    selected: list[RankedPhrase] = []
    for candidate in ranked:
        if candidate.score <= 0:
            continue
        candidate_tokens = _tokens(candidate.text)
        if candidate.normalized in _LOW_VALUE_PHRASES:
            continue
        if (
            len(candidate_tokens) == 1
            and candidate_tokens[0].normalized in _GENERIC_WORDS
            and not candidate.protected
        ):
            continue
        if any(candidate.normalized == item.normalized for item in selected):
            continue
        if any(
            _overlaps(candidate, item)
            and (
                candidate.normalized in item.normalized
                or item.normalized in candidate.normalized
                or _token_overlap(candidate, item) >= (1 / 3)
            )
            for item in selected
        ):
            continue
        selected.append(candidate)
        if len(selected) == limit:
            break
    return tuple(candidate.text for candidate in selected)


class BilingualKeywordExtractor:
    """Corpus-aware exact keyphrase extractor for Vietnamese-English speech."""

    def extract_many(self, texts: list[str]) -> list[KeywordExtraction]:
        candidate_groups = [_candidate_phrases(text) for text in texts]
        document_frequency: Counter[str] = Counter()
        for candidates in candidate_groups:
            document_frequency.update({candidate.normalized for candidate in candidates})

        results: list[KeywordExtraction] = []
        for text, candidates in zip(texts, candidate_groups):
            ranked = sorted(
                (
                    RankedPhrase(
                        candidate.text,
                        candidate.start,
                        candidate.end,
                        _score_phrase(
                            candidate,
                            text=text,
                            document_frequency=document_frequency,
                            corpus_size=len(texts),
                        ),
                        candidate.protected,
                    )
                    for candidate in candidates
                ),
                key=lambda candidate: (
                    not candidate.protected,
                    -candidate.score,
                    candidate.start,
                    -len(candidate.text),
                ),
            )
            keywords = _select_keywords(ranked)
            results.append(
                KeywordExtraction(
                    keywords=keywords,
                    ranked_phrases=tuple(ranked),
                    is_generic=not keywords,
                )
            )
        return results

    def extract(self, text: str) -> KeywordExtraction:
        return self.extract_many([text])[0]
