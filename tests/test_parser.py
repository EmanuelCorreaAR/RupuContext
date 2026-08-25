from pathlib import Path

import pytest

from rupucontext.parser import ParseError, group_by_pack, load_jsonl


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_load_dup_pack():
    segments = load_jsonl(FIXTURES / "dup-pack.jsonl")
    assert len(segments) == 4
    packs = group_by_pack(segments)
    assert list(packs) == ["req-001"]


def test_invalid_role():
    bad = FIXTURES.parent / "tests" / "_bad_role.jsonl"
    bad.write_text('{"pack_id": "x", "role": "tool", "text": "hi"}\n', encoding="utf-8")
    try:
        with pytest.raises(ParseError, match="role must be"):
            load_jsonl(bad)
    finally:
        bad.unlink(missing_ok=True)


def test_empty_file(tmp_path: Path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n", encoding="utf-8")
    with pytest.raises(ParseError, match="no segments"):
        load_jsonl(empty)
