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
    phase: str  # "preflight" (model assets) or "annotate" (per document)
    event: str  # "start", "done" or "error"
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

def describe(event: ProgressEvent) -> str:
    """Human-readable one-line message for an event."""

    if event.phase == "preflight":
        return _describe_preflight(event)
    return _describe_annotate(event)

def log_progress(event: ProgressEvent) -> None:
    """Log concise run progress, while always preserving failures."""

    if event.event == "error":
        logger.warning("%s", describe(event))
        return

    if event.phase == "annotate":
        if event.event == "start" and event.document_index not in (None, 1):
            return
        if event.event == "done" and event.document_index is not None:
            is_milestone = event.document_index % 25 == 0
            is_final = (
                event.document_total is not None
                and event.document_index == event.document_total
            )
            if not (is_milestone or is_final):
                return

    logger.info("%s", describe(event))

def _describe_preflight(event: ProgressEvent) -> str:
    if event.event == "start":
        hint = ANNOTATOR_ASSET_HINTS.get(event.annotator)
        message = f"Loading {event.label} model assets"
        return f"{message}; {hint}" if hint else message
    if event.event == "done":
        return f"Loaded {event.label} model assets{_elapsed(event)}"
    return f"{event.label} model assets unavailable{_elapsed(event)}: {event.reason}"

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
            message += f" - {event.reason}"
        return message
    return f"{prefix}{event.label} failed{target}{_elapsed(event)}: {event.reason}"

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
