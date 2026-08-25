from __future__ import annotations

from dataclasses import dataclass

from .models import PackReport

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_POLICY = 2


@dataclass(frozen=True)
class GateRule:
    metric: str
    actual: float
    threshold: float
    passed: bool


@dataclass
class GateResult:
    passed: bool
    rules: list[GateRule]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "rules": [
                {
                    "metric": rule.metric,
                    "actual": rule.actual,
                    "threshold": rule.threshold,
                    "passed": rule.passed,
                }
                for rule in self.rules
            ],
        }


def evaluate_scan_gate(
    report: PackReport,
    *,
    fail_on_overlap: bool = False,
    max_duplicate_rate: float | None = None,
    max_near_duplicate_rate: float | None = None,
) -> GateResult | None:
    if not fail_on_overlap and max_duplicate_rate is None and max_near_duplicate_rate is None:
        return None

    rules: list[GateRule] = []
    overlap_signals = len(report.duplicates) + len(report.cross_segment)

    if fail_on_overlap:
        rules.append(
            GateRule(
                metric="overlap_pairs",
                actual=float(overlap_signals),
                threshold=0.0,
                passed=overlap_signals == 0,
            )
        )

    if max_duplicate_rate is not None:
        exact_rate = report.exact_duplicate_rate
        rules.append(
            GateRule(
                metric="duplicate_rate",
                actual=round(exact_rate, 6),
                threshold=max_duplicate_rate,
                passed=exact_rate <= max_duplicate_rate,
            )
        )

    if max_near_duplicate_rate is not None:
        rules.append(
            GateRule(
                metric="near_duplicate_rate",
                actual=round(report.near_duplicate_rate, 6),
                threshold=max_near_duplicate_rate,
                passed=report.near_duplicate_rate <= max_near_duplicate_rate,
            )
        )

    return GateResult(passed=all(rule.passed for rule in rules), rules=rules)


def evaluate_compare_gate(
    *,
    hit_count: int,
    overlap_rate: float,
    fail_on_overlap: bool = False,
    max_overlap_rate: float | None = None,
) -> GateResult | None:
    if not fail_on_overlap and max_overlap_rate is None:
        return None

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
        rules.append(
            GateRule(
                metric="overlap_rate",
                actual=round(overlap_rate, 6),
                threshold=0.0,
                passed=overlap_rate <= 0.0,
            )
        )

    if max_overlap_rate is not None:
        rules.append(
            GateRule(
                metric="overlap_rate",
                actual=round(overlap_rate, 6),
                threshold=max_overlap_rate,
                passed=overlap_rate <= max_overlap_rate,
            )
        )

    return GateResult(passed=all(rule.passed for rule in rules), rules=rules)


def gate_exit_code(gate: GateResult | None) -> int:
    if gate is None or gate.passed:
        return EXIT_OK
    return EXIT_POLICY
