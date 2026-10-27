from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Any, Callable

from bio_annotation.annotators.apollo import (
    _load_apollo_pipeline,
    annotate_with_apollo,
)
from bio_annotation.annotators.bent import annotate_with_bent
from bio_annotation.annotators.bern2 import annotate_with_bern2
from bio_annotation.annotators.clinicalbert import (
    _load_clinicalbert_pipeline,
    annotate_with_clinicalbert,
)
from bio_annotation.annotators.d4data import (
    _load_d4data_pipeline,
    annotate_with_d4data,
)
from bio_annotation.annotators.flair import FLAIR_INSTALL_HINT, annotate_with_flair
from bio_annotation.annotators.medcat import annotate_with_medcat
from bio_annotation.annotators.pubtator3 import annotate_with_pubtator3
from bio_annotation.annotators.scispacy import (
    SCISPACY_MODEL_BY_ANNOTATOR,
    _load_scispacy_model,
    annotate_with_scispacy,
)
from bio_annotation.annotators.stanza import annotate_with_stanza
from bio_annotation.deps import (
    ANNOTATOR_EXTRAS,
    EXTRA_INSTALL_HINTS,
    ensure_extras,
    ensure_tool_environments,
    extra_installed,
)
from bio_annotation.entity_proposal.medcat_proposer import reset_reported_endpoints
from bio_annotation.entity_proposal.stanza_proposer import (
    STANZA_ANNOTATORS,
    stanza_model_for_annotator,
)
from bio_annotation.entity_types import normalize_entity_type
from bio_annotation.pipeline.options import (
    DEFAULT_FLAIR_LINKERS,
    SCISPACY_ANNOTATORS,
    SCISPACY_ANNOTATOR_SET,
    SUPPORTED_ANNOTATORS,
    _read_apollo_options,
    _read_bent_options,
    _read_bern2_options,
    _read_clinicalbert_options,
    _read_d4data_options,
    _read_flair_options,
    _read_medcat_options,
    _read_pubtator3_options,
    _read_scispacy_options,
    _read_stanza_options,
    _validate_annotators,
)
from bio_annotation.pipeline.output import _flatten_values, _normalize_scalar_id
from bio_annotation.pipeline.progress import _build_annotator_summary
from bio_annotation.pipeline_config import PipelineConfig
from bio_annotation.preprocessing.document_loader import (
    resolve_input_description,
    summarize_ingestion,
)
from bio_annotation.schemas.document import Document
from bio_annotation.schemas.entity import Annotation

def build_pipeline_output(
    documents: list[Document],
    config: PipelineConfig,
    *,
    bern2_request_fn: Callable[[Document], Any] | None = None,
    pubtator3_request_fn: Callable[[Document], Any] | None = None,
    flair_spans_by_document: dict[str, list[Any]] | None = None,
    bent_request_fn: Callable[[Document], Any] | None = None,
    clinicalbert_responses_by_document: dict[str, list[Any]] | None = None,
    apollo_responses_by_document: dict[str, list[Any]] | None = None,
    d4data_responses_by_document: dict[str, list[Any]] | None = None,
    medcat_request_fn: Callable[[Document], Any] | None = None,
    scispacy_responses_by_document: dict[str, dict[str, list[Any]]] | None = None,
    stanza_entities_by_document: dict[str, dict[str, list[Any]]] | None = None,
) -> dict[str, Any]:
    enabled_annotators = list(config.annotators)
    annotator_settings = dict(config.annotator_settings)
    _validate_annotators(enabled_annotators)
    reset_reported_endpoints()
    input_description = resolve_input_description(config)
    corpus_documents = [document_to_dict(document) for document in documents]
    bern2_options = _read_bern2_options(annotator_settings.get("bern2", {}))
    pubtator3_options = _read_pubtator3_options(annotator_settings.get("pubtator3", {}))
    flair_options = _read_flair_options(annotator_settings.get("flair", {}))
    bent_options = _read_bent_options(annotator_settings.get("bent", {}))
    clinicalbert_options = _read_clinicalbert_options(annotator_settings.get("clinicalbert", {}))
    apollo_options = _read_apollo_options(annotator_settings.get("apollo", {}))
    d4data_options = _read_d4data_options(annotator_settings.get("d4data", {}))
    medcat_options = _read_medcat_options(annotator_settings.get("medcat", {}))
    scispacy_options = {
        annotator: _read_scispacy_options(
            annotator,
            annotator_settings.get(annotator, {}),
        )
        for annotator in enabled_annotators
        if annotator in SCISPACY_ANNOTATOR_SET
    }
    stanza_options = {
        annotator: _read_stanza_options(annotator_settings.get(annotator, {}))
        for annotator in enabled_annotators
        if annotator in STANZA_ANNOTATORS
    }

    flair_tagger = None
    flair_linkers: list[Any] = []
    if "flair" in enabled_annotators and flair_spans_by_document is None:
        try:
            flair_tagger = _load_flair_tagger(flair_options["model"] or "hunflair2")
        except Exception as exc:
            logger.warning("flair unavailable: %s", exc)
        if flair_tagger is not None and flair_options.get("linking"):
            for linker_name in flair_options["linkers"]:
                try:
                    flair_linkers.append(_load_flair_linker(linker_name))
                except Exception as exc:
                    logger.warning("flair linker %s unavailable: %s", linker_name, exc)
    clinicalbert_pipeline = None
    if "clinicalbert" in enabled_annotators and clinicalbert_responses_by_document is None:
        try:
            clinicalbert_pipeline = _load_clinicalbert_pipeline(clinicalbert_options["model"])
        except Exception as exc:
            logger.warning("clinicalbert unavailable: %s", exc)
    apollo_pipeline = None
    if "apollo" in enabled_annotators and apollo_responses_by_document is None:
        try:
            apollo_pipeline = _load_apollo_pipeline(apollo_options["model"])
        except Exception as exc:
            logger.warning("apollo unavailable: %s", exc)
    d4data_pipeline = None
    if "d4data" in enabled_annotators and d4data_responses_by_document is None:
        try:
            d4data_pipeline = _load_d4data_pipeline(d4data_options["model"])
        except Exception as exc:
            logger.warning("d4data unavailable: %s", exc)
    scispacy_nlps: dict[str, Any] = {}
    if scispacy_responses_by_document is None:
        for annotator in enabled_annotators:
            if annotator not in SCISPACY_ANNOTATOR_SET:
                continue
            try:
                options = scispacy_options[annotator]
                scispacy_nlps[annotator] = _load_scispacy_model(
                    options["model"],
                    linker_name=options.get("linker_name"),
                )
            except Exception as exc:
                logger.warning("%s unavailable: %s", annotator, exc)
    document_annotations: list[dict[str, Any]] = []
    annotations_output: list[dict[str, Any]] = []
    keyword_output: list[dict[str, Any]] = []
    annotation_summary = {
        "annotators_enabled": enabled_annotators,
        "document_count": len(documents),
        "annotation_count": 0,
        "keyword_count": 0,
    }

    all_statuses: list[dict[str, Any]] = []

    for document in documents:
        results, statuses = run_selected_annotators_with_status(
            document,
            enabled_annotators,
            bern2_request_fn=bern2_request_fn,
            pubtator3_request_fn=pubtator3_request_fn,
            bent_request_fn=bent_request_fn,
            medcat_request_fn=medcat_request_fn,
            bern2_options=bern2_options,
            pubtator3_options=pubtator3_options,
            bent_options=bent_options,
            medcat_options=medcat_options,
            stanza_options=stanza_options,
            flair_spans=(
                flair_spans_by_document.get(document.document_id)
                if flair_spans_by_document is not None
                else None
            ),
            flair_tagger=flair_tagger,
            flair_linkers=flair_linkers,
            flair_options=flair_options,
            clinicalbert_response=(
                clinicalbert_responses_by_document.get(document.document_id)
                if clinicalbert_responses_by_document is not None
                else None
            ),
            clinicalbert_pipeline=clinicalbert_pipeline,
            clinicalbert_options=clinicalbert_options,
            apollo_response=(
                apollo_responses_by_document.get(document.document_id)
                if apollo_responses_by_document is not None
                else None
            ),
            apollo_pipeline=apollo_pipeline,
            apollo_options=apollo_options,
            d4data_response=(
                d4data_responses_by_document.get(document.document_id)
                if d4data_responses_by_document is not None
                else None
            ),
            d4data_pipeline=d4data_pipeline,
            d4data_options=d4data_options,
            scispacy_response_by_annotator=(
                scispacy_responses_by_document.get(document.document_id)
                if scispacy_responses_by_document is not None
                else None
            ),
            scispacy_nlps=scispacy_nlps,
            scispacy_options=scispacy_options,
            stanza_entities=(
                stanza_entities_by_document.get(document.document_id)
                if stanza_entities_by_document is not None
                else None
            ),
        )
        all_statuses.extend(statuses)

        annotations = flatten_annotations(results)
        annotations = filter_annotations_by_type(annotations, config.entity_types)
        annotation_summary["annotation_count"] += len(annotations)
        document_keywords = build_keyword_annotations(document.document_id, annotations)
        annotation_summary["keyword_count"] += len(document_keywords)
        keyword_output.extend(document_keywords)
        if enabled_annotators:
            document_annotations.append(
                {
                    "document_id": document.document_id,
                    "sources": sorted(results),
                    "annotators": statuses,
                    "annotation_count": len(annotations),
                    "annotation_ids": [
                        annotation.annotation_id for annotation in annotations
                    ],
                }
            )
        annotations_output.extend(
            {
                "document_id": document.document_id,
                **annotation.to_dict(),
            }
            for annotation in annotations
        )

    return {
        "stage": "corpus",
        "input": input_description,
        "pipeline": {
            "mode": "ingestion_only" if not enabled_annotators else "ingestion_and_annotation",
            "annotators_enabled": enabled_annotators,
            "annotator_settings": {name: annotator_settings.get(name, {}) for name in enabled_annotators},
        },
        "document_count": len(corpus_documents),
        "corpus_summary": summarize_ingestion(documents),
        "entity_types": config.entity_types,
        "documents": corpus_documents,
        "annotation_summary": annotation_summary,
        "annotator_summary": _build_annotator_summary(
            enabled_annotators,
            all_statuses,
        ),
        "document_annotations": document_annotations,
        "keywords": keyword_output,
        "annotations": annotations_output,
    }


def run_selected_annotators(
    document: Document,
    annotators: list[str],
    *,
    bern2_request_fn: Callable[[Document], Any] | None = None,
    pubtator3_request_fn: Callable[[Document], Any] | None = None,
    bent_request_fn: Callable[[Document], Any] | None = None,
    medcat_request_fn: Callable[[Document], Any] | None = None,
    bern2_options: dict[str, Any] | None = None,
    pubtator3_options: dict[str, Any] | None = None,
    bent_options: dict[str, Any] | None = None,
    medcat_options: dict[str, Any] | None = None,
    stanza_options: dict[str, dict[str, Any]] | None = None,
    flair_spans: list[Any] | None = None,
    flair_tagger: Any = None,
    flair_linkers: list[Any] | None = None,
    flair_options: dict[str, Any] | None = None,
    clinicalbert_response: Any = None,
    clinicalbert_pipeline: Any = None,
    clinicalbert_options: dict[str, Any] | None = None,
    apollo_response: Any = None,
    apollo_pipeline: Any = None,
    apollo_options: dict[str, Any] | None = None,
    d4data_response: Any = None,
    d4data_pipeline: Any = None,
    d4data_options: dict[str, Any] | None = None,
    scispacy_response_by_annotator: dict[str, list[Any]] | None = None,
    scispacy_nlps: dict[str, Any] | None = None,
    scispacy_options: dict[str, dict[str, Any]] | None = None,
    stanza_entities: dict[str, list[Any]] | None = None,
) -> dict[str, list[Annotation]]:
    results, _ = run_selected_annotators_with_status(
        document,
        annotators,
        bern2_request_fn=bern2_request_fn,
        pubtator3_request_fn=pubtator3_request_fn,
        bent_request_fn=bent_request_fn,
        medcat_request_fn=medcat_request_fn,
        bern2_options=bern2_options,
        pubtator3_options=pubtator3_options,
        bent_options=bent_options,
        medcat_options=medcat_options,
        stanza_options=stanza_options,
        flair_spans=flair_spans,
        flair_tagger=flair_tagger,
        flair_linkers=flair_linkers,
        flair_options=flair_options,
        clinicalbert_response=clinicalbert_response,
        clinicalbert_pipeline=clinicalbert_pipeline,
        clinicalbert_options=clinicalbert_options,
        apollo_response=apollo_response,
        apollo_pipeline=apollo_pipeline,
        apollo_options=apollo_options,
        d4data_response=d4data_response,
        d4data_pipeline=d4data_pipeline,
        d4data_options=d4data_options,
        scispacy_response_by_annotator=scispacy_response_by_annotator,
        scispacy_nlps=scispacy_nlps,
        scispacy_options=scispacy_options,
        stanza_entities=stanza_entities,
    )
    return results


def run_selected_annotators_with_status(
    document: Document,
    annotators: list[str],
    *,
    bern2_request_fn: Callable[[Document], Any] | None = None,
    pubtator3_request_fn: Callable[[Document], Any] | None = None,
    bent_request_fn: Callable[[Document], Any] | None = None,
    medcat_request_fn: Callable[[Document], Any] | None = None,
    bern2_options: dict[str, Any] | None = None,
    pubtator3_options: dict[str, Any] | None = None,
    bent_options: dict[str, Any] | None = None,
    medcat_options: dict[str, Any] | None = None,
    stanza_options: dict[str, dict[str, Any]] | None = None,
    flair_spans: list[Any] | None = None,
    flair_tagger: Any = None,
    flair_linkers: list[Any] | None = None,
    flair_options: dict[str, Any] | None = None,
    clinicalbert_response: Any = None,
    clinicalbert_pipeline: Any = None,
    clinicalbert_options: dict[str, Any] | None = None,
    apollo_response: Any = None,
    apollo_pipeline: Any = None,
    apollo_options: dict[str, Any] | None = None,
    d4data_response: Any = None,
    d4data_pipeline: Any = None,
    d4data_options: dict[str, Any] | None = None,
    scispacy_response_by_annotator: dict[str, list[Any]] | None = None,
    scispacy_nlps: dict[str, Any] | None = None,
    scispacy_options: dict[str, dict[str, Any]] | None = None,
    stanza_entities: dict[str, list[Any]] | None = None,
) -> tuple[dict[str, list[Annotation]], list[dict[str, Any]]]:
    results: dict[str, list[Annotation]] = {}
    statuses: list[dict[str, Any]] = []

    for annotator in annotators:
        started = time.perf_counter()
        try:
            if annotator == "bern2":
                results[annotator] = annotate_with_bern2(
                    document,
                    request_fn=bern2_request_fn,
                    endpoint=(
                        bern2_options.get("endpoint")
                        if bern2_options
                        else None
                    ),
                )
            elif annotator == "flair":
                results[annotator] = annotate_with_flair(
                    document,
                    spans=flair_spans,
                    tagger=flair_tagger,
                    linkers=flair_linkers,
                    model=flair_options.get("model") if flair_options else None,
                )
            elif annotator == "pubtator3":
                results[annotator] = annotate_with_pubtator3(
                    document,
                    request_fn=pubtator3_request_fn,
                    endpoint=pubtator3_options.get("endpoint")
                    if pubtator3_options
                    else None,
                    timeout=pubtator3_options.get("timeout", 60)
                    if pubtator3_options
                    else 60,
                    format=pubtator3_options.get("format", "biocjson")
                    if pubtator3_options
                    else "biocjson",
                )
            elif annotator == "bent":
                results[annotator] = annotate_with_bent(
                    document,
                    request_fn=bent_request_fn,
                    types=bent_options.get("types") if bent_options else None,
                    mode=bent_options.get("mode", "ner_nel") if bent_options else "ner_nel",
                    project=bent_options.get("project", "tools/bent")
                    if bent_options
                    else "tools/bent",
                    script=bent_options.get("script") if bent_options else None,
                    python=bent_options.get("python") if bent_options else None,
                    timeout=bent_options.get("timeout", 900)
                    if bent_options
                    else 900,
                )
            elif annotator == "clinicalbert":
                results[annotator] = annotate_with_clinicalbert(
                    document,
                    response=clinicalbert_response,
                    pipeline=clinicalbert_pipeline,
                    model=clinicalbert_options.get("model") if clinicalbert_options else None,
                )
            elif annotator == "apollo":
                results[annotator] = annotate_with_apollo(
                    document,
                    response=apollo_response,
                    pipeline=apollo_pipeline,
                    model=apollo_options.get("model") if apollo_options else None,
                )
            elif annotator == "d4data":
                results[annotator] = annotate_with_d4data(
                    document,
                    response=d4data_response,
                    pipeline=d4data_pipeline,
                    model=d4data_options.get("model") if d4data_options else None,
                )
            elif annotator == "medcat":
                results[annotator] = annotate_with_medcat(
                    document,
                    request_fn=medcat_request_fn,
                    endpoint=medcat_options.get("endpoint") if medcat_options else None,
                    min_acc=medcat_options.get("min_acc") if medcat_options else None,
                )
            elif annotator in SCISPACY_ANNOTATOR_SET:
                options = scispacy_options.get(annotator, {}) if scispacy_options else {}
                results[annotator] = annotate_with_scispacy(
                    document,
                    source=annotator,
                    response=(
                        scispacy_response_by_annotator.get(annotator)
                        if scispacy_response_by_annotator is not None
                        else None
                    ),
                    nlp=scispacy_nlps.get(annotator) if scispacy_nlps else None,
                    model=options.get("model") or SCISPACY_MODEL_BY_ANNOTATOR[annotator],
                    linker_name=options.get("linker_name"),
                )
            elif annotator in STANZA_ANNOTATORS:
                options = stanza_options.get(annotator, {}) if stanza_options else {}
                results[annotator] = annotate_with_stanza(
                    document,
                    stanza_model_for_annotator(annotator),
                    entities=stanza_entities.get(annotator) if stanza_entities else None,
                    package=options.get("package"),
                )
            else:
                raise ValueError(f"Unsupported annotator: {annotator}")
        except Exception as exc:
            logger.warning("%s unavailable: %s", annotator, exc)
            results[annotator] = []
            statuses.append(
                {
                    "name": annotator,
                    "status": "failed",
                    "annotation_count": 0,
                    "reason": str(exc),
                    "duration_seconds": round(time.perf_counter() - started, 3),
                }
            )
            continue

        annotation_count = len(results[annotator])
        if annotation_count:
            status = "produced_annotations"
            reason = None
        else:
            status = "no_annotations"
            reason = _no_annotations_reason(annotator)
        statuses.append(
            {
                "name": annotator,
                "status": status,
                "annotation_count": annotation_count,
                "reason": reason,
                "duration_seconds": round(time.perf_counter() - started, 3),
            }
        )

    return results, statuses


def flatten_annotations(results: dict[str, list[Annotation]]) -> list[Annotation]:
    annotations: list[Annotation] = []
    for source in (
        "bern2",
        "flair",
        "pubtator3",
        "bent",
        "apollo",
        "clinicalbert",
        "d4data",
        "medcat",
        *SCISPACY_ANNOTATORS,
        *STANZA_ANNOTATORS,
    ):
        annotations.extend(results.get(source, []))
    return annotations


def build_keyword_annotations(
    document_id: str,
    annotations: list[Annotation],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}

    for annotation in annotations:
        keyword = annotation.span_text.strip()
        if not keyword:
            continue

        normalized = keyword.casefold()
        key = (document_id, normalized)

        if key not in groups:
            groups[key] = {
                "document_id": document_id,
                "keyword": keyword,
                "normalized_keyword": normalized,
                "variants": [],
                "mention_count": 0,
                "annotation_count": 0,
                "annotator_count": 0,
                "labels": [],
                "canonical_ids": [],
                "mentions": [],
                "annotation_ids": [],
            }

        group = groups[key]
        group["annotation_count"] += 1
        group["annotation_ids"].append(annotation.annotation_id)
        if keyword not in group["variants"]:
            group["variants"].append(keyword)

        mention_key = (annotation.start, annotation.end)
        mention = next(
            (
                item
                for item in group["mentions"]
                if (item["start"], item["end"]) == mention_key
            ),
            None,
        )
        if mention is None:
            mention = {
                "text": keyword,
                "start": annotation.start,
                "end": annotation.end,
                "annotation_count": 0,
                "annotator_count": 0,
                "annotation_ids": [],
            }
            group["mentions"].append(mention)
        mention["annotation_count"] += 1
        mention["annotation_ids"].append(annotation.annotation_id)

    for group in groups.values():
        annotations_by_id = {
            annotation.annotation_id: annotation
            for annotation in annotations
            if annotation.annotation_id in set(group["annotation_ids"])
        }
        group["variants"] = sorted(group["variants"])
        group["annotation_ids"] = sorted(group["annotation_ids"])
        group["mention_count"] = len(group["mentions"])
        group["mentions"] = [
            _finalize_mention(item, annotations_by_id) for item in group["mentions"]
        ]
        group["mentions"] = sorted(
            group["mentions"],
            key=lambda item: (
                item["start"] is None,
                item["start"] if item["start"] is not None else -1,
                item["end"] is None,
                item["end"] if item["end"] is not None else -1,
                item["text"].casefold(),
            ),
        )
        group["annotator_count"] = len(
            {
                annotation.source
                for annotation in annotations_by_id.values()
            }
        )
        group["labels"] = sorted(
            {
                annotation.entity_type
                for annotation in annotations_by_id.values()
                if annotation.entity_type is not None
            }
        )
        group["canonical_ids"] = sorted(
            {
                canonical_id
                for annotation in annotations_by_id.values()
                for canonical_id in _flatten_values(
                    _normalize_scalar_id(annotation.canonical_id)
                )
                if canonical_id
            }
        )

    return sorted(
        groups.values(),
        key=lambda item: (
            item["document_id"],
            item["mentions"][0]["start"] is None,
            item["mentions"][0]["start"] if item["mentions"][0]["start"] is not None else -1,
            item["mentions"][0]["end"] is None,
            item["mentions"][0]["end"] if item["mentions"][0]["end"] is not None else -1,
            item["keyword"].casefold(),
        ),
    )


def filter_annotations_by_type(
    annotations: list[Annotation],
    entity_types: list[str],
) -> list[Annotation]:
    if not entity_types:
        return annotations
    allowed = {normalize_entity_type(entity_type) for entity_type in entity_types}
    return [
        annotation
        for annotation in annotations
        if normalize_entity_type(annotation.entity_type) in allowed
    ]


def document_to_dict(document: Document) -> dict[str, Any]:
    return {
        "document_id": document.document_id,
        "pmid": document.pmid,
        "title": document.title,
        "abstract": document.abstract,
        "full_text": document.full_text,
        "source": document.source,
        "year": document.year,
        "metadata": document.metadata,
    }


def _no_annotations_reason(annotator: str) -> str:
    if annotator == "bern2":
        return (
            "No annotations returned. Verify the Bern2 service is reachable "
            "and returned entities for this document."
        )
    if annotator == "flair":
        return (
            "No annotations returned. The Flair model may be unavailable/not "
            "cached, or it found no entities."
        )
    if annotator == "pubtator3":
        return (
            "No annotations returned. PubTator3 only annotates documents with a "
            "PMID or PMCID; otherwise verify it is reachable and returned entities."
        )
    if annotator == "clinicalbert":
        return (
            "No annotations returned. The ClinicalBERT model may be unavailable/not "
            "downloaded (uv sync --extra clinicalbert), or it found no entities."
        )
    if annotator == "apollo":
        return (
            "No annotations returned. The apollo model may be unavailable/not "
            "downloaded (uv sync --extra apollo), or it found no entities."
        )
    if annotator == "d4data":
        return (
            "No annotations returned. The d4data model may be unavailable/not "
            "downloaded (uv sync --extra d4data), or it found no entities."
        )
    if annotator == "medcat":
        return (
            "No annotations returned. Verify the MedCAT service is reachable "
            "(set annotators.medcat.endpoint or MEDCAT_API_URL) and returned "
            "entities for this document."
        )
    if annotator in SCISPACY_ANNOTATOR_SET:
        return (
            "No annotations returned. The scispaCy model may be unavailable/not "
            "installed (uv sync --extra scispacy, then install the model package), "
            "or it found no entities."
        )
    if annotator in STANZA_ANNOTATORS:
        return (
            "No annotations returned. The Stanza model may be unavailable/not "
            "downloaded, or it found no entities."
        )
    return "No annotations returned."


def _finalize_mention(
    mention: dict[str, Any],
    annotations_by_id: dict[str, Annotation],
) -> dict[str, Any]:
    mention["annotation_ids"] = sorted(mention["annotation_ids"])
    mention["annotator_count"] = len(
        {
            annotation.source
            for annotation_id in mention["annotation_ids"]
            if (annotation := annotations_by_id.get(annotation_id)) is not None
        }
    )
    return mention


def validate_optional_annotator_dependencies(
    config: PipelineConfig,
    *,
    flair_spans_by_document: dict[str, list[Any]] | None = None,
    clinicalbert_responses_by_document: dict[str, list[Any]] | None = None,
    apollo_responses_by_document: dict[str, list[Any]] | None = None,
    d4data_responses_by_document: dict[str, list[Any]] | None = None,
    scispacy_responses_by_document: dict[str, dict[str, list[Any]]] | None = None,
    stanza_entities_by_document: dict[str, dict[str, list[Any]]] | None = None,
) -> None:
    injected = {
        "flair": flair_spans_by_document,
        "clinicalbert": clinicalbert_responses_by_document,
        "apollo": apollo_responses_by_document,
        "d4data": d4data_responses_by_document,
        "scispacy": scispacy_responses_by_document,
        "stanza": stanza_entities_by_document,
    }
    required = [
        annotator
        for annotator in config.annotators
        if (extra := ANNOTATOR_EXTRAS.get(annotator)) is not None and injected[extra] is None
    ]
    ensure_extras(required)
    # Setup-script annotators never block the run: a missing environment leaves
    # them unavailable and the remaining annotators still run.
    ensure_tool_environments(config.annotators, config.annotator_settings)
    for annotator in required:
        extra = ANNOTATOR_EXTRAS[annotator]
        if not extra_installed(extra):
            raise ValueError(EXTRA_INSTALL_HINTS[extra])


def _load_flair_tagger(model: str) -> Any:
    try:
        import flair
        from flair.nn import Classifier
    except ImportError as exc:
        raise RuntimeError(FLAIR_INSTALL_HINT) from exc

    flair.logger.setLevel(logging.WARNING)
    return Classifier.load(model)


def _load_flair_linker(model: str) -> Any:
    try:
        import flair
        from flair.models import EntityMentionLinker
    except ImportError as exc:
        raise RuntimeError(FLAIR_INSTALL_HINT) from exc

    flair.logger.setLevel(logging.WARNING)
    return EntityMentionLinker.load(model)
