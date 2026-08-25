from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .audit import build_audit
from .brand import (
    DEFAULT_COMPARE_REPORT,
    DEFAULT_NEAR_THRESHOLD,
    DEFAULT_SCAN_REPORT,
)
from .overlap import analyze_pack, compare_corpus
from .parser import ParseError, group_by_pack, load_jsonl
from .policy import (
    EXIT_ERROR,
    EXIT_POLICY,
    evaluate_compare_gate,
    evaluate_scan_gate,
    gate_exit_code,
)
from .terminal import render_compare_summary, render_scan_report


def _write_json(data: object, output: Path, *, quiet: bool) -> Path:
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    output.write_text(payload, encoding="utf-8")
    if not quiet:
        print(f"Report written to: {output}", file=sys.stderr)
    return output


def _scan_gate_options(args: argparse.Namespace) -> tuple[bool, float | None, float | None]:
    fail_on_overlap = getattr(args, "fail_on_overlap", False)
    max_duplicate_rate = getattr(args, "max_duplicate_rate", None)
    max_near_duplicate_rate = getattr(args, "max_near_duplicate_rate", None)
    if fail_on_overlap and max_duplicate_rate is None and max_near_duplicate_rate is None:
        max_duplicate_rate = 0.0
    return fail_on_overlap, max_duplicate_rate, max_near_duplicate_rate


def _compare_gate_options(args: argparse.Namespace) -> tuple[bool, float | None]:
    fail_on_overlap = getattr(args, "fail_on_overlap", False)
    max_overlap_rate = getattr(args, "max_overlap_rate", None)
    if fail_on_overlap and max_overlap_rate is None:
        max_overlap_rate = 0.0
    return fail_on_overlap, max_overlap_rate


def cmd_scan(args: argparse.Namespace) -> int:
    try:
        segments = load_jsonl(args.pack)
        packs = group_by_pack(segments)
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    reports = [analyze_pack(pack_segments, args.near_duplicate_threshold) for pack_segments in packs.values()]
    fail_on_overlap, max_duplicate_rate, max_near_duplicate_rate = _scan_gate_options(args)
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
        from .policy import GateResult

        gate = GateResult(
            passed=all(g.passed for g in gates if g is not None),
            rules=[rule for g in gates if g for rule in g.rules],
        )
    else:
        gate = None

    if not args.quiet:
        for report, pack_gate in zip(reports, gates):
            render_scan_report(
                report,
                gate=pack_gate if len(reports) == 1 else None,
                output_path=str(args.output or DEFAULT_SCAN_REPORT),
            )
        if len(reports) > 1 and gate is not None:
            print(
                f"Policy gate: {'PASSED' if gate.passed else 'FAILED'} (all packs)",
                file=sys.stderr,
            )

    audit = build_audit(
        "scan",
        input_meta={
            "path": str(args.pack),
            "segments": len(segments),
            "packs": len(packs),
        },
        configuration={
            "near_duplicate_threshold": args.near_duplicate_threshold,
            "fail_on_overlap": fail_on_overlap,
            "max_duplicate_rate": max_duplicate_rate,
            "max_near_duplicate_rate": max_near_duplicate_rate,
        },
        result=result,
        gate=gate,
    )
    _write_json(audit, args.output or Path(DEFAULT_SCAN_REPORT), quiet=args.quiet)

    if any(g is not None and not g.passed for g in gates):
        if not args.quiet:
            print(f"Policy gate failed; exiting {EXIT_POLICY}.", file=sys.stderr)
        return EXIT_POLICY
    return gate_exit_code(gate)


def cmd_compare(args: argparse.Namespace) -> int:
    try:
        corpus = load_jsonl(args.corpus)
        questions = load_jsonl(args.questions)
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    hits = compare_corpus(corpus, questions, args.near_duplicate_threshold)
    hit_count = len(hits)
    overlap_rate = hit_count / len(questions) if questions else 0.0
    fail_on_overlap, max_overlap_rate = _compare_gate_options(args)
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

    if not args.quiet:
        render_compare_summary(
            str(args.corpus),
            str(args.questions),
            hit_count,
            overlap_rate,
            gate=gate,
            output_path=str(args.output or DEFAULT_COMPARE_REPORT),
        )

    audit = build_audit(
        "compare",
        input_meta={
            "corpus": {"path": str(args.corpus), "segments": len(corpus)},
            "questions": {"path": str(args.questions), "segments": len(questions)},
        },
        configuration={
            "near_duplicate_threshold": args.near_duplicate_threshold,
            "fail_on_overlap": fail_on_overlap,
            "max_overlap_rate": max_overlap_rate,
        },
        result=result,
        gate=gate,
    )
    _write_json(audit, args.output or Path(DEFAULT_COMPARE_REPORT), quiet=args.quiet)
    return gate_exit_code(gate)


def _add_scan_gate_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--fail-on-overlap",
        action="store_true",
        help="Exit 2 if any duplicate pair is found (same as --max-duplicate-rate 0). Report is still written.",
    )
    parser.add_argument(
        "--max-duplicate-rate",
        type=float,
        default=None,
        metavar="RATE",
        help="Exit 2 if exact duplicate_rate exceeds this threshold (CI gate).",
    )
    parser.add_argument(
        "--max-near-duplicate-rate",
        type=float,
        default=None,
        metavar="RATE",
        help="Exit 2 if near_duplicate record_rate exceeds this threshold (CI gate).",
    )


def _add_compare_gate_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--fail-on-overlap",
        action="store_true",
        help="Exit 2 if any overlap is detected (same as --max-overlap-rate 0). Report is still written.",
    )
    parser.add_argument(
        "--max-overlap-rate",
        type=float,
        default=None,
        metavar="RATE",
        help="Exit 2 if overlap rate exceeds this threshold (CI gate). Report is still written.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rupucontext",
        description=(
            "RupuContext — lint the pack before the LLM call.\n\n"
            "Part of the Rupu family.\n"
            "Policy gate flags exit 2 when thresholds are exceeded. Exit 1 is for errors."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Audit a context pack for duplicate and cross-segment overlap")
    scan.add_argument("pack", type=Path, help="JSONL context pack file")
    scan.add_argument(
        "-o",
        "--output",
        type=Path,
        help=f"JSON audit report (default: {DEFAULT_SCAN_REPORT})",
    )
    scan.add_argument(
        "--near-duplicate-threshold",
        type=float,
        default=DEFAULT_NEAR_THRESHOLD,
        help="Jaccard threshold for near-duplicate pairs (default: 0.85)",
    )
    scan.add_argument("-q", "--quiet", action="store_true", help="Skip terminal summary")
    _add_scan_gate_flags(scan)
    scan.set_defaults(func=cmd_scan)

    compare = sub.add_parser(
        "compare",
        help="Overlap between corpus segments and user questions (RAG leak signal)",
    )
    compare.add_argument("corpus", type=Path, help="Corpus JSONL file")
    compare.add_argument("questions", type=Path, help="Questions JSONL file")
    compare.add_argument(
        "-o",
        "--output",
        type=Path,
        help=f"JSON audit report (default: {DEFAULT_COMPARE_REPORT})",
    )
    compare.add_argument(
        "--near-duplicate-threshold",
        type=float,
        default=DEFAULT_NEAR_THRESHOLD,
        help="Jaccard threshold for near-duplicate matches (default: 0.85)",
    )
    compare.add_argument("-q", "--quiet", action="store_true", help="Skip terminal summary")
    _add_compare_gate_flags(compare)
    compare.set_defaults(func=cmd_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "quiet"):
        args.quiet = False
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
