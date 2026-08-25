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


def evaluate_pack_gate(
    report: PackReport,
    *,
    fail_on_overlap: bool = False,
    max_overlap_rate: float | None = None,
    threshold: float = 0.85,
) -> GateResult | None:
    if not fail_on_overlap and max_overlap_rate is None:
        return None

    max_overlap = report.max_overlap
    rules: list[GateRule] = []

    if fail_on_overlap:
        rules.append(
            GateRule(
                metric="any_overlap",
                actual=max_overlap,
                threshold=0.0,
                passed=max_overlap <= 0.0,
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
    elif fail_on_overlap:
        pass
    else:
        rules.append(
            GateRule(
                metric="max_overlap_rate",
                actual=max_overlap,
                threshold=threshold,
                passed=max_overlap <= threshold,
            )
        )

    passed = all(rule.passed for rule in rules)
    return GateResult(passed=passed, rules=rules)


def gate_exit_code(gate: GateResult | None) -> int:
    if gate is None or gate.passed:
        return EXIT_OK
    return EXIT_POLICY
