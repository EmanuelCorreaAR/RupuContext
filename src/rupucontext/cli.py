"""RupuContext CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from . import __version__
from .audit import build_audit
from .brand import DEFAULT_COMPARE_REPORT, DEFAULT_NEAR_THRESHOLD, DEFAULT_SCAN_REPORT
from .overlap import analyze_pack, compare_corpus
from .parser import ParseError, group_by_pack, load_jsonl
from .policy import (
    EXIT_ERROR,
    EXIT_POLICY,
    GateResult,
    evaluate_compare_gate,
    evaluate_scan_gate,
)
from .terminal import render_compare_summary, render_scan_report

app = typer.Typer(
    name="rupucontext",
    help=(
        "Local-first CLI for auditing LLM context packs.\n\n"
        "Policy gates (--fail-on-overlap, --max-*-rate) live on each command:\n"
        "  rupucontext scan --help\n"
        "  rupucontext compare --help"
    ),
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console(stderr=True)


def _write_json(data: object, output: Path, *, quiet: bool) -> Path:
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    output.write_text(payload, encoding="utf-8")
    if not quiet:
        console.print(f"Report written to: [bold]{output}[/bold]")
    return output


def _print_gate_failure() -> None:
    console.print(f"[red]Policy gate failed[/red]; exiting {EXIT_POLICY}.")


def _scan_gate_options(
    fail_on_overlap: bool,
    max_duplicate_rate: Optional[float],
    max_near_duplicate_rate: Optional[float],
) -> tuple[bool, Optional[float], Optional[float]]:
    if fail_on_overlap and max_duplicate_rate is None and max_near_duplicate_rate is None:
        max_duplicate_rate = 0.0
    return fail_on_overlap, max_duplicate_rate, max_near_duplicate_rate


def _compare_gate_options(
    fail_on_overlap: bool,
    max_overlap_rate: Optional[float],
) -> tuple[bool, Optional[float]]:
    if fail_on_overlap and max_overlap_rate is None:
        max_overlap_rate = 0.0
    return fail_on_overlap, max_overlap_rate


@app.command(
    "scan",
    help=(
        "Audit a context pack for duplicate and cross-segment overlap "
        "(--fail-on-overlap, --max-duplicate-rate, --max-near-duplicate-rate)."
    ),
)
def scan(
    pack: Path = typer.Argument(..., help="JSONL context pack file."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help=f"Path for the JSON report (default: ./{DEFAULT_SCAN_REPORT}).",
    ),
    near_duplicate_threshold: float = typer.Option(
        DEFAULT_NEAR_THRESHOLD,
        "--near-duplicate-threshold",
        min=0.0,
        max=1.0,
        help="Jaccard threshold for near-duplicate pairs (character shingles).",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Skip terminal summary."),
    fail_on_overlap: bool = typer.Option(
        False,
        "--fail-on-overlap",
        help=(
            "Exit 2 if any overlap is found "
            "(same as --max-duplicate-rate 0). Report is still written."
        ),
    ),
    max_duplicate_rate: Optional[float] = typer.Option(
        None,
        "--max-duplicate-rate",
        min=0.0,
        max=1.0,
        help="Exit 2 if exact duplicate_rate exceeds this threshold (CI gate).",
    ),
    max_near_duplicate_rate: Optional[float] = typer.Option(
        None,
        "--max-near-duplicate-rate",
        min=0.0,
        max=1.0,
        help="Exit 2 if near_duplicate record_rate exceeds this threshold (CI gate).",
    ),
) -> None:
    """Audit a context pack for wasted overlap inside the pack."""
    try:
        segments = load_jsonl(pack)
        packs = group_by_pack(segments)
    except ParseError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=EXIT_ERROR) from exc

    reports = [analyze_pack(pack_segments, near_duplicate_threshold) for pack_segments in packs.values()]
    fail_on_overlap, max_duplicate_rate, max_near_duplicate_rate = _scan_gate_options(
        fail_on_overlap,
        max_duplicate_rate,
        max_near_duplicate_rate,
    )
    gates = [
        evaluate_scan_gate(
            report,
            fail_on_overlap=fail_on_overlap,
            max_duplicate_rate=max_duplicate_rate,
            max_near_duplicate_rate=max_near_duplicate_rate,
        )
        for report in reports
    ]

    result = {"results": [report.to_audit_result() for report in reports]}
    if len(gates) == 1:
        gate = gates[0]
    elif any(g is not None for g in gates):
        gate = GateResult(
            passed=all(g.passed for g in gates if g is not None),
            rules=[rule for g in gates if g for rule in g.rules],
        )
    else:
        gate = None

    report_path = output or Path(DEFAULT_SCAN_REPORT)
    if not quiet:
        for report, pack_gate in zip(reports, gates):
            render_scan_report(
                report,
                gate=pack_gate if len(reports) == 1 else None,
                output_path=str(report_path),
            )
        if len(reports) > 1 and gate is not None:
            console.print(
                f"[bold]{'green' if gate.passed else 'red'}[/bold] "
                f"Policy gate: {'PASSED' if gate.passed else 'FAILED'} (all packs)"
            )

    audit = build_audit(
        "scan",
        input_meta={
            "path": str(pack),
            "segments": len(segments),
            "packs": len(packs),
        },
        configuration={
            "near_duplicate_threshold": near_duplicate_threshold,
            "fail_on_overlap": fail_on_overlap,
            "max_duplicate_rate": max_duplicate_rate,
            "max_near_duplicate_rate": max_near_duplicate_rate,
        },
        result=result,
        gate=gate,
    )
    _write_json(audit, report_path, quiet=quiet)

    if any(g is not None and not g.passed for g in gates):
        _print_gate_failure()
        raise typer.Exit(code=EXIT_POLICY)


@app.command(
    "compare",
    help=(
        "Compare corpus segments vs user questions for overlap "
        "(--fail-on-overlap, --max-overlap-rate)."
    ),
)
def compare(
    corpus: Path = typer.Argument(..., help="Corpus JSONL file."),
    questions: Path = typer.Argument(..., help="Questions JSONL file."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help=f"Path for the JSON report (default: ./{DEFAULT_COMPARE_REPORT}).",
    ),
    near_duplicate_threshold: float = typer.Option(
        DEFAULT_NEAR_THRESHOLD,
        "--near-duplicate-threshold",
        min=0.0,
        max=1.0,
        help="Jaccard threshold for near-duplicate matches (character shingles).",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Skip terminal summary."),
    fail_on_overlap: bool = typer.Option(
        False,
        "--fail-on-overlap",
        help=(
            "Exit 2 if any overlap is detected "
            "(same as --max-overlap-rate 0). Report is still written."
        ),
    ),
    max_overlap_rate: Optional[float] = typer.Option(
        None,
        "--max-overlap-rate",
        min=0.0,
        max=1.0,
        help="Exit 2 if overlap rate exceeds this threshold (CI gate). Report is still written.",
    ),
) -> None:
    """Compare corpus segments against user questions (RAG leak signal)."""
    try:
        corpus_segments = load_jsonl(corpus)
        question_segments = load_jsonl(questions)
    except ParseError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=EXIT_ERROR) from exc

    hits = compare_corpus(corpus_segments, question_segments, near_duplicate_threshold)
    hit_count = len(hits)
    overlap_rate = hit_count / len(question_segments) if question_segments else 0.0
    fail_on_overlap, max_overlap_rate = _compare_gate_options(fail_on_overlap, max_overlap_rate)
    gate = evaluate_compare_gate(
        hit_count=hit_count,
        overlap_rate=overlap_rate,
        fail_on_overlap=fail_on_overlap,
        max_overlap_rate=max_overlap_rate,
    )

    result = {
        "exact_overlap": {
            "shared_segments": hit_count,
            "rate": round(overlap_rate, 6),
        },
        "normalized_overlap": {
            "shared_segments": hit_count,
            "rate": round(overlap_rate, 6),
        },
        "matches": {
            "exact": hits,
            "normalized": hits,
        },
        "status": "OVERLAP_DETECTED" if hit_count else "NO_OVERLAP_DETECTED",
    }

    report_path = output or Path(DEFAULT_COMPARE_REPORT)
    if not quiet:
        render_compare_summary(
            str(corpus),
            str(questions),
            hit_count,
            overlap_rate,
            gate=gate,
            output_path=str(report_path),
        )

    audit = build_audit(
        "compare",
        input_meta={
            "corpus": {"path": str(corpus), "segments": len(corpus_segments)},
            "questions": {"path": str(questions), "segments": len(question_segments)},
        },
        configuration={
            "near_duplicate_threshold": near_duplicate_threshold,
            "fail_on_overlap": fail_on_overlap,
            "max_overlap_rate": max_overlap_rate,
        },
        result=result,
        gate=gate,
    )
    _write_json(audit, report_path, quiet=quiet)

    if gate is not None and not gate.passed:
        _print_gate_failure()
        raise typer.Exit(code=EXIT_POLICY)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    """RupuContext — lint the pack. Don't pay twice."""
    if version:
        typer.echo(f"rupucontext {__version__}")
        raise typer.Exit()


def cli_main() -> None:
    app()


if __name__ == "__main__":
    cli_main()
