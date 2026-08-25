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
    duplicate_bytes: int = 0

    @property
    def max_overlap(self) -> float:
        values = [d.overlap for d in self.duplicates] + [c.overlap for c in self.cross_segment]
        return max(values) if values else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "duplicates": [d.to_dict() for d in self.duplicates],
            "cross_segment": [c.to_dict() for c in self.cross_segment],
            "summary": {
                "segment_count": self.segment_count,
                "duplicate_bytes": self.duplicate_bytes,
            },
        }
