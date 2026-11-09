from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable
from urllib import error, parse, request

from bio_annotation.entity_proposal._shared import make_annotation, pick_first
from bio_annotation.schemas.document import Document
from bio_annotation.schemas.entity import Annotation

logger = logging.getLogger(__name__)

# MedCAT has no public endpoint; the CogStack MedCATservice docker-compose maps
# the service to localhost:5555 by default, so an unconfigured run still reaches
# a local service. MEDCAT_API_URL or an explicit endpoint override this.
DEFAULT_MEDCAT_API_URL = "http://localhost:5555"


class MedCATServiceError(RuntimeError):
    """A failed MedCAT request, distinct from a successful empty prediction."""


def _normalize_medcat_process_url(url: str) -> str:
    """CogStack MedCATservice expects POST ``/api/process``. Users often set only host:port."""

    raw = (url or "").strip()
    parsed = parse.urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise MedCATServiceError("MedCAT endpoint must be an absolute http(s) URL.")
    try:
        parsed.port
    except ValueError as exc:
        raise MedCATServiceError("MedCAT endpoint has an invalid port.") from exc
    path = parsed.path.rstrip("/")
    if not path:
        path = "/api/process"
    elif path == "/api":
        path += "/process"
    # Preserve explicit paths: do not silently turn a typo into /typo/api/process.
    return parse.urlunparse(parsed._replace(path=path, fragment=""))


def _medcat_min_acc_threshold(explicit: float | None) -> float | None:
    """Optional 0..1 cutoff on MedCAT ``acc`` / ``context_similarity`` (see env ``MEDCAT_MIN_ACC``)."""

    if explicit is not None:
        return explicit if explicit > 0.0 else None
    raw = os.getenv("MEDCAT_MIN_ACC", "").strip()
    if not raw:
        return None
    try:
        v = float(raw)
    except ValueError:
        return None
    return v if v > 0.0 else None


def _first_nonempty_str_list(value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return None
    first = value[0]
    if first is None:
        return None
    text = str(first).strip()
    return text or None


def _looks_like_entity_record(item: dict[str, Any]) -> bool:
    if not item:
        return False
    return bool(
        item.get("cui")
        or item.get("pretty_name")
        or item.get("source_value")
        or item.get("value")
        or item.get("mention")
    )


def _flatten_annotation_value(raw: Any) -> list[dict[str, Any]]:
    """Normalize MedCAT / MedCATservice annotation containers to flat entity dicts."""

    if raw is None:
        return []
    if isinstance(raw, list):
        out: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            vals = [v for v in item.values() if isinstance(v, dict)]
            if (
                vals
                and len(vals) == len(item)
                and any(_looks_like_entity_record(v) for v in vals)
            ):
                out.extend(vals)
            else:
                out.append(item)
        return [x for x in out if _looks_like_entity_record(x)]
    if isinstance(raw, dict):
        nested_ent = raw.get("entities")
        if isinstance(nested_ent, dict) and nested_ent:
            inner = _flatten_annotation_value(nested_ent)
            if inner:
                return inner
        vals = [v for v in raw.values() if isinstance(v, dict)]
        if vals and len(vals) == len(raw) and any(_looks_like_entity_record(v) for v in vals):
            return vals
        if _looks_like_entity_record(raw):
            return [raw]
    return []


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict) and _looks_like_entity_record(item)]

    if not isinstance(payload, dict):
        return []

    # CogStack MedCATservice: { "result": { "annotations": ... } }
    # MedCAT 1.2+ often uses annotations: { "entities": { "0": {...}, ... }, "tokens": [...] }.
    result = payload.get("result")
    if isinstance(result, dict):
        ann = result.get("annotations")
        if isinstance(ann, dict):
            nested = ann.get("entities")
            if isinstance(nested, dict) and nested:
                records = _flatten_annotation_value(nested)
                if records:
                    return records
        for key in ("annotations", "entities"):
            records = _flatten_annotation_value(result.get(key))
            if records:
                return records

    for key in ("entities", "annotations", "results", "denotations"):
        records = _flatten_annotation_value(payload.get(key))
        if records:
            return records

    if _looks_like_entity_record(payload):
        return [payload]
    return []


def parse_medcat_response(
    document: Document,
    payload: Any,
    *,
    min_acc: float | None = None,
) -> list[Annotation]:
    """Parse MedCATservice JSON. Set ``min_acc`` or ``MEDCAT_MIN_ACC`` to drop low-confidence spans."""

    threshold = _medcat_min_acc_threshold(min_acc)
    annotations: list[Annotation] = []
    for record in _extract_records(payload):
        mention = pick_first(
            record.get("value"),
            record.get("source_value"),
            record.get("detected_name"),
            record.get("mention"),
            record.get("text"),
            record.get("pretty_name"),
        )
        if not mention:
            continue
        raw_conf = pick_first(
            record.get("acc"),
            record.get("context_similarity"),
            record.get("confidence"),
            record.get("score"),
        )
        if threshold is not None:
            try:
                conf_f = float(raw_conf) if raw_conf is not None else None
            except (TypeError, ValueError):
                conf_f = None
            if conf_f is None or conf_f < threshold:
                continue

        annotations.append(
            make_annotation(
                document=document,
                source="medcat",
                span_text=mention,
                entity_type=pick_first(
                    record.get("type"),
                    record.get("entity_type"),
                    record.get("tui"),
                    record.get("semantic_type"),
                    _first_nonempty_str_list(record.get("type_ids")),
                    _first_nonempty_str_list(record.get("types")),
                    "concept",
                ),
                start=pick_first(
                    record.get("start"),
                    record.get("start_char"),
                    record.get("begin"),
                ),
                end=pick_first(
                    record.get("end"),
                    record.get("end_char"),
                ),
                canonical_id=pick_first(
                    record.get("cui"),
                    record.get("id"),
                    record.get("concept_id"),
                ),
                canonical_name=pick_first(
                    record.get("pretty_name"),
                    record.get("name"),
                    record.get("preferred_name"),
                ),
                normalization_score=raw_conf,
            )
        )
    return annotations


def _summarize_response_body(body: str, limit: int = 120) -> str:
    text = " ".join(re.sub(r"<[^>]+>", " ", body).split())
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


_reported_endpoints: set[str] = set()


def reset_reported_endpoints() -> None:
    _reported_endpoints.clear()


def _failure_log_level(target: str) -> int:
    """WARNING for an endpoint's first failure, DEBUG for the repeats."""

    if target in _reported_endpoints:
        return logging.DEBUG
    _reported_endpoints.add(target)
    return logging.WARNING


def call_medcat(document: Document, endpoint: str | None = None, timeout: int = 45) -> Any:
    target = _normalize_medcat_process_url(endpoint or os.getenv("MEDCAT_API_URL") or DEFAULT_MEDCAT_API_URL)
    text = document.get_text()
    # CogStack MedCATservice POST /api/process uses {"content": {"text": ...}}; we also send top-level "text".
    body: dict[str, Any] = {
        "text": text,
        "content": {"text": text},
    }
    payload = json.dumps(body).encode("utf-8")
    http_request = request.Request(
        target,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "BioAnnoHub/medcat-client"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            _validate_medcat_response(result)
            return result
    except error.HTTPError as exc:
        try:
            detail = _summarize_response_body(exc.read(4096).decode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            detail = ""
        hint = (
            "Check the process endpoint path."
            if exc.code in {404, 405}
            else "Check MedCATservice logs and that its model has loaded."
        )
        message = f"MedCAT HTTP {exc.code} {exc.reason} at {target}. {hint}"
        if detail:
            message += f" Response: {detail}"
        logger.log(_failure_log_level(target), "%s", message)
        raise MedCATServiceError(message) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MedCATServiceError(
            f"MedCAT returned invalid JSON at {target}; check the endpoint path."
        ) from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        message = (
            f"MedCAT connection failed at {target}: {exc}. Start MedCATservice and check "
            "annotators.medcat.endpoint or MEDCAT_API_URL (host/port and container networking)."
        )
        logger.log(_failure_log_level(target), "%s", message)
        raise MedCATServiceError(message) from exc


def _validate_medcat_response(payload: Any) -> None:
    """Reject error/unknown responses without rejecting supported empty containers."""
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return
    if isinstance(payload, dict):
        result = payload.get("result", payload)
        if payload.get("success") is False or (isinstance(result, dict) and result.get("success") is False):
            raise MedCATServiceError("MedCAT reported success=false; check MedCATservice logs.")
        if isinstance(result, dict):
            for key in ("annotations", "entities", "results", "denotations"):
                if isinstance(result.get(key), (dict, list)):
                    return
            if _looks_like_entity_record(result):
                return
    raise MedCATServiceError("MedCAT returned an unrecognized response; check the process endpoint and service logs.")


def annotate_with_medcat(
    document: Document,
    *,
    response: Any = None,
    request_fn: Callable[[Document], Any] | None = None,
    endpoint: str | None = None,
    min_acc: float | None = None,
) -> list[Annotation]:
    payload = response
    if payload is None and request_fn is not None:
        payload = request_fn(document)
    if payload is None and request_fn is None:
        payload = call_medcat(document, endpoint=endpoint)
    _validate_medcat_response(payload)
    return parse_medcat_response(document, payload, min_acc=min_acc)


__all__ = ["DEFAULT_MEDCAT_API_URL", "annotate_with_medcat", "call_medcat", "parse_medcat_response"]
