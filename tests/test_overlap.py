from pathlib import Path

from rupucontext.audit import build_audit
from rupucontext.brand import FAMILY, METHODOLOGY, SIBLING_TOOL, TAGLINE, TOOL
from rupucontext.overlap import analyze_pack, compare_corpus, jaccard, normalize, overlap_score
from rupucontext.parser import load_jsonl


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_family_constants():
    assert TOOL == "rupucontext"
    assert FAMILY == "rupudata"
    assert SIBLING_TOOL == "rupudata"
    assert TAGLINE == "Lint the pack. Don't pay twice."
    assert METHODOLOGY["near"] == "jaccard_char_shingles_v1"


def test_audit_envelope():
    payload = build_audit("report", {"pack_id": "x"}, notes=["test"])
    assert payload["tool"] == "rupucontext"
    assert payload["family"] == "rupudata"
    assert payload["methodology"] == METHODOLOGY


def test_normalize():
    assert normalize("  Hello   World  ") == "hello world"


def test_exact_overlap():
    method, score = overlap_score("abc", "abc")
    assert method == "exact"
    assert score == 1.0


def test_jaccard_partial():
    score = jaccard("refund policy thirty days", "refund policy sixty days")
    assert 0.0 < score < 1.0


def test_dup_pack_report():
    segments = load_jsonl(FIXTURES / "dup-pack.jsonl")
    report = analyze_pack(segments, threshold=0.85)
    assert report.pack_id == "req-001"
    assert report.segment_count == 4
    assert any(d.method == "exact" and d.overlap == 1.0 for d in report.duplicates)
    assert report.duplicate_bytes > 0
    assert report.max_overlap == 1.0


def test_clean_pack_passes_gate():
    segments = load_jsonl(FIXTURES / "clean-pack.jsonl")
    report = analyze_pack(segments, threshold=0.85)
    assert report.max_overlap < 0.85


def test_compare_corpus():
    corpus = load_jsonl(FIXTURES / "corpus.jsonl")
    questions = load_jsonl(FIXTURES / "questions.jsonl")
    hits = compare_corpus(corpus, questions, threshold=0.85)
    assert len(hits) == 1
    assert hits[0]["overlap"] == 1.0
