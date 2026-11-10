from __future__ import annotations

import ctypes
import os
import sys
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Any

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.text import Text

from bio_annotation.pipeline.progress import (
    ProgressEvent,
    ProgressReporter,
    describe,
    should_report_progress,
)


THEME_WIDTH = 100
BIOANNOHUB_THEME = Theme(
    {
        "brand": "bold cyan",
        "accent": "bold magenta",
        "muted": "cyan",
        "panel.border": "bright_cyan",
        "panel.title": "bold cyan",
        "table.header": "bold cyan",
        "table.title": "bold magenta",
        "field": "bold cyan",
        "ok": "bold green",
        "warning": "bold yellow",
        "path": "bright_blue",
    }
)


@contextmanager
def annotator_spinner() -> Iterator[ProgressReporter]:
    terminal = os.fdopen(os.dup(1), "w", encoding="utf-8", errors="replace")
    console = Console(file=terminal, theme=BIOANNOHUB_THEME)
    status = console.status("Running annotation...", spinner="dots")
    status.start()
    try:
        with _native_output_above(console):

            def report(event: ProgressEvent) -> None:
                if not should_report_progress(event):
                    return
                if event.event == "start":
                    status.update(Text(describe(event), style="muted"))
                else:
                    # Printed above the spinner so outcomes survive the run.
                    style = "warning" if event.event == "error" else "ok"
                    console.print(Text(describe(event), style=style))

            yield report
    finally:
        status.stop()


@contextmanager
def _native_output_above(console: Console) -> Iterator[None]:
    sys.stdout.flush()
    sys.stderr.flush()
    read_fd, write_fd = os.pipe()
    saved_fds = [os.dup(1), os.dup(2)]
    os.dup2(write_fd, 1)
    os.dup2(write_fd, 2)
    os.close(write_fd)

    def forward() -> None:
        with os.fdopen(read_fd, encoding="utf-8", errors="replace") as captured:
            for line in captured:
                console.print(Text(line.rstrip("\n"), style="muted"))

    reader = threading.Thread(target=forward, daemon=True)
    reader.start()
    try:
        yield
    finally:
        _flush_c_stdio()
        sys.stdout.flush()
        sys.stderr.flush()
        for fd, saved in zip((1, 2), saved_fds):
            os.dup2(saved, fd)
            os.close(saved)
        reader.join(timeout=1)


def _flush_c_stdio() -> None:
    try:
        ctypes.CDLL(None).fflush(None)
    except (OSError, AttributeError, TypeError):
        pass


def render_lines(renderable: Any) -> list[str]:
    """Render a Rich object to plain terminal lines for the existing output_fn API."""

    buffer = StringIO()
    console = Console(
        width=THEME_WIDTH,
        color_system="truecolor",
        force_terminal=True,
        file=buffer,
        theme=BIOANNOHUB_THEME,
    )
    console.print(renderable)
    return buffer.getvalue().rstrip("\n").splitlines()


def emit(output_fn, lines: Iterable[str]) -> None:
    for line in lines:
        output_fn(line)


def banner_lines() -> list[str]:
    title = Text("BioAnnoHub", justify="center", style="brand")
    subtitle = Text("Biomedical entity annotation workspace", justify="center", style="muted")
    body = Text.assemble(title, "\n", subtitle)
    return render_lines(
        Panel(
            Align.center(body),
            box=box.ROUNDED,
            border_style="panel.border",
            padding=(1, 2),
        )
    )


def help_lines() -> list[str]:
    return render_lines(
        Panel(
            Text.assemble(
                ("Choose input, filter annotators by domain and supported task, then choose annotators and entity filters.\n", "muted"),
                ("Type 'restart' or 'exit' at any prompt; press Enter at the final prompt to run.\n", "muted"),
                ("Each completed run writes ", "muted"),
                ("config", "field"),
                (", ", "muted"),
                ("JSON", "field"),
                (", ", "muted"),
                ("TSV review tables", "field"),
                (", and a ", "muted"),
                ("manifest", "field"),
                (". Annotations retain their source; entity filters apply after execution to combined results.", "muted"),
            ),
            title="Workflow",
            title_align="left",
            border_style="panel.border",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def choice_lines(title: str, choices: tuple[tuple[str, str], ...], *, default_indexes: list[int] | None = None) -> list[str]:
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_header=True,
        header_style="table.header",
        title_style="table.title",
        border_style="panel.border",
        pad_edge=True,
    )
    defaults = set(default_indexes or [])
    table.add_column("#", justify="right", no_wrap=True, style="accent")
    table.add_column("Option")
    if defaults:
        table.add_column("Default", justify="center", no_wrap=True, style="ok")
    for index, (_, label) in enumerate(choices, start=1):
        row = [str(index), label]
        if defaults:
            row.append("default" if index in defaults else "")
        table.add_row(*row)
    return render_lines(table)


def annotator_capability_lines(
    rows: Iterable[tuple[str, str, str, str, str]],
) -> list[str]:
    table = Table(
        title="Selected annotator capabilities",
        box=box.ROUNDED,
        show_lines=True,
        show_header=True,
        header_style="table.header",
        title_style="table.title",
        border_style="panel.border",
        pad_edge=True,
    )
    for column in ("Annotator", "Domains", "Inputs", "Tasks", "Entity types"):
        table.add_column(column)
    for row in rows:
        table.add_row(*row)
    return render_lines(table)


def warning_lines(title: str, messages: Iterable[str]) -> list[str]:
    return render_lines(
        Panel(
            "\n".join(messages),
            title=title,
            title_align="left",
            border_style="warning",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def run_plan_lines(
    *,
    input_mode: str,
    domain: str = "Biomedical",
    task: str = "NER-capable",
    annotators: list[str],
    entity_types: list[str],
) -> list[str]:
    table = Table(
        title="Run plan",
        box=box.ROUNDED,
        show_header=False,
        title_style="table.title",
        border_style="panel.border",
    )
    table.add_column("Field", style="field")
    table.add_column("Value")
    table.add_row("Input", input_mode)
    table.add_row("Domain filter", domain)
    table.add_row("Task filter", task)
    table.add_row("Annotators", ", ".join(annotators) or "all")
    table.add_row("Entity filters", ", ".join(entity_types) if entity_types else "all entity types")
    return render_lines(table)


def run_summary_lines(*, document_count: int, annotation_count: int, results_path: Path, tsv_paths: dict[str, Path], config_path: Path, manifest_path: Path) -> list[str]:
    table = Table(
        title="Run complete",
        box=box.ROUNDED,
        show_header=False,
        title_style="table.title",
        border_style="ok",
    )
    table.add_column("Item", style="field")
    table.add_column("Value")
    table.add_row("Documents", str(document_count))
    table.add_row("Annotations", str(annotation_count))
    table.add_row("Results JSON", str(results_path))
    for label, path in tsv_paths.items():
        table.add_row(label, str(path))
    table.add_row("Config", str(config_path))
    table.add_row("Manifest", str(manifest_path))
    return render_lines(table)


def annotator_results_lines(annotators: list[dict[str, Any]]) -> list[str]:
    """Render per-annotator outcomes and post-filter entity counts."""
    with_results = sum(int(row.get("entity_count", 0)) > 0 for row in annotators)
    table = Table(
        title="Annotator results",
        box=box.ROUNDED,
        title_style="table.title",
        border_style="panel.border",
    )
    table.add_column("Annotator", style="field")
    table.add_column("Status")
    table.add_column("Entities after filters", justify="right")
    for row in annotators:
        table.add_row(
            str(row.get("annotator", "Unknown")),
            str(row.get("status", "Unknown")),
            str(row.get("entity_count", 0)),
        )
    lines = [f"Annotators with results after filters: {with_results}/{len(annotators)}"]
    if annotators:
        lines.extend(render_lines(table))
    return lines

