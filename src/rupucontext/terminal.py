from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .brand import TAGLINE, TOOL
from .models import PackReport
from .policy import GateResult


def _header(console: Console) -> None:
    console.print(
        Panel.fit(
            f"[bold]{TOOL}[/bold] v{__version__}\n[dim]{TAGLINE}[/dim]",
            border_style="cyan",
        )
    )


def _render_gate(gate: GateResult | None, console: Console) -> None:
    if gate is None:
        return
    status = "PASSED" if gate.passed else "FAILED"
    style = "green" if gate.passed else "red"
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("metric")
    table.add_column("actual")
    table.add_column("threshold")
    table.add_column("ok")
    for rule in gate.rules:
        table.add_row(
            rule.metric,
            f"{rule.actual:.6g}",
            f"{rule.threshold:.6g}",
            "yes" if rule.passed else "no",
        )
    console.print(f"[bold {style}]Policy gate: {status}[/bold {style}]")
    console.print("─" * 30)
    console.print(table)
    console.print()


def render_scan_report(
    report: PackReport,
    *,
    gate: GateResult | None = None,
    output_path: str | None = None,
    console: Console | None = None,
) -> None:
    console = console or Console(stderr=True)
    _header(console)
    console.print(f"\nScanning pack: [bold]{report.pack_id}[/bold]\n")

    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Segments", f"{report.segment_count:,}")
    summary.add_row("Exact duplicate pairs", f"{len(report.exact_pairs):,}")
    summary.add_row("Near-duplicate pairs", f"{len(report.near_pairs):,}")
    summary.add_row("Duplicate bytes", f"{report.duplicate_bytes:,}")
    console.print("[bold cyan]Duplicates[/bold cyan]")
    console.print("─" * 30)
    console.print(summary)
    console.print()

    if report.exact_pairs:
        ev = Table(show_header=True, box=None, padding=(0, 2))
        ev.add_column("a")
        ev.add_column("b")
        ev.add_column("method")
        ev.add_column("overlap")
        for item in report.exact_pairs[:5]:
            ev.add_row(item.a, item.b, item.method, f"{item.overlap:.4f}")
        console.print("[bold cyan]Evidence (sample)[/bold cyan]")
        console.print("─" * 30)
        console.print(ev)
        console.print()

    _render_gate(gate, console)
    if output_path:
        console.print(f"Report written to:\n[bold]{output_path}[/bold]\n")


def render_compare_summary(
    corpus_path: str,
    questions_path: str,
    hit_count: int,
    overlap_rate: float,
    *,
    gate: GateResult | None = None,
    output_path: str | None = None,
    console: Console | None = None,
) -> None:
    console = console or Console(stderr=True)
    _header(console)
    console.print(
        f"\nCompare: [bold]{corpus_path}[/bold] vs [bold]{questions_path}[/bold]\n"
    )

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Overlap hits", f"{hit_count:,}")
    table.add_row("Overlap rate", f"{overlap_rate:.6g}")
    table.add_row("Status", "OVERLAP_DETECTED" if hit_count else "NO_OVERLAP_DETECTED")
    console.print("[bold cyan]Overlap[/bold cyan]")
    console.print("─" * 30)
    console.print(table)
    console.print()

    _render_gate(gate, console)
    if output_path:
        console.print(f"Report written to:\n[bold]{output_path}[/bold]\n")
