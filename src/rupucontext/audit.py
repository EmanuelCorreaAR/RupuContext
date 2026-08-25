from __future__ import annotations

from typing import Any

from . import __version__
from .brand import METHOD, TOOL
from .policy import GateResult


def build_audit(
    command: str,
    *,
    input_meta: dict[str, Any],
    configuration: dict[str, Any],
    result: Any,
    gate: GateResult | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tool": TOOL,
        "version": __version__,
        "command": command,
        "input": input_meta,
        "configuration": configuration,
        "method": METHOD,
        "result": result,
    }
    if gate is not None:
        payload["gate"] = gate.to_dict()
    if notes:
        payload["notes"] = notes
    return payload
