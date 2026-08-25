from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_ROLES = frozenset({"system", "retrieve", "history", "user"})


@dataclass(frozen=True)
class Segment:
    pack_id: str
    role: str
    text: str
    chunk_id: str | None = None
    line_no: int = 0

    @property
    def segment_id(self) -> str:
        if self.chunk_id is not None:
            return self.chunk_id
        return f"{self.role}:{self.line_no}"

    @property
    def byte_length(self) -> int:
        return len(self.text.encode("utf-8"))


@dataclass
class DuplicatePair:
    a: str
    b: str
    method: str
    overlap: float

    def to_dict(self) -> dict[str, Any]:
        return {"a": self.a, "b": self.b, "method": self.method, "overlap": self.overlap}


@dataclass
class CrossSegmentOverlap:
    from_role: str
    to_role: str
    overlap: float

    def to_dict(self) -> dict[str, Any]:
        return {"from": self.from_role, "to": self.to_role, "overlap": self.overlap}


@dataclass
class PackReport:
    pack_id: str
    duplicates: list[DuplicatePair] = field(default_factory=list)
    cross_segment: list[CrossSegmentOverlap] = field(default_factory=list)
    segment_count: int = 0
    retrieve_segment_count: int = 0
    duplicate_bytes: int = 0

    @property
    def exact_pairs(self) -> list[DuplicatePair]:
        return [pair for pair in self.duplicates if pair.method in {"exact", "normalized"}]

    @property
    def near_pairs(self) -> list[DuplicatePair]:
        return [pair for pair in self.duplicates if pair.method == "jaccard"]

    def _retrieve_flagged(self, pairs: list[DuplicatePair]) -> set[str]:
        return {seg for pair in pairs for seg in (pair.a, pair.b)}

    @property
    def exact_duplicate_rate(self) -> float:
        if self.retrieve_segment_count == 0:
            return 0.0
        return len(self._retrieve_flagged(self.exact_pairs)) / self.retrieve_segment_count

    @property
    def near_duplicate_rate(self) -> float:
        if self.retrieve_segment_count == 0:
            return 0.0
        return len(self._retrieve_flagged(self.near_pairs)) / self.retrieve_segment_count

    def to_audit_result(self) -> dict[str, Any]:
        exact_flagged = self._retrieve_flagged(self.exact_pairs)
        near_flagged = self._retrieve_flagged(self.near_pairs)
        return {
            "pack_id": self.pack_id,
            "segment_count": self.segment_count,
            "retrieve_segment_count": self.retrieve_segment_count,
            "exact_duplicates": {
                "pairs": len(self.exact_pairs),
                "segments_flagged": len(exact_flagged),
                "duplicate_bytes": self.duplicate_bytes if self.exact_pairs else 0,
                "duplicate_rate": round(self.exact_duplicate_rate, 6),
                "rate_denominator": "retrieve_segments",
                "evidence": [pair.to_dict() for pair in self.exact_pairs],
            },
            "near_duplicates": {
                "pairs": len(self.near_pairs),
                "segments_flagged": len(near_flagged),
                "record_rate": round(self.near_duplicate_rate, 6),
                "rate_denominator": "retrieve_segments",
                "evidence": [pair.to_dict() for pair in self.near_pairs],
            },
            "cross_segment": [item.to_dict() for item in self.cross_segment],
        }
