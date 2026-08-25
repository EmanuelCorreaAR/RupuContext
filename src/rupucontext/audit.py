from __future__ import annotations

from typing import Any

from . import __version__
from .brand import FAMILY, METHODOLOGY, TAGLINE, TOOL
from .policy import GateResult


def build_audit(
    command: str,
    result: Any,
    *,
    gate: GateResult | None = None,
    configuration: dict[str, Any] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tool": TOOL,
        "version": __version__,
        "family": FAMILY,
        "tagline": TAGLINE,
        "command": command,
        "methodology": METHODOLOGY,
        "result": result,
    }
    if configuration:
        payload["configuration"] = configuration
    if gate is not None:
        payload["gate"] = gate.to_dict()
    if notes:
        payload["notes"] = notes
    return payload
