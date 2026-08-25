from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    workdir = cwd or ROOT
    return subprocess.run(
        [sys.executable, "-m", "rupucontext", *args],
        cwd=workdir,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(ROOT / "src"), **__import__("os").environ},
    )


@pytest.fixture
def tmp_report(tmp_path: Path):
    return tmp_path / "out.json"


def _scan_results(data: dict) -> list[dict]:
    return data["result"]["results"]


def test_scan_audit_contract(tmp_report: Path):
    result = run_cli("scan", str(FIXTURES / "dup-pack.jsonl"), "-o", str(tmp_report), "-q")
    assert result.returncode == 0
    data = json.loads(tmp_report.read_text(encoding="utf-8"))
    assert data["tool"] == "rupucontext"
    assert "family" not in data
    assert data["input"]["segments"] == 4
    assert data["method"]["exact"] == "text_exact_v1"
    pack = _scan_results(data)[0]
    assert pack["exact_duplicates"]["pairs"] == 1
    assert pack["cross_segment"] == []
    assert "gate" not in data


def test_scan_policy_twice_cross_segment(tmp_report: Path):
    result = run_cli("scan", str(FIXTURES / "policy-twice.jsonl"), "-o", str(tmp_report), "-q")
    assert result.returncode == 0
    pack = _scan_results(json.loads(tmp_report.read_text(encoding="utf-8")))[0]
    assert pack["cross_segment"] == [
        {"from": "retrieve", "to": "system", "method": "exact", "overlap": 1.0}
    ]


def test_scan_fail_on_overlap_dup_pack(tmp_report: Path):
    result = run_cli(
        "scan",
        str(FIXTURES / "dup-pack.jsonl"),
        "--fail-on-overlap",
        "-o",
        str(tmp_report),
        "-q",
    )
    assert result.returncode == 2
    data = json.loads(tmp_report.read_text(encoding="utf-8"))
    assert data["gate"]["passed"] is False
    assert data["gate"]["rules"][0]["metric"] == "overlap_pairs"


def test_scan_fail_on_overlap_policy_twice(tmp_report: Path):
    result = run_cli(
        "scan",
        str(FIXTURES / "policy-twice.jsonl"),
        "--fail-on-overlap",
        "-o",
        str(tmp_report),
        "-q",
    )
    assert result.returncode == 2


def test_scan_clean_pack(tmp_report: Path):
    result = run_cli(
        "scan",
        str(FIXTURES / "clean-pack.jsonl"),
        "--fail-on-overlap",
        "-o",
        str(tmp_report),
        "-q",
    )
    assert result.returncode == 0
    data = json.loads(tmp_report.read_text(encoding="utf-8"))
    assert data["gate"]["passed"] is True


def test_scan_usage_error(tmp_report: Path):
    result = run_cli("scan", str(FIXTURES / "missing.jsonl"), "-o", str(tmp_report), "-q")
    assert result.returncode == 1


def test_compare(tmp_report: Path):
    result = run_cli(
        "compare",
        str(FIXTURES / "corpus.jsonl"),
        str(FIXTURES / "questions.jsonl"),
        "-o",
        str(tmp_report),
        "-q",
    )
    assert result.returncode == 0
    data = json.loads(tmp_report.read_text(encoding="utf-8"))
    assert data["command"] == "compare"
    assert data["result"]["exact_overlap"]["shared_segments"] == 1


def test_report_and_gate_removed():
    result = run_cli("report", str(FIXTURES / "dup-pack.jsonl"))
    assert result.returncode != 0

    result = run_cli("gate", str(FIXTURES / "dup-pack.jsonl"))
    assert result.returncode != 0
