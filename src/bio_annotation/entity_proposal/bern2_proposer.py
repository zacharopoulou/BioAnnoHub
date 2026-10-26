from __future__ import annotations

import json
import logging
import os
from difflib import SequenceMatcher
from typing import Any, Callable
from urllib import error, parse, request

from bio_annotation.entity_proposal._shared import make_annotation, pick_first
from bio_annotation.schemas.document import Document
from bio_annotation.schemas.entity import Annotation

DEFAULT_BERN2_API_URL = "https://bern2.korea.ac.kr/plain"
LOCAL_BERN2_HOSTS = {"127.0.0.1", "localhost", "::1"}
MAX_ALIGNMENT_EDITS = 256
MAX_ALIGNMENT_CELLS = 5_000_000
MAX_ALIGNMENT_COMPARISONS = 25_000_000
logger = logging.getLogger(__name__)


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("annotations", "entities", "denotations"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def parse_bern2_response(document: Document, payload: Any) -> list[Annotation]:
    annotations: list[Annotation] = []
    records = _extract_records(payload)
    response_text = payload.get("text") if isinstance(payload, dict) else None
    text_matches = isinstance(response_text, str) and response_text == document.text

    offset_map: dict[int, int] | None = None
    if records and not text_matches and isinstance(response_text, str):
        offset_map = _unique_offset_map(
            document.text,
            response_text,
            [
                offset
                for record in records
                for offset in _record_offsets(record)
                if offset is not None
            ],
        )
        if offset_map is None:
            logger.warning(
                "BERN2 predictions for %s are unplaced: response text differs and no safe unique alignment was found",
                document.document_id,
            )
    elif records and not text_matches:
        logger.warning(
            "BERN2 predictions for %s are unplaced: response did not include text to verify its coordinate basis",
            document.document_id,
        )

    unaligned_count = 0
    for record in records:
        mention = pick_first(
            record.get("mention"),
            record.get("text"),
            record.get("span_text"),
            record.get("obj"),
        )
        if not mention:
            continue

        start, end = _record_offsets(record)
        if text_matches:
            mapped = _validated_offsets(document.text, str(mention).strip(), start, end, None)
        elif offset_map is not None:
            mapped = _validated_offsets(document.text, str(mention).strip(), start, end, offset_map)
        else:
            mapped = None
        if mapped is None:
            start = end = None
            unaligned_count += 1
        else:
            start, end = mapped

        annotations.append(
            make_annotation(
                document=document,
                source="bern2",
                span_text=mention,
                entity_type=pick_first(
                    record.get("type"),
                    record.get("entity_type"),
                    record.get("obj"),
                ),
                start=start,
                end=end,
                canonical_id=pick_first(
                    _first_identifier(record.get("id")),
                    record.get("db_id"),
                    record.get("identifier"),
                ),
                canonical_name=pick_first(
                    record.get("normalizedName"),
                    record.get("preferred_name"),
                    record.get("name"),
                ),
                confidence=pick_first(
                    record.get("confidence"),
                    record.get("probability"),
                    record.get("prob"),
                    record.get("score"),
                ),
                infer_missing_offsets=False,
            )
        )

    if unaligned_count:
        logger.warning(
            "BERN2 returned %d predictions for %s whose coordinates do not select their mention in the submitted text; left unplaced",
            unaligned_count,
            document.document_id,
        )
    elif records and not text_matches:
        logger.info(
            "BERN2 text for %s differed from submitted text; all %d predictions mapped to verified spans",
            document.document_id,
            len(annotations),
        )

    return annotations


def _record_offsets(record: dict[str, Any]) -> tuple[Any, Any]:
    span = record.get("span") if isinstance(record.get("span"), dict) else {}
    return (
        pick_first(record.get("start"), span.get("begin"), span.get("start")),
        pick_first(record.get("end"), span.get("end")),
    )


def _validated_offsets(
    document_text: str,
    mention: str,
    start: Any,
    end: Any,
    offset_map: dict[int, int] | None,
) -> tuple[int, int] | None:
    try:
        response_start, response_end = int(start), int(end)
    except (TypeError, ValueError):
        return None

    if response_start < 0 or response_end < response_start:
        return None

    if offset_map is None:
        mapped_start, mapped_end = response_start, response_end
    else:
        if response_start not in offset_map or response_end not in offset_map:
            return None
        mapped_start = offset_map[response_start]
        mapped_end = offset_map[response_end]

    if mapped_end > len(document_text):
        return None
    if document_text[mapped_start:mapped_end] != mention:
        return None
    return mapped_start, mapped_end


def _unique_offset_map(
    document_text: str,
    response_text: str,
    response_boundaries: list[Any],
) -> dict[int, int] | None:
    """Map response boundaries only when every shortest text alignment agrees."""
    boundaries: set[int] = set()
    for value in response_boundaries:
        try:
            boundary = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= boundary <= len(response_text):
            boundaries.add(boundary)

    if len(document_text) * len(response_text) > MAX_ALIGNMENT_COMPARISONS:
        return None

    matcher = SequenceMatcher(a=document_text, b=response_text, autojunk=False)
    edit_bound = sum(
        max(i2 - i1, j2 - j1)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag != "equal"
    )
    if edit_bound > MAX_ALIGNMENT_EDITS:
        return None
    estimated_cells = (len(document_text) + 1) * min(
        len(response_text) + 1,
        2 * edit_bound + 1,
    )
    if estimated_cells > MAX_ALIGNMENT_CELLS:
        return None

    forward, distance = _boundary_distances(document_text, response_text, boundaries, edit_bound)
    if distance is None:
        return None
    reverse_boundaries = {len(response_text) - value for value in boundaries}
    backward, reverse_distance = _boundary_distances(
        document_text[::-1],
        response_text[::-1],
        reverse_boundaries,
        edit_bound,
    )
    if reverse_distance != distance:
        return None

    mapping: dict[int, int] = {}
    for response_boundary in boundaries:
        reverse_boundary = len(response_text) - response_boundary
        possible: set[int] = set()
        for document_boundary, prefix_cost in forward[response_boundary].items():
            reverse_document_boundary = len(document_text) - document_boundary
            suffix_cost = backward[reverse_boundary].get(reverse_document_boundary)
            if suffix_cost is not None and prefix_cost + suffix_cost == distance:
                possible.add(document_boundary)
        if len(possible) != 1:
            continue
        mapping[response_boundary] = next(iter(possible))
    return mapping


def _boundary_distances(
    document_text: str,
    response_text: str,
    boundaries: set[int],
    edit_bound: int,
) -> tuple[dict[int, dict[int, int]], int | None]:
    """Return prefix edit costs at requested response boundaries within a safe band."""
    infinity = edit_bound + 1
    width = len(response_text)
    previous = {column: column for column in range(min(width, edit_bound) + 1)}
    found: dict[int, dict[int, int]] = {boundary: {} for boundary in boundaries}
    if 0 in boundaries:
        found[0][0] = 0

    for row_index, character in enumerate(document_text, start=1):
        low = max(0, row_index - edit_bound)
        high = min(width, row_index + edit_bound)
        current: dict[int, int] = {}
        for column in range(low, high + 1):
            deletion = previous.get(column, infinity) + 1
            insertion = current.get(column - 1, infinity) + 1
            substitution = previous.get(column - 1, infinity) + (
                0 if character == response_text[column - 1] else 1
            ) if column > 0 else infinity
            cost = min(deletion, insertion, substitution)
            if cost <= edit_bound:
                current[column] = cost
                if column in boundaries:
                    found[column][row_index] = cost
        previous = current

    return found, previous.get(width)


def _first_identifier(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def call_bern2(document: Document, endpoint: str | None = None, timeout: int = 30) -> Any:
    target = endpoint or os.getenv("BERN2_API_URL") or DEFAULT_BERN2_API_URL
    if not target.endswith("/plain"):
        target = target.rstrip("/") + "/plain"

    payload = json.dumps({"text": document.text}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    http_request = request.Request(target, data=payload, headers=headers, method="POST")

    try:
        opener = _request_opener_for_url(target)
        with opener.open(http_request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(f"BERN2 request failed for {target}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"BERN2 returned invalid JSON from {target}: {exc}") from exc


def _request_opener_for_url(url: str) -> request.OpenerDirector:
    host = parse.urlparse(url).hostname
    if host in LOCAL_BERN2_HOSTS:
        return request.build_opener(request.ProxyHandler({}))
    return request.build_opener()


def annotate_with_bern2(
    document: Document,
    *,
    response: Any = None,
    request_fn: Callable[[Document], Any] | None = None,
    endpoint: str | None = None,
    timeout: int = 30,
) -> list[Annotation]:
    payload = response
    if payload is None and request_fn is not None:
        payload = request_fn(document)
    if payload is None:
        payload = call_bern2(document, endpoint=endpoint, timeout=timeout)
    return parse_bern2_response(document, payload)
