from __future__ import annotations

from typing import Any

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
