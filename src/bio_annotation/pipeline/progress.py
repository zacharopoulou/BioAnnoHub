"""Progress reporting and annotator status summaries for pipeline runs.

Annotator work emits `ProgressEvent`s; the default reporter logs them, and the
terminal UI swaps in a reporter that drives a spinner. Rendering never happens
in the pipeline layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from bio_annotation.entity_types import ANNOTATOR_DISPLAY_NAMES

logger = logging.getLogger(__name__)

# Approximate download sizes. Loading is cached by Hugging Face, so the download
# only happens when the model is not on disk yet.
ANNOTATOR_ASSET_HINTS: dict[str, str] = {
    "apollo": "~740 MB to download if not cached",
    "clinicalbert": "~430 MB to download if not cached",
    "d4data": "~430 MB to download if not cached",
}

@dataclass(frozen=True)
class ProgressEvent:
    annotator: str
    phase: str  # "fetch", "preflight" or "annotate"
    event: str  # "start", "done" or "error"
    source: str | None = None
    document_count: int | None = None
    annotator_index: int | None = None
    annotator_total: int | None = None
    document_id: str | None = None
    pmid: str | None = None
    document_index: int | None = None
    document_total: int | None = None
    elapsed_seconds: float | None = None
    annotation_count: int | None = None
    reason: str | None = None

    @property
    def label(self) -> str:
        return ANNOTATOR_DISPLAY_NAMES.get(self.annotator, self.annotator)

    @property
    def document_label(self) -> str | None:
        if self.pmid:
            return f"PMID {self.pmid}"
        return self.document_id


ProgressReporter = Callable[[ProgressEvent], None]
SHORT_REASON_LENGTH = 100

def describe(event: ProgressEvent) -> str:
    """Human-readable one-line message for an event."""

    if event.phase == "fetch":
        return _describe_fetch(event)
    if event.phase == "preflight":
        return _describe_preflight(event)
    return _describe_annotate(event)

def log_progress(event: ProgressEvent) -> None:
    """Log concise progress and preserve full failure detail at debug level."""

    if event.event == "error":
        logger.warning("%s", describe(event))
        if event.reason and short_reason(event.reason) != event.reason:
            logger.debug("Full %s error: %s", event.label, event.reason)
        return

    if not should_report_progress(event):
        return

    logger.info("%s", describe(event))


def should_report_progress(event: ProgressEvent) -> bool:
    """Keep batch logs concise while retaining starts, milestones and outcomes."""

    if event.phase != "annotate" or event.document_index is None:
        return True
    if event.event == "start":
        return event.document_index == 1 or event.document_index % 25 == 0
    if event.event == "done":
        return (
            event.document_index % 25 == 0
            or event.document_total is not None
            and event.document_index == event.document_total
        )
    return True


def _describe_fetch(event: ProgressEvent) -> str:
    source = event.source or "document source"
    total = event.document_total
    count = event.document_count
    if event.event == "start":
        target = f" for {total} PMID(s)" if total is not None else ""
        return f"Fetching {source}{target}"
    if event.event == "done":
        if count is not None and total is not None:
            message = f"Fetched {count}/{total} document(s) from {source}"
        else:
            message = f"Finished fetching from {source}"
        return f"{message}{_elapsed(event)}"
    return f"{source} fetch failed{_elapsed(event)}: {short_reason(event.reason or '')}"

def _describe_preflight(event: ProgressEvent) -> str:
    if event.event == "start":
        hint = ANNOTATOR_ASSET_HINTS.get(event.annotator)
        message = f"Loading {event.label} model assets"
        return f"{message}; {hint}" if hint else message
    if event.event == "done":
        return f"Loaded {event.label} model assets{_elapsed(event)}"
    return f"{event.label} model assets unavailable{_elapsed(event)}: {short_reason(event.reason or '')}"

def _describe_annotate(event: ProgressEvent) -> str:
    prefix = ""
    if event.annotator_index and event.annotator_total:
        prefix = f"[{event.annotator_index}/{event.annotator_total}] "
    target = ""
    if event.document_label:
        target = f" on {event.document_label}"
    if event.document_index and event.document_total:
        target += f" (document {event.document_index}/{event.document_total})"
    if event.event == "start":
        return f"{prefix}Running {event.label}{target}"
    if event.event == "done":
        count = event.annotation_count or 0
        plural = "" if count == 1 else "s"
        message = f"{prefix}{event.label}{target}: {count} annotation{plural}{_elapsed(event)}"
        if not count and event.reason:
            message += f" - {short_reason(event.reason)}"
        return message
    return f"{prefix}{event.label} failed{target}{_elapsed(event)}: {short_reason(event.reason or '')}"


def short_reason(reason: str) -> str:
    """Keep progress output to one line, using the final exception for tracebacks."""

    lines = [line.strip() for line in reason.splitlines() if line.strip()]
    if not lines:
        return reason
    summary = lines[-1] if "Traceback (most recent call last)" in reason else lines[0]
    if len(summary) > SHORT_REASON_LENGTH:
        summary = summary[: SHORT_REASON_LENGTH - 1].rstrip() + "…"
    return summary

def _elapsed(event: ProgressEvent) -> str:
    if event.elapsed_seconds is None:
        return ""
    return f" in {event.elapsed_seconds:.1f}s"


def _build_annotator_summary(
    configured: list[str],
    statuses: list[dict[str, Any]],
) -> dict[str, Any]:
    produced = sorted(
        {
            str(status["name"])
            for status in statuses
            if status.get("status") == "produced_annotations"
        }
    )
    failed = sorted(
        {
            str(status["name"])
            for status in statuses
            if status.get("status") == "failed"
        }
    )
    not_produced = [
        name
        for name in configured
        if name not in produced and name not in failed
    ]
    return {
        "configured": configured,
        "produced": produced,
        "not_produced": not_produced,
        "failed": failed,
        "annotators": statuses,
    }


def _aggregate_annotator_statuses(statuses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse per-document annotator statuses into one entry per annotator."""
    aggregated: dict[str, dict[str, Any]] = {}
    for status in statuses:
        entry = aggregated.setdefault(
            str(status["name"]),
            {
                "name": status["name"],
                "status": "no_annotations",
                "annotation_count": 0,
                "duration_seconds": 0.0,
                "failed_documents": 0,
                "errors": [],
            },
        )
        entry["annotation_count"] += status.get("annotation_count", 0)
        entry["duration_seconds"] += status.get("duration_seconds", 0.0)
        if status.get("status") == "failed":
            entry["failed_documents"] += 1
            if status.get("reason") and status["reason"] not in entry["errors"]:
                entry["errors"].append(status["reason"])
    for entry in aggregated.values():
        entry["duration_seconds"] = round(entry["duration_seconds"], 3)
        if entry["annotation_count"]:
            entry["status"] = "produced_annotations"
        elif entry["failed_documents"]:
            entry["status"] = "failed"
    return list(aggregated.values())
