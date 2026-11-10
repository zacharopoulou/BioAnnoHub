from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable

from bio_annotation.pipeline.progress import ProgressReporter
from bio_annotation.pipeline_config import PipelineConfig, effective_pmid_fetch_sources
from bio_annotation.schemas.document import Document

PubMedFetcher = Callable[[str], dict[str, Any]]
OrchestratorFactory = Callable[[], Any]
"""Callable returning a fetch orchestrator (bio_annotation.fetch.default_fetch_orchestrator)."""


def load_document_from_pmid(
    pmid: str,
    *,
    extra_metadata: dict[str, Any] | None = None,
    fetcher: PubMedFetcher | None = None,
    enrichment_sources: list[str] | None = None,
) -> Document:
    if fetcher is None:
        normalized_pmids = _dedupe_pmids([pmid])
        if not normalized_pmids:
            raise ValueError("PMID must not be empty.")
        normalized_pmid = normalized_pmids[0]
        documents = _fetch_pmids_from_pubtator3(
            [normalized_pmid],
            enrichment_sources=enrichment_sources,
        )
        if not documents:
            raise ValueError(
                f"PubTator3 returned no usable text for PMID {normalized_pmid}; the article was skipped."
            )
        document = documents[0]
        if extra_metadata:
            document.metadata.update(extra_metadata)
        return document

    record = fetcher(pmid)
    normalized_pmid = str(record.get("pmid") or pmid).strip()
    metadata = extra_metadata.copy() if extra_metadata else {}
    metadata["pubmed_record"] = dict(record)

    return Document(
        document_id=f"PMID:{normalized_pmid}",
        pmid=normalized_pmid,
        title=str(record.get("title") or "").strip(),
        abstract=str(record.get("abstract") or "").strip(),
        full_text=None,
        source="pubmed",
        year=_clean_optional_text(record.get("year")),
        metadata=metadata,
    )


def load_document_from_text(
    document_id: str,
    *,
    title: str = "",
    abstract: str = "",
    source: str = "text_table",
    extra_metadata: dict[str, Any] | None = None,
) -> Document:
    cleaned_document_id = str(document_id).strip()
    if not cleaned_document_id:
        raise ValueError("document_id must not be empty.")

    metadata = extra_metadata.copy() if extra_metadata else {}
    return Document(
        document_id=cleaned_document_id,
        title=title.strip(),
        abstract=abstract.strip(),
        full_text=None,
        source=source,
        metadata=metadata,
    )


def load_documents_from_pmids(
    pmids: list[str],
    *,
    fetcher: PubMedFetcher | None = None,
    enrichment_sources: list[str] | None = None,
) -> list[Document]:
    normalized_pmids = _dedupe_pmids(pmids)
    if fetcher is None:
        return _fetch_pmids_from_pubtator3(
            normalized_pmids,
            enrichment_sources=enrichment_sources,
        )

    documents: list[Document] = []
    for pmid in normalized_pmids:
        documents.append(
            load_document_from_pmid(
                pmid,
                fetcher=fetcher,
                enrichment_sources=enrichment_sources,
            )
        )
    return documents


def _fetch_pmids_from_pubtator3(
    pmids: list[str],
    *,
    enrichment_sources: list[str] | None = None,
) -> list[Document]:
    if not pmids:
        return []
    from bio_annotation.fetch import (
        EntrezSource,
        EuropePmcSource,
        FetchInput,
        PubTator3Source,
        PubtatorFirstOrchestrator,
    )

    orchestrator = PubtatorFirstOrchestrator(
        pubtator=PubTator3Source(),
        entrez=EntrezSource(enrichments=tuple(enrichment_sources or ())),
        europe_pmc=EuropePmcSource(),
    )
    request = FetchInput.from_pmid_list(pmids)
    sources = ["pubtator3", "entrez", "europe_pmc"] if enrichment_sources else ["pubtator3"]
    return orchestrator.fetch(request, prefer=sources)


def load_documents_from_pmid_file(
    path: Path,
    *,
    fetcher: PubMedFetcher | None = None,
    enrichment_sources: list[str] | None = None,
) -> list[Document]:
    pmids = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return load_documents_from_pmids(
        pmids,
        fetcher=fetcher,
        enrichment_sources=enrichment_sources,
    )


def load_documents_from_text_table(
    path: Path,
    *,
    fmt: str,
    document_id_column: str,
    title_column: str,
    abstract_column: str,
) -> list[Document]:
    delimiter = _delimiter_for_format(fmt)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"{path} must contain a header row.")
        _validate_columns(
            path,
            reader.fieldnames,
            [document_id_column, title_column, abstract_column],
        )

        documents: list[Document] = []
        for index, row in enumerate(reader, start=2):
            document_id = (row.get(document_id_column) or "").strip()
            if not document_id:
                raise ValueError(f"{path} row {index} is missing {document_id_column}.")
            title = (row.get(title_column) or "").strip()
            abstract = (row.get(abstract_column) or "").strip()
            metadata = {
                key: value
                for key, value in row.items()
                if key not in {document_id_column, title_column, abstract_column}
            }
            documents.append(
                load_document_from_text(
                    document_id,
                    title=title,
                    abstract=abstract,
                    source="text_table",
                    extra_metadata=metadata,
                )
            )
    return documents


def load_documents_from_config(
    config: PipelineConfig,
    *,
    orchestrator_factory: OrchestratorFactory | None = None,
    progress: ProgressReporter | None = None,
) -> list[Document]:
    """Load documents per input mode. PMID and PMID-file modes route through the fetch orchestrator."""

    mode = config.input_mode
    if mode in {"pmids", "pmid_file"}:
        return _load_documents_via_orchestrator(
            config,
            orchestrator_factory=orchestrator_factory,
            progress=progress,
        )
    if mode == "text_table":
        if config.text_file is None:
            raise ValueError("input.text_file must be set when input.mode = 'text_table'.")
        return load_documents_from_text_table(
            config.text_file,
            fmt=config.text_format,
            document_id_column=config.document_id_column,
            title_column=config.title_column,
            abstract_column=config.abstract_column,
        )
    if mode == "corpus":
        if config.corpus_path is None:
            raise ValueError("input.corpus_path must be set when input.mode = 'corpus'.")
        return load_corpus_documents(config.corpus_path)
    raise ValueError(f"Unsupported input mode: {mode}")


def _load_documents_via_orchestrator(
    config: PipelineConfig,
    *,
    orchestrator_factory: OrchestratorFactory | None,
    progress: ProgressReporter | None = None,
) -> list[Document]:
    pmids = _resolve_pmids_from_config(config)
    if not pmids:
        return []
    request = _build_orchestrator_request(config, pmids)
    orchestrator = _build_orchestrator(
        orchestrator_factory,
        pubtator3_full_text=config.pubtator3_full_text,
        entrez_enrichments=config.enrichment_sources,
        progress=progress,
    )
    fetch_sources = effective_pmid_fetch_sources(
        config.fetch_sources,
        config.fetch_fields,
        config.fetch_fields_per_source,
        config.enrichment_sources,
    )
    if orchestrator_factory is not None:
        # Preserve explicit injected orchestrators used by callers and local fixtures.
        fetch_sources = config.fetch_sources or ["pubtator3"]
    if len(fetch_sources) == 1:
        return orchestrator.fetch(request, prefer=fetch_sources[0])
    return orchestrator.fetch(request, prefer=list(fetch_sources))


def _resolve_pmids_from_config(config: PipelineConfig) -> list[str]:
    if config.input_mode == "pmids":
        return _dedupe_pmids(config.pmids)
    if config.pmid_file is None:
        raise ValueError("input.pmid_file must be set when input.mode = 'pmid_file'.")
    raw = [
        line.strip()
        for line in config.pmid_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return _dedupe_pmids(raw)


def _build_orchestrator_request(config: PipelineConfig, pmids: list[str]) -> Any:
    from bio_annotation.fetch import FetchInput

    fields = (
        frozenset(config.fetch_fields)
        if config.fetch_fields is not None
        else None
    )
    fields_per_source = (
        {name: frozenset(values) for name, values in config.fetch_fields_per_source.items()}
        if config.fetch_fields_per_source
        else None
    )
    fetch_sources = config.fetch_sources or ["pubtator3"]
    if "pubtator3" in config.annotators and "pubtator3" in fetch_sources:
        pubtator3_fields = (
            fields_per_source.get("pubtator3")
            if fields_per_source is not None and "pubtator3" in fields_per_source
            else fields
        )
        if pubtator3_fields is not None:
            fields_per_source = dict(fields_per_source or {})
            fields_per_source["pubtator3"] = pubtator3_fields | {"annotations"}
    if len(pmids) == 1:
        return FetchInput.from_pmid(
            pmids[0],
            fields=fields,
            fields_per_source=fields_per_source,
        )
    return FetchInput.from_pmid_list(
        pmids,
        fields=fields,
        fields_per_source=fields_per_source,
    )


def _build_orchestrator(
    factory: OrchestratorFactory | None,
    *,
    pubtator3_full_text: bool,
    entrez_enrichments: list[str] | None = None,
    progress: ProgressReporter | None = None,
) -> Any:
    if factory is not None:
        return factory()
    from bio_annotation.fetch import (
        EntrezSource,
        EuropePmcSource,
        PubTator3Source,
        PubtatorFirstOrchestrator,
    )

    return PubtatorFirstOrchestrator(
        pubtator=PubTator3Source(full_text=pubtator3_full_text),
        entrez=EntrezSource(enrichments=tuple(entrez_enrichments or ())),
        europe_pmc=EuropePmcSource(),
        progress=progress,
    )


def resolve_input_description(config: PipelineConfig) -> dict[str, Any]:
    fetch_sources = (
        effective_pmid_fetch_sources(
            config.fetch_sources,
            config.fetch_fields,
            config.fetch_fields_per_source,
            config.enrichment_sources,
        )
        if config.input_mode in {"pmids", "pmid_file"}
        else list(config.fetch_sources)
    )
    base_fetch = {
        "fetch_sources": fetch_sources,
        "fetch_fields": list(config.fetch_fields) if config.fetch_fields is not None else None,
        "fetch_fields_per_source": (
            {k: list(v) for k, v in config.fetch_fields_per_source.items()}
            if config.fetch_fields_per_source is not None
            else None
        ),
        "pubtator3_full_text": config.pubtator3_full_text,
    }
    if config.input_mode == "pmids":
        return {
            "mode": "pmids",
            "pmid_count": len(_dedupe_pmids(config.pmids)),
            "pmid_file": None,
            "text_file": None,
            "corpus_path": None,
            **base_fetch,
        }
    if config.input_mode == "pmid_file":
        return {
            "mode": "pmid_file",
            "pmid_count": None,
            "pmid_file": str(config.pmid_file) if config.pmid_file is not None else None,
            "text_file": None,
            "corpus_path": None,
            **base_fetch,
        }
    if config.input_mode == "text_table":
        return {
            "mode": "text_table",
            "pmid_count": None,
            "pmid_file": None,
            "text_file": str(config.text_file) if config.text_file is not None else None,
            "corpus_path": None,
            **base_fetch,
        }
    return {
        "mode": "corpus",
        "pmid_count": None,
        "pmid_file": None,
        "text_file": None,
        "corpus_path": str(config.corpus_path) if config.corpus_path is not None else None,
        **base_fetch,
    }


def summarize_ingestion(documents: list[Document]) -> dict[str, Any]:
    pmid_documents = sum(1 for document in documents if document.pmid)
    documents_with_pmcid = sum(
        1
        for document in documents
        if isinstance(document.metadata.get("pubmed_record"), dict)
        and document.metadata["pubmed_record"].get("pmcid")
    )
    return {
        "document_count": len(documents),
        "pmid_documents": pmid_documents,
        "documents_with_pmcid": documents_with_pmcid,
    }


def load_corpus_documents(path: Path) -> list[Document]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        records = payload.get("documents", [])
    elif isinstance(payload, list):
        records = payload
    else:
        raise ValueError(f"{path} must contain a list of documents or a top-level documents list.")

    documents: list[Document] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"{path} contains a non-object record at index {index}.")
        documents.append(_build_document_from_record(record, index=index))
    return documents


def _delimiter_for_format(fmt: str) -> str:
    cleaned = fmt.strip().lower()
    if cleaned == "csv":
        return ","
    if cleaned == "tsv":
        return "\t"
    raise ValueError(f"Unsupported text table format: {fmt}")


def _validate_columns(path: Path, fieldnames: list[str], required: list[str]) -> None:
    missing = [column for column in required if column not in fieldnames]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")


def _dedupe_pmids(pmids: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for pmid in pmids:
        cleaned = str(pmid).strip()
        if cleaned.upper().startswith("PMID:"):
            cleaned = cleaned.split(":", 1)[1].strip()
        if not cleaned:
            continue
        if cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out


def _clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _build_document_from_record(record: dict[str, Any], *, index: int) -> Document:
    metadata = record.get("metadata")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError(f"Corpus record at index {index} has non-object metadata.")

    pmid = _clean_optional_text(record.get("pmid"))
    document_id = _clean_optional_text(record.get("document_id")) or (f"PMID:{pmid}" if pmid else f"CORPUS:{index}")
    return Document(
        document_id=document_id,
        pmid=pmid,
        title=_clean_optional_text(record.get("title")) or "",
        abstract=_clean_optional_text(record.get("abstract")) or "",
        full_text=_clean_optional_text(record.get("full_text")),
        source=_clean_optional_text(record.get("source")) or "corpus",
        year=_clean_optional_text(record.get("year")),
        metadata=metadata,
    )
