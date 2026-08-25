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


def test_scan(tmp_report: Path):
    result = run_cli("scan", str(FIXTURES / "dup-pack.jsonl"), "-o", str(tmp_report), "-q")
    assert result.returncode == 0
    data = json.loads(tmp_report.read_text(encoding="utf-8"))
    assert data["tool"] == "rupucontext"
    assert data["family"] == "rupudata"
    assert data["result"]["segment_count"] == 4


def test_report_family_envelope(tmp_report: Path):
    result = run_cli("report", str(FIXTURES / "dup-pack.jsonl"), "-o", str(tmp_report), "-q")
    assert result.returncode == 0
    data = json.loads(tmp_report.read_text(encoding="utf-8"))
    assert data["family"] == "rupudata"
    assert data["methodology"]["exact"] == "text_exact_v1"
    assert data["result"]["pack_id"] == "req-001"
    assert data["result"]["duplicates"]


def test_report_gate_fails(tmp_report: Path):
    result = run_cli(
        "report",
        str(FIXTURES / "dup-pack.jsonl"),
        "--max-overlap-rate",
        "0.85",
        "-o",
        str(tmp_report),
        "-q",
    )
    assert result.returncode == 2
    data = json.loads(tmp_report.read_text(encoding="utf-8"))
    assert data["gate"]["passed"] is False


def test_gate_fails_on_duplicates(tmp_report: Path):
    result = run_cli(
        "gate",
        str(FIXTURES / "dup-pack.jsonl"),
        "--threshold",
        "0.85",
        "-o",
        str(tmp_report),
        "-q",
    )
    assert result.returncode == 2


def test_gate_passes_clean_pack(tmp_report: Path):
    result = run_cli(
        "gate",
        str(FIXTURES / "clean-pack.jsonl"),
        "--threshold",
        "0.85",
        "-o",
        str(tmp_report),
        "-q",
    )
    assert result.returncode == 0
    data = json.loads(tmp_report.read_text(encoding="utf-8"))
    assert data["gate"]["passed"] is True


def test_gate_usage_error(tmp_report: Path):
    result = run_cli("gate", str(FIXTURES / "missing.jsonl"), "-o", str(tmp_report), "-q")
    assert result.returncode == 1
