from __future__ import annotations

import re
from itertools import combinations

from .models import CrossSegmentOverlap, DuplicatePair, PackReport, Segment

WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text.strip().casefold())


def _shingles(text: str, k: int = 5) -> set[str]:
    normalized = normalize(text)
    if len(normalized) < k:
        return {normalized} if normalized else set()
    return {normalized[i : i + k] for i in range(len(normalized) - k + 1)}


def jaccard(a: str, b: str, k: int = 5) -> float:
    sa, sb = _shingles(a, k), _shingles(b, k)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def overlap_score(a: str, b: str) -> tuple[str, float]:
    if a == b:
        return "exact", 1.0
    if normalize(a) == normalize(b):
        return "normalized", 1.0
    score = jaccard(a, b)
    return "jaccard", score


def _duplicate_bytes(a: Segment, b: Segment) -> int:
    if a.text == b.text:
        return min(a.byte_length, b.byte_length)
    shorter, longer = sorted((a.text, b.text), key=len)
    if shorter and shorter in longer:
        return len(shorter.encode("utf-8"))
    return 0


def find_duplicates(segments: list[Segment], threshold: float) -> tuple[list[DuplicatePair], int]:
    pairs: list[DuplicatePair] = []
    duplicate_bytes = 0

    for left, right in combinations(segments, 2):
        method, score = overlap_score(left.text, right.text)
        if score < threshold:
            continue
        pairs.append(
            DuplicatePair(
                a=left.segment_id,
                b=right.segment_id,
                method=method,
                overlap=round(score, 4),
            )
        )
        duplicate_bytes += _duplicate_bytes(left, right)

    pairs.sort(key=lambda p: (-p.overlap, p.a, p.b))
    return pairs, duplicate_bytes


def find_cross_segment(segments: list[Segment], threshold: float) -> list[CrossSegmentOverlap]:
    by_role: dict[str, list[Segment]] = {}
    for segment in segments:
        by_role.setdefault(segment.role, []).append(segment)

    roles = sorted(by_role)
    results: list[CrossSegmentOverlap] = []

    for from_role, to_role in combinations(roles, 2):
        best = 0.0
        for left in by_role[from_role]:
            for right in by_role[to_role]:
                _, score = overlap_score(left.text, right.text)
                best = max(best, score)
        if best >= threshold:
            results.append(
                CrossSegmentOverlap(
                    from_role=from_role,
                    to_role=to_role,
                    overlap=round(best, 4),
                )
            )

    results.sort(key=lambda c: (-c.overlap, c.from_role, c.to_role))
    return results


def analyze_pack(segments: list[Segment], threshold: float = 0.85) -> PackReport:
    duplicates, duplicate_bytes = find_duplicates(segments, threshold)
    cross_segment = find_cross_segment(segments, threshold)
    pack_id = segments[0].pack_id if segments else "unknown"
    return PackReport(
        pack_id=pack_id,
        duplicates=duplicates,
        cross_segment=cross_segment,
        segment_count=len(segments),
        duplicate_bytes=duplicate_bytes,
    )


def compare_corpus(corpus: list[Segment], questions: list[Segment], threshold: float) -> list[dict]:
    corpus_texts = [s.text for s in corpus]
    hits: list[dict] = []

    for question in questions:
        best_method = ""
        best_score = 0.0
        best_corpus_idx = -1
        for idx, text in enumerate(corpus_texts):
            method, score = overlap_score(question.text, text)
            if score > best_score:
                best_method, best_score, best_corpus_idx = method, score, idx

        if best_score >= threshold:
            hits.append(
                {
                    "question": question.segment_id,
                    "corpus": corpus[best_corpus_idx].segment_id,
                    "method": best_method,
                    "overlap": round(best_score, 4),
                }
            )

    hits.sort(key=lambda h: (-h["overlap"], h["question"]))
    return hits
