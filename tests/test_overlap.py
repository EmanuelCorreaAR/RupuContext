from pathlib import Path

from rupucontext.audit import build_audit
from rupucontext.brand import FAMILY, METHOD, TAGLINE, TOOL
from rupucontext.overlap import analyze_pack, compare_corpus, jaccard, normalize, overlap_score
from rupucontext.parser import load_jsonl
from rupucontext.policy import evaluate_scan_gate


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_brand_constants():
    assert TOOL == "rupucontext"
    assert FAMILY == "rupu"
    assert TAGLINE == "Lint the pack. Don't pay twice."
    assert METHOD["near"] == "jaccard_char_shingles_v1"


def test_audit_contract():
    payload = build_audit(
        "scan",
        input_meta={"path": "x.jsonl", "segments": 1, "packs": 1},
        configuration={"near_duplicate_threshold": 0.85},
        result={"pack_id": "x"},
    )
    assert payload["tool"] == "rupucontext"
    assert "family" not in payload
    assert payload["method"] == METHOD
    assert "input" in payload
    assert "configuration" in payload


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
    result = report.to_audit_result()
    assert result["pack_id"] == "req-001"
    assert result["segment_count"] == 4
    assert result["exact_duplicates"]["pairs"] == 1
    assert result["exact_duplicates"]["evidence"][0]["overlap"] == 1.0


def test_scan_gate_exact_duplicate():
    segments = load_jsonl(FIXTURES / "dup-pack.jsonl")
    report = analyze_pack(segments, threshold=0.85)
    gate = evaluate_scan_gate(report, fail_on_overlap=True)
    assert gate is not None
    assert gate.passed is False


def test_clean_pack_passes_gate():
    segments = load_jsonl(FIXTURES / "clean-pack.jsonl")
    report = analyze_pack(segments, threshold=0.85)
    gate = evaluate_scan_gate(report, fail_on_overlap=True)
    assert gate is not None
    assert gate.passed is True


def test_compare_corpus():
    corpus = load_jsonl(FIXTURES / "corpus.jsonl")
    questions = load_jsonl(FIXTURES / "questions.jsonl")
    hits = compare_corpus(corpus, questions, threshold=0.85)
    assert len(hits) == 1
    assert hits[0]["overlap"] == 1.0
