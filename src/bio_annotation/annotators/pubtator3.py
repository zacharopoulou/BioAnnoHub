from __future__ import annotations

import json
import os
from typing import Any, Callable

from bio_annotation.clients.pubtator3 import (
    DEFAULT_EXPORT_FORMAT,
    PUBTATOR3_API_BASE_URL,
    PubTator3Client,
)
from bio_annotation.entity_proposal._shared import make_annotation, pick_first
from bio_annotation.schemas.document import Document
from bio_annotation.schemas.entity import Annotation


def _document_annotation_text(document: Document) -> str:
    return document.text.strip()


def _parse_bioc_document(document: Document, doc_payload: dict[str, Any]) -> list[Annotation]:
    annotations: list[Annotation] = []
    source_text = _document_annotation_text(document)

    for passage in doc_payload.get("passages", []):
        coordinate_shift = _passage_coordinate_shift(document, passage)
        for record in passage.get("annotations", []):
            locations = record.get("locations", [])
            first_location = locations[0] if locations else {}
            raw_start = pick_first(first_location.get("offset"), record.get("start"))
            length = first_location.get("length")
            raw_end = pick_first(
                record.get("end"),
                int(raw_start) + int(length) if raw_start is not None and length is not None else None,
            )
            start = _shift_offset(raw_start, coordinate_shift)
            end = _shift_offset(raw_end, coordinate_shift)

            mention = pick_first(record.get("text"), record.get("span_text"))
            if mention is None and start is not None and end is not None:
                mention = source_text[int(start) : int(end)]
            if not mention:
                continue

            infons = record.get("infons", {})
            annotations.append(
                make_annotation(
                    document=document,
                    source="pubtator3",
                    span_text=mention,
                    entity_type=pick_first(
                        infons.get("type"),
                        record.get("type"),
                        record.get("entity_type"),
                    ),
                    start=start,
                    end=end,
                    canonical_id=pick_first(
                        infons.get("identifier"),
                        record.get("identifier"),
                        record.get("id"),
                    ),
                    canonical_name=pick_first(infons.get("name"), record.get("name")),
                )
            )

    return annotations


def _parse_pubtator_text(document: Document, payload: str) -> list[Annotation]:
    annotations: list[Annotation] = []
    for line in payload.splitlines():
        if not line.strip() or "|t|" in line or "|a|" in line:
            continue
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        _, start, end, mention, entity_type, canonical_id = parts[:6]
        try:
            start_offset = int(start)
            end_offset = int(end)
        except ValueError:
            continue
        annotations.append(
            make_annotation(
                document=document,
                source="pubtator3",
                span_text=mention,
                entity_type=entity_type,
                start=start_offset,
                end=end_offset,
                canonical_id=canonical_id,
            )
        )
    return annotations


def parse_pubtator3_response(document: Document, payload: Any) -> list[Annotation]:
    if payload is None:
        return []

    if isinstance(payload, str):
        if not payload.strip():
            return []
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return _parse_pubtator_text(document, payload)

    if isinstance(payload, dict):
        if "documents" in payload and isinstance(payload["documents"], list):
            annotations: list[Annotation] = []
            for doc_payload in payload["documents"]:
                if isinstance(doc_payload, dict):
                    annotations.extend(_parse_bioc_document(document, doc_payload))
            return annotations

        if "PubTator3" in payload and isinstance(payload["PubTator3"], list):
            annotations: list[Annotation] = []
            for doc_payload in payload["PubTator3"]:
                if isinstance(doc_payload, dict):
                    annotations.extend(_parse_bioc_document(document, doc_payload))
            return annotations

        if "passages" in payload:
            return _parse_bioc_document(document, payload)

        return []

    if isinstance(payload, list):
        annotations: list[Annotation] = []
        for doc_payload in payload:
            if isinstance(doc_payload, dict):
                annotations.extend(_parse_bioc_document(document, doc_payload))
        return annotations

    return []


def _passage_coordinate_shift(document: Document, passage: dict[str, Any]) -> int:
    source_start = _passage_source_start(passage)
    canonical_start = _canonical_passage_start(document, passage)
    if source_start is None or canonical_start is None:
        return 0
    return canonical_start - source_start


def _passage_source_start(passage: dict[str, Any]) -> int | None:
    for key in ("offset", "start", "begin"):
        value = _to_int(passage.get(key))
        if value is not None:
            return value
    offsets = passage.get("offsets")
    if isinstance(offsets, list) and offsets:
        first = offsets[0]
        if isinstance(first, list) and first:
            return _to_int(first[0])
        if isinstance(first, dict):
            return _to_int(first.get("start") or first.get("begin") or first.get("offset"))
        return _to_int(first)
    return None


def _canonical_passage_start(document: Document, passage: dict[str, Any]) -> int | None:
    passage_text = _passage_text(passage)
    document_text = document.text
    if passage_text:
        index = document_text.find(passage_text)
        if index >= 0:
            return index

    kind = _passage_kind(passage)
    if kind == "title":
        return 0
    if kind == "abstract":
        title = document.title or ""
        return len(title) + 2 if title else 0
    return None


def _passage_text(passage: dict[str, Any]) -> str:
    value = passage.get("text")
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item is not None).strip()
    return str(value or "").strip()


def _passage_kind(passage: dict[str, Any]) -> str | None:
    infons = passage.get("infons") if isinstance(passage.get("infons"), dict) else {}
    raw = pick_first(passage.get("type"), passage.get("section_type"), infons.get("type"))
    text = str(raw or "").lower()
    if "title" in text:
        return "title"
    if "abstract" in text:
        return "abstract"
    return None


def _shift_offset(value: Any, shift: int) -> int | None:
    number = _to_int(value)
    return number + shift if number is not None else None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _document_pmcid(document: Document) -> str | None:
    metadata = document.metadata if isinstance(document.metadata, dict) else {}
    pubmed_record = metadata.get("pubmed_record")
    if isinstance(pubmed_record, dict):
        value = pubmed_record.get("pmcid")
        if value:
            return str(value)
    value = metadata.get("pmcid")
    if value:
        return str(value)
    return None


def call_pubtator3(
    document: Document,
    *,
    client: PubTator3Client | None = None,
    endpoint: str | None = None,
    timeout: int = 60,
    format: str = DEFAULT_EXPORT_FORMAT,
) -> Any:
    active_client = client or PubTator3Client(
        base_url=endpoint or os.getenv("PUBTATOR3_API_URL", PUBTATOR3_API_BASE_URL),
        timeout=timeout,
    )

    if document.pmid:
        return active_client.fetch_publications_by_pmids([document.pmid], format=format)

    pmcid = _document_pmcid(document)
    if pmcid:
        return active_client.fetch_publications_by_pmcids([pmcid], format=format)
    return None


def annotate_with_pubtator3(
    document: Document,
    *,
    response: Any = None,
    request_fn: Callable[[Document], Any] | None = None,
    client: PubTator3Client | None = None,
    endpoint: str | None = None,
    timeout: int = 60,
    format: str = DEFAULT_EXPORT_FORMAT,
) -> list[Annotation]:
    payload = response
    if payload is None and request_fn is not None:
        payload = request_fn(document)
    if payload is None:
        payload = call_pubtator3(
            document,
            client=client,
            endpoint=endpoint,
            timeout=timeout,
            format=format,
        )
    return parse_pubtator3_response(document, payload)


__all__ = [
    "annotate_with_pubtator3",
    "call_pubtator3",
    "parse_pubtator3_response",
]
