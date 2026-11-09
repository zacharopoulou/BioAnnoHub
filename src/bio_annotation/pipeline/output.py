from __future__ import annotations

import ast
import csv
import json
from pathlib import Path
from typing import Any

from bio_annotation.report import write_html_report

_EPMC_RAW_FIELD_NAMES = {
    "authorString": "authors",
    "journalTitle": "journal",
    "meshHeadingList": "mesh_terms",
    "keywordList": "keywords",
    "citedByCount": "citation_count",
    "isOpenAccess": "is_open_access",
    "inEPMC": "in_epmc",
    "fullTextUrlList": "full_text_urls",
    "pubYear": "year",
}
_EPMC_METADATA_KEYS = {
    "doi": "doi",
    "citation_count": "citation_count",
    "is_open_access": "is_open_access",
    "in_epmc": "in_epmc",
    "license": "license",
    "full_text_urls": "full_text_urls",
    "epmc_id": "id",
    "epmc_source": "source",
    "europe_pmc_year": "year",
}
_EPMC_TEXT_FIELDS = {"title", "abstractText", "fullTextXML", "fullText", "pmid"}


def write_pipeline_output(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_pipeline_tsv_outputs(payload, output_path)
    write_html_report(payload, output_path.with_suffix(".html"))


def pipeline_tsv_output_paths(output_path: Path) -> dict[str, Path]:
    return {
        "documents_tsv": output_path.with_name(f"{output_path.stem}.documents.tsv"),
        "keywords_tsv": output_path.with_name(f"{output_path.stem}.keywords.tsv"),
        "annotations_tsv": output_path.with_name(f"{output_path.stem}.annotations.tsv"),
    }


def write_pipeline_tsv_outputs(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    paths = pipeline_tsv_output_paths(output_path)
    write_documents_tsv(payload, paths["documents_tsv"])
    write_keywords_tsv(payload, paths["keywords_tsv"])
    write_annotations_tsv(payload, paths["annotations_tsv"])


def write_documents_tsv(payload: dict[str, Any], output_path: Path) -> None:
    documents = [
        document
        for document in payload.get("documents", [])
        if isinstance(document, dict)
    ]
    entrez_fields = sorted(
        {
            str(field)
            for document in documents
            if isinstance(document.get("metadata"), dict)
            and isinstance(document["metadata"].get("pubmed_record"), dict)
            for field in document["metadata"]["pubmed_record"]
            if field not in {"pmid", "title", "abstract"}
        }
    )
    europe_pmc_fields: set[str] = set()
    for document in documents:
        metadata = document.get("metadata")
        if not isinstance(metadata, dict):
            continue
        record = metadata.get("epmc_meta")
        if isinstance(record, dict):
            europe_pmc_fields.update(
                _EPMC_RAW_FIELD_NAMES.get(field, field)
                for field in record
                if field not in _EPMC_TEXT_FIELDS
            )
        europe_pmc_fields.update(
            column
            for key, column in _EPMC_METADATA_KEYS.items()
            if key in metadata
        )
    europe_pmc_fields.discard("pmcid")
    europe_pmc_fields.discard("pmid")
    fieldnames = [
        "document_id",
        "pmid",
        "pmcid",
        "title",
        "year",
        "source",
        "origin_sources",
        *(f"entrez_{field}" for field in entrez_fields),
        *(f"europe_pmc_{field}" for field in sorted(europe_pmc_fields)),
    ]
    rows: list[dict[str, Any]] = []
    for document in documents:
        metadata = document.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        record = metadata.get("pubmed_record")
        record = record if isinstance(record, dict) else {}
        row = {
            "document_id": document.get("document_id"),
            "pmid": document.get("pmid"),
            "pmcid": metadata.get("pmcid") or record.get("pmcid"),
            "title": document.get("title"),
            "year": document.get("year"),
            "source": document.get("source"),
            "origin_sources": _join_values(metadata.get("origin_sources")),
        }
        row.update(
            {
                f"entrez_{field}": _tsv_cell(record.get(field))
                for field in entrez_fields
            }
        )
        epmc_record = metadata.get("epmc_meta")
        epmc_record = epmc_record if isinstance(epmc_record, dict) else {}
        for field in europe_pmc_fields:
            value = None
            for metadata_key, column in _EPMC_METADATA_KEYS.items():
                if column == field and metadata_key in metadata:
                    value = metadata[metadata_key]
                    break
            if value is None:
                for raw_field, column in _EPMC_RAW_FIELD_NAMES.items():
                    if column == field and raw_field in epmc_record:
                        value = epmc_record[raw_field]
                        break
            if value is None:
                for raw_field, raw_value in epmc_record.items():
                    if (
                        raw_field not in _EPMC_TEXT_FIELDS
                        and _EPMC_RAW_FIELD_NAMES.get(raw_field, raw_field) == field
                    ):
                        value = raw_value
                        break
            row[f"europe_pmc_{field}"] = _tsv_cell(value)
        rows.append(row)

    _write_tsv(output_path, fieldnames, rows)


def write_keywords_tsv(payload: dict[str, Any], output_path: Path) -> None:
    documents = _documents_by_id(payload)
    annotations = _annotations_by_id(payload)
    rows: list[dict[str, Any]] = []

    for keyword in payload.get("keywords", []):
        if not isinstance(keyword, dict):
            continue

        document_id = str(keyword.get("document_id") or "")
        document = documents.get(document_id, {})
        keyword_annotations = _resolve_annotations(
            annotations,
            keyword.get("annotation_ids"),
        )

        first_mention = _first_mention(keyword)
        rows.append(
            {
                "document_id": document_id,
                "pmid": document.get("pmid"),
                "title": document.get("title"),
                "keyword": keyword.get("keyword"),
                "start": first_mention.get("start"),
                "end": first_mention.get("end"),
                "annotation_count": keyword.get("annotation_count"),
                "annotator_count": keyword.get("annotator_count"),
                "labels": _join_values(keyword.get("labels")),
                "canonical_ids": _join_values(keyword.get("canonical_ids")),
                "sources": _join_values(
                    sorted(
                        {
                            annotation.get("source")
                            for annotation in keyword_annotations
                            if annotation.get("source")
                        }
                    )
                ),
            }
        )

    _write_tsv(
        output_path,
        [
            "document_id",
            "pmid",
            "title",
            "keyword",
            "start",
            "end",
            "annotation_count",
            "annotator_count",
            "labels",
            "canonical_ids",
            "sources",
        ],
        rows,
    )


def write_annotations_tsv(payload: dict[str, Any], output_path: Path) -> None:
    documents = _documents_by_id(payload)
    rows: list[dict[str, Any]] = []

    for annotation in payload.get("annotations", []):
        if not isinstance(annotation, dict):
            continue

        document_id = str(annotation.get("document_id") or "")
        document = documents.get(document_id, {})

        rows.append(
            {
                "document_id": document_id,
                "pmid": document.get("pmid"),
                "title": document.get("title"),
                "source": annotation.get("source"),
                "span_text": annotation.get("span_text"),
                "start": annotation.get("start"),
                "end": annotation.get("end"),
                "entity_type": annotation.get("entity_type"),
                "annotation_id": annotation.get("annotation_id"),
                "canonical_id": _join_values(annotation.get("canonical_id")),
                "canonical_name": annotation.get("canonical_name"),
                "confidence": annotation.get("confidence"),
                "normalization_score": annotation.get("normalization_score"),
            }
        )

    _write_tsv(
        output_path,
        [
            "document_id",
            "pmid",
            "title",
            "source",
            "span_text",
            "start",
            "end",
            "entity_type",
            "annotation_id",
            "canonical_id",
            "canonical_name",
            "confidence",
            "normalization_score",
        ],
        rows,
    )


def _documents_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for document in payload.get("documents", []):
        if not isinstance(document, dict):
            continue
        document_id = document.get("document_id")
        if document_id is not None:
            documents[str(document_id)] = document
    return documents


def _annotations_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    annotations: dict[str, dict[str, Any]] = {}
    for annotation in payload.get("annotations", []):
        if not isinstance(annotation, dict):
            continue
        annotation_id = annotation.get("annotation_id")
        if annotation_id is not None:
            annotations[str(annotation_id)] = annotation
    return annotations


def _resolve_annotations(
    annotations: dict[str, dict[str, Any]],
    annotation_ids: object,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for annotation_id in _flatten_values(annotation_ids):
        annotation = annotations.get(str(annotation_id))
        if annotation is not None:
            resolved.append(annotation)
    return resolved


def _first_mention(keyword: dict[str, Any]) -> dict[str, Any]:
    mentions = keyword.get("mentions")
    if isinstance(mentions, list):
        for mention in mentions:
            if isinstance(mention, dict):
                return mention
    return {}


def _normalize_scalar_id(value: object) -> object:
    flattened = [_normalize_identifier_text(item) for item in _flatten_values(value)]
    if not flattened:
        return None
    if len(flattened) == 1:
        return flattened[0]
    return flattened


def _flatten_values(values: object) -> list[object]:
    if values is None:
        return []
    if isinstance(values, list | tuple | set):
        flattened: list[object] = []
        for value in values:
            flattened.extend(_flatten_values(value))
        return flattened
    if isinstance(values, str):
        parsed = _parse_stringified_list(values)
        if parsed is not None:
            return _flatten_values(parsed)
    return [values]


def _normalize_identifier_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped.lower().startswith("mesh:"):
        return f"MESH:{stripped.split(':', 1)[1]}"
    return stripped


def _parse_stringified_list(value: str) -> object | None:
    stripped = value.strip()
    if not stripped.startswith("[") or not stripped.endswith("]"):
        return None
    try:
        parsed = ast.literal_eval(stripped)
    except (SyntaxError, ValueError):
        return None
    return parsed if isinstance(parsed, list | tuple | set) else None


def _join_values(values: object) -> str:
    if values is None:
        return ""
    return "|".join(
        str(_normalize_identifier_text(value))
        for value in _flatten_values(values)
        if value is not None
    )


def _tsv_cell(value: Any) -> Any:
    if isinstance(value, set):
        value = sorted(value, key=str)
    if isinstance(value, list | tuple | dict | set):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return value


def _write_tsv(
    output_path: Path,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
