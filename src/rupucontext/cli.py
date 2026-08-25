from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .audit import build_audit
from .brand import SIBLING_REPO, SIBLING_TAGLINE, SIBLING_TOOL
from .overlap import analyze_pack, compare_corpus
from .parser import ParseError, group_by_pack, load_jsonl
from .policy import EXIT_ERROR, EXIT_OK, EXIT_POLICY, GateResult, GateRule, evaluate_pack_gate, gate_exit_code
from .terminal import render_pack_report, render_scan_summary

DEFAULT_NEAR_THRESHOLD = 0.85
DEFAULT_REPORT = Path("rupucontext-report.json")


def _write_json(data: object, output: Path | None, *, quiet: bool) -> Path:
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    target = output or DEFAULT_REPORT
    target.write_text(payload, encoding="utf-8")
    if not quiet:
        print(f"Report written to: {target}", file=sys.stderr)
    return target


def _pack_gate_options(args: argparse.Namespace) -> tuple[bool, float | None]:
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

    if not args.quiet:
        render_scan_summary(str(args.pack), len(packs), len(segments))

    summary = {
        "file": str(args.pack),
        "pack_count": len(packs),
        "segment_count": len(segments),
        "packs": {
            pack_id: {
                "segment_count": len(pack_segments),
                "roles": sorted({s.role for s in pack_segments}),
            }
            for pack_id, pack_segments in sorted(packs.items())
        },
    }
    audit = build_audit(
        "scan",
        summary,
        configuration={"input": str(args.pack)},
        notes=[
            f"Sibling tool: {SIBLING_TOOL} — {SIBLING_TAGLINE}",
            f"Repository: {SIBLING_REPO}",
        ],
    )
    _write_json(audit, args.output, quiet=args.quiet)
    return EXIT_OK


def cmd_report(args: argparse.Namespace) -> int:
    try:
        segments = load_jsonl(args.pack)
        packs = group_by_pack(segments)
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    fail_on_overlap, max_overlap_rate = _pack_gate_options(args)
    reports = [analyze_pack(pack_segments, args.threshold) for pack_segments in packs.values()]
    gates = [
        evaluate_pack_gate(
            report,
            fail_on_overlap=fail_on_overlap,
            max_overlap_rate=max_overlap_rate,
        )
        for report in reports
    ]

    result: object
    gate: object = None
    if len(reports) == 1:
        result = reports[0].to_dict()
        gate = gates[0]
        if not args.quiet:
            render_pack_report(
                reports[0],
                gate=gates[0],
                output_path=str(args.output or DEFAULT_REPORT),
            )
    else:
        result = [report.to_dict() for report in reports]
        if any(g is not None for g in gates):
            gate = GateResult(
                passed=all(g.passed for g in gates if g is not None),
                rules=[rule for g in gates if g for rule in g.rules],
            )
        else:
            gate = None

    audit = build_audit(
        "report",
        result,
        gate=gate,
        configuration={
            "input": str(args.pack),
            "near_duplicate_threshold": args.threshold,
            "fail_on_overlap": fail_on_overlap,
            "max_overlap_rate": max_overlap_rate,
        },
        notes=[
            "Matching uses the same family methodology as RupuData: exact, normalized, Jaccard char shingles.",
            f"Train/eval overlap: {SIBLING_TOOL} compare · Context pack overlap: rupucontext report",
        ],
    )
    _write_json(audit, args.output, quiet=args.quiet)

    if any(g is not None and not g.passed for g in gates):
        if not args.quiet:
            print(f"Policy gate failed; exiting {EXIT_POLICY}.", file=sys.stderr)
        return EXIT_POLICY
    return EXIT_OK


def cmd_compare(args: argparse.Namespace) -> int:
    try:
        corpus = load_jsonl(args.corpus)
        questions = load_jsonl(args.questions)
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    hits = compare_corpus(corpus, questions, args.threshold)
    fail_on_overlap, max_overlap_rate = _pack_gate_options(args)
    hit_count = len(hits)
    max_overlap = max((hit["overlap"] for hit in hits), default=0.0)

    gate = None
    if fail_on_overlap or max_overlap_rate is not None:
        rules: list[GateRule] = []
        if fail_on_overlap:
            rules.append(
                GateRule(
                    metric="overlap_hits",
                    actual=float(hit_count),
                    threshold=0.0,
                    passed=hit_count == 0,
                )
            )
        if max_overlap_rate is not None:
            rules.append(
                GateRule(
                    metric="max_overlap_rate",
                    actual=max_overlap,
                    threshold=max_overlap_rate,
                    passed=max_overlap <= max_overlap_rate,
                )
            )
        gate = GateResult(passed=all(rule.passed for rule in rules), rules=rules)

    result = {
        "hits": hits,
        "hit_count": hit_count,
        "max_overlap": round(max_overlap, 4),
        "status": "OVERLAP_DETECTED" if hit_count else "NO_OVERLAP_DETECTED",
    }
    audit = build_audit(
        "compare",
        result,
        gate=gate,
        configuration={
            "corpus": str(args.corpus),
            "questions": str(args.questions),
            "near_duplicate_threshold": args.threshold,
            "fail_on_overlap": fail_on_overlap,
            "max_overlap_rate": max_overlap_rate,
        },
        notes=[
            f"Corpus vs user-message overlap — sibling to {SIBLING_TOOL} compare train.jsonl eval.jsonl.",
        ],
    )
    _write_json(audit, args.output, quiet=args.quiet)
    return gate_exit_code(gate)


def cmd_gate(args: argparse.Namespace) -> int:
    args.fail_on_overlap = False
    args.max_overlap_rate = args.threshold
    args.quiet = getattr(args, "quiet", False)
    return cmd_report(args)


def _add_gate_flags(parser: argparse.ArgumentParser) -> None:
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
        help="Exit 2 if max overlap exceeds this threshold (CI gate). Report is still written.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rupucontext",
        description=(
            "RupuContext — lint the pack before the LLM call.\n\n"
            "Part of the RupuData family (rupudata = path of the data · "
            "rupucontext = path of the context).\n\n"
            "Policy gates (--fail-on-overlap, --max-overlap-rate) exit 2 when "
            "thresholds are exceeded. Exit 1 is reserved for errors."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Parse, validate, and summarize a context pack")
    scan.add_argument("pack", type=Path, help="JSONL context pack file")
    scan.add_argument("-o", "--output", type=Path, help=f"JSON audit report (default: {DEFAULT_REPORT})")
    scan.add_argument("-q", "--quiet", action="store_true", help="Skip terminal summary")
    scan.set_defaults(func=cmd_scan)

    compare = sub.add_parser(
        "compare",
        help="Overlap between corpus segments and user questions (like rupudata compare)",
    )
    compare.add_argument("corpus", type=Path, help="Corpus JSONL file")
    compare.add_argument("questions", type=Path, help="Questions JSONL file")
    compare.add_argument("-o", "--output", type=Path, help=f"JSON audit report (default: {DEFAULT_REPORT})")
    compare.add_argument(
        "--threshold",
        "--near-duplicate-threshold",
        type=float,
        default=DEFAULT_NEAR_THRESHOLD,
        dest="threshold",
        help="Jaccard threshold for near-duplicate pairs (default: 0.85)",
    )
    compare.add_argument("-q", "--quiet", action="store_true", help="Skip terminal output")
    _add_gate_flags(compare)
    compare.set_defaults(func=cmd_compare)

    report = sub.add_parser("report", help="Audit a context pack for duplicate and cross-segment overlap")
    report.add_argument("pack", type=Path, help="JSONL context pack file")
    report.add_argument("-o", "--output", type=Path, help=f"JSON audit report (default: {DEFAULT_REPORT})")
    report.add_argument(
        "--threshold",
        "--near-duplicate-threshold",
        type=float,
        default=DEFAULT_NEAR_THRESHOLD,
        dest="threshold",
        help="Jaccard threshold for near-duplicate pairs (default: 0.85)",
    )
    report.add_argument("-q", "--quiet", action="store_true", help="Skip terminal summary")
    _add_gate_flags(report)
    report.set_defaults(func=cmd_report)

    gate = sub.add_parser(
        "gate",
        help="CI shortcut for report --max-overlap-rate THRESHOLD (exit 2 on failure)",
    )
    gate.add_argument("pack", type=Path, help="JSONL context pack file")
    gate.add_argument("-o", "--output", type=Path, help=f"JSON audit report (default: {DEFAULT_REPORT})")
    gate.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_NEAR_THRESHOLD,
        help="Maximum allowed overlap ratio (default: 0.85)",
    )
    gate.add_argument("-q", "--quiet", action="store_true", help="Skip terminal summary")
    gate.set_defaults(func=cmd_gate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "quiet"):
        args.quiet = False
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
