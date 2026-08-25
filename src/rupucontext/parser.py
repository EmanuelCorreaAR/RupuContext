from __future__ import annotations

import json
from pathlib import Path

from .models import VALID_ROLES, Segment


class ParseError(Exception):
    """Invalid JSONL input or schema violation."""


def _parse_line(raw: dict, line_no: int) -> Segment:
    if not isinstance(raw, dict):
        raise ParseError(f"line {line_no}: expected JSON object")

    pack_id = raw.get("pack_id")
    role = raw.get("role")
    text = raw.get("text")

    if not isinstance(pack_id, str) or not pack_id.strip():
        raise ParseError(f"line {line_no}: missing or invalid pack_id")
    if not isinstance(role, str) or role not in VALID_ROLES:
        raise ParseError(
            f"line {line_no}: role must be one of {sorted(VALID_ROLES)}, got {role!r}"
        )
    if not isinstance(text, str):
        raise ParseError(f"line {line_no}: missing or invalid text")

    chunk_id = raw.get("chunk_id")
    if chunk_id is not None and not isinstance(chunk_id, str):
        raise ParseError(f"line {line_no}: chunk_id must be a string when present")

    return Segment(
        pack_id=pack_id,
        role=role,
        text=text,
        chunk_id=chunk_id,
        line_no=line_no,
    )


def load_jsonl(path: Path | str) -> list[Segment]:
    path = Path(path)
    if not path.is_file():
        raise ParseError(f"file not found: {path}")

    segments: list[Segment] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ParseError(f"line {line_no}: invalid JSON — {exc.msg}") from exc
            segments.append(_parse_line(raw, line_no))

    if not segments:
        raise ParseError(f"no segments found in {path}")

    return segments


def group_by_pack(segments: list[Segment]) -> dict[str, list[Segment]]:
    packs: dict[str, list[Segment]] = {}
    for segment in segments:
        packs.setdefault(segment.pack_id, []).append(segment)
    return packs
