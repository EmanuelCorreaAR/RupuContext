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


def render_scan_summary(
    path: str,
    pack_count: int,
    segment_count: int,
    *,
    console: Console | None = None,
) -> None:
    console = console or Console(stderr=True)
    _header(console)
    console.print(f"\nScanning pack: [bold]{path}[/bold]\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Packs", f"{pack_count:,}")
    table.add_row("Segments", f"{segment_count:,}")
    console.print("[bold cyan]Context pack[/bold cyan]")
    console.print("─" * 30)
    console.print(table)
    console.print()


def render_pack_report(
    report: PackReport,
    *,
    gate: GateResult | None = None,
    output_path: str | None = None,
    console: Console | None = None,
) -> None:
    console = console or Console(stderr=True)
    _header(console)
    console.print(f"\nPack audit: [bold]{report.pack_id}[/bold]\n")

    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Segments", f"{report.segment_count:,}")
    summary.add_row("Duplicate pairs", f"{len(report.duplicates):,}")
    summary.add_row("Cross-segment overlaps", f"{len(report.cross_segment):,}")
    summary.add_row("Duplicate bytes", f"{report.duplicate_bytes:,}")
    summary.add_row("Max overlap", f"{report.max_overlap:.4f}")
    console.print("[bold cyan]Overlap[/bold cyan]")
    console.print("─" * 30)
    console.print(summary)
    console.print()

    if report.duplicates:
        ev = Table(show_header=True, box=None, padding=(0, 2))
        ev.add_column("a")
        ev.add_column("b")
        ev.add_column("method")
        ev.add_column("overlap")
        for item in report.duplicates[:5]:
            ev.add_row(item.a, item.b, item.method, f"{item.overlap:.4f}")
        console.print("[bold cyan]Evidence (sample)[/bold cyan]")
        console.print("─" * 30)
        console.print(ev)
        console.print()

    if gate is not None:
        status = "PASSED" if gate.passed else "FAILED"
        style = "green" if gate.passed else "red"
        gate_table = Table(show_header=True, box=None, padding=(0, 2))
        gate_table.add_column("metric")
        gate_table.add_column("actual")
        gate_table.add_column("threshold")
        gate_table.add_column("ok")
        for rule in gate.rules:
            gate_table.add_row(
                rule.metric,
                f"{rule.actual:.6g}",
                f"{rule.threshold:.6g}",
                "yes" if rule.passed else "no",
            )
        console.print(f"[bold {style}]Policy gate: {status}[/bold {style}]")
        console.print("─" * 30)
        console.print(gate_table)
        console.print()

    if output_path:
        console.print(f"Report written to:\n[bold]{output_path}[/bold]\n")
