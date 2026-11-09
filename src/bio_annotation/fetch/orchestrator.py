"""Source selection, merge (unite_into), and default orchestrator wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import socket
import time
from dataclasses import dataclass, replace
from typing import Iterable
from urllib.error import HTTPError, URLError

from bio_annotation.fetch.entrez import EntrezSource
from bio_annotation.fetch.europe_pmc import EuropePmcSource
from bio_annotation.fetch.input import (
    FetchInput,
    FetchSource,
    UnsupportedInputError,
)
from bio_annotation.fetch.pubtator3 import PubTator3Source
from bio_annotation.schemas.document import Document

logger = logging.getLogger(__name__)


# A. Merge helper

def unite_into(base: Document, extra: Document) -> None:
    """Merge *extra* into *base* in place; *base* wins on non-empty conflicts."""

    if not base.title.strip() and extra.title.strip():
        base.title = extra.title
    if not base.abstract.strip() and extra.abstract.strip():
        base.abstract = extra.abstract
    if not base.full_text and extra.full_text:
        base.full_text = extra.full_text
    if not base.year and extra.year:
        base.year = extra.year
    if not base.pmid and extra.pmid:
        base.pmid = extra.pmid
    for key, value in extra.metadata.items():
        if key == "origin_sources":
            continue
        base.metadata.setdefault(key, value)


# B. Orchestrators

class SourceNotFoundError(KeyError):
    """Raised when a requested source name is not registered."""


@dataclass(slots=True)
class FetchOrchestrator:
    """Select one or more registered :class:`FetchSource` implementations."""

    sources: list[FetchSource]

    def __post_init__(self) -> None:
        names = [s.name for s in self.sources]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(
                f"Duplicate source names registered: {duplicates}. "
                "Each source must have a unique 'name' attribute."
            )

    def names(self) -> list[str]:
        return [s.name for s in self.sources]

    def get(self, name: str) -> FetchSource:
        for source in self.sources:
            if source.name == name:
                return source
        raise SourceNotFoundError(
            f"No source named {name!r}. Available: {self.names()}."
        )

    def available_sources(self, request: FetchInput) -> list[str]:
        return [s.name for s in self.sources if request.kind in s.supported_inputs]

    def fetch(
        self,
        request: FetchInput,
        *,
        prefer: str | Iterable[str] | None = None,
        strict: bool = True,
    ) -> list[Document]:
        selected = self._select(request, prefer)
        if not selected:
            raise UnsupportedInputError(
                f"No registered source supports input kind {request.kind!r}. "
                f"Registered sources: {self.names()}."
            )
        if len(selected) == 1:
            return selected[0].fetch(request)
        return self._fetch_and_merge(request, selected, strict=strict)

    def _select(
        self,
        request: FetchInput,
        prefer: str | Iterable[str] | None,
    ) -> list[FetchSource]:
        if prefer is None:
            for source in self.sources:
                if request.kind in source.supported_inputs:
                    return [source]
            return []

        if isinstance(prefer, str):
            source = self.get(prefer)
            if request.kind not in source.supported_inputs:
                raise UnsupportedInputError(
                    f"Source {prefer!r} does not support input kind "
                    f"{request.kind!r}. Supported: {sorted(source.supported_inputs)}."
                )
            return [source]

        seen: set[str] = set()
        chain: list[FetchSource] = []
        for name in prefer:
            if name in seen:
                continue
            seen.add(name)
            source = self.get(name)
            if request.kind not in source.supported_inputs:
                raise UnsupportedInputError(
                    f"Source {name!r} does not support input kind "
                    f"{request.kind!r}. Supported: {sorted(source.supported_inputs)}."
                )
            chain.append(source)
        if not chain:
            raise ValueError("prefer iterable must name at least one source.")
        return chain

    def _fetch_and_merge(
        self,
        request: FetchInput,
        sources: list[FetchSource],
        *,
        strict: bool,
    ) -> list[Document]:
        merged: dict[str, Document] = {}
        order: list[str] = []
        origins: dict[str, list[str]] = {}

        for source in sources:
            try:
                results = source.fetch(request)
            except Exception as exc:
                if strict:
                    raise
                logger.warning(
                    "source %s failed during merged fetch: %s",
                    source.name,
                    exc,
                )
                continue
            for doc in results:
                if doc.document_id in merged:
                    unite_into(merged[doc.document_id], doc)
                else:
                    merged[doc.document_id] = doc
                    order.append(doc.document_id)
                origins.setdefault(doc.document_id, []).append(source.name)

        for doc_id, contributing in origins.items():
            merged[doc_id].metadata["origin_sources"] = contributing

        return [merged[doc_id] for doc_id in order]


def _blank_body(document: Document) -> bool:
    return (
        not document.title.strip()
        and not document.abstract.strip()
        and not (document.full_text or "").strip()
    )


@dataclass(slots=True)
class PubtatorFirstOrchestrator:
    """Use PubTator3 as the sole PMID text source, with optional Entrez metadata."""

    pubtator: FetchSource
    entrez: FetchSource

    def fetch(
        self,
        request: FetchInput,
        *,
        prefer: str | Iterable[str] | None = None,
    ) -> list[Document]:
        selected = [prefer] if isinstance(prefer, str) else list(prefer or ["pubtator3"])
        unknown = sorted(set(selected) - {"pubtator3", "entrez"})
        if unknown:
            raise ValueError(
                "PMID annotation runs support PubTator3 text and optional Entrez metadata; "
                f"unsupported sources: {', '.join(unknown)}."
            )
        use_entrez = "entrez" in selected

        if request.kind in {"pmcid", "pmcid_list"}:
            if use_entrez:
                raise UnsupportedInputError("Entrez metadata is available only for PMID inputs.")
            return self.pubtator.fetch(request)

        primary_request = _request_with_pubtator_text_fields(request)
        requested_pmids = list(dict.fromkeys(request.pmids))
        returned = self._fetch_pubtator_with_fallback(primary_request, requested_pmids)
        requested_set = set(requested_pmids)
        by_pmid: dict[str, Document] = {}
        for document in returned:
            pmid = _document_pmid(document)
            if pmid in requested_set and not _blank_body(document):
                by_pmid.setdefault(pmid, document)

        available_pmids = [pmid for pmid in requested_pmids if pmid in by_pmid]
        missing_pmids = [pmid for pmid in requested_pmids if pmid not in by_pmid]
        if missing_pmids:
            logger.warning(
                "Skipping %d of %d requested PMID(s): PubTator3 returned no usable text. "
                "PMIDs: %s",
                len(missing_pmids),
                len(requested_pmids),
                ", ".join(missing_pmids),
            )

        documents = [by_pmid[pmid] for pmid in available_pmids]
        if not use_entrez or not available_pmids:
            return documents

        metadata_request = _request_for_pmids(request, available_pmids)
        try:
            metadata_documents = self.entrez.fetch(metadata_request)
        except Exception as exc:
            logger.warning("Entrez metadata fetch failed; keeping PubTator3 text only: %s", exc)
            return documents

        available_pmid_set = set(available_pmids)
        metadata_by_pmid = {
            pmid: document
            for document in metadata_documents
            if (pmid := _document_pmid(document)) in available_pmid_set
        }
        missing_metadata = [pmid for pmid in available_pmids if pmid not in metadata_by_pmid]
        if missing_metadata:
            logger.warning(
                "Entrez returned no metadata for %d PubTator3 article(s): %s",
                len(missing_metadata),
                ", ".join(missing_metadata),
            )

        requested_metadata_fields = metadata_request.fields_for("entrez")
        for pmid in available_pmids:
            extra = metadata_by_pmid.get(pmid)
            if extra is not None:
                _merge_metadata_only(by_pmid[pmid], extra, requested_metadata_fields)
        return documents

    def _fetch_pubtator_with_fallback(
        self,
        request: FetchInput,
        pmids: list[str],
    ) -> list[Document]:
        if not pmids:
            return []
        try:
            return self.pubtator.fetch(_request_for_pmids(request, pmids))
        except Exception as exc:
            if _is_transient_pubtator_failure(exc):
                for attempt in range(2):
                    delay = _pubtator_retry_delay(exc, attempt)
                    logger.warning(
                        "Temporary PubTator3 error for a batch of %d PMID(s); "
                        "retrying in %.1f seconds (%d/2): %s",
                        len(pmids),
                        delay,
                        attempt + 1,
                        exc,
                    )
                    time.sleep(delay)
                    try:
                        return self.pubtator.fetch(_request_for_pmids(request, pmids))
                    except Exception as retry_exc:
                        exc = retry_exc
                        if not _is_transient_pubtator_failure(exc):
                            break
                if _is_transient_pubtator_failure(exc):
                    logger.warning(
                        "PubTator3 remained unavailable for a batch of %d PMID(s); "
                        "skipping the batch: %s",
                        len(pmids),
                        exc,
                    )
                    return []

            if len(pmids) == 1:
                logger.warning("Skipping PMID %s after PubTator3 request failure: %s", pmids[0], exc)
                return []

            midpoint = len(pmids) // 2
            logger.warning(
                "PubTator3 request failed for %d PMIDs; splitting and retrying: %s",
                len(pmids),
                exc,
            )
            return self._fetch_pubtator_with_fallback(
                request,
                pmids[:midpoint],
            ) + self._fetch_pubtator_with_fallback(request, pmids[midpoint:])


def _document_pmid(document: Document) -> str:
    pmid = str(document.pmid or "").strip()
    if pmid.upper().startswith("PMID:"):
        pmid = pmid.split(":", 1)[1].strip()
    return pmid


def _is_transient_pubtator_failure(error: Exception) -> bool:
    http_error = _find_http_error(error)
    if http_error is not None:
        return http_error.code in {408, 429} or http_error.code >= 500

    current: BaseException | None = error
    while current is not None:
        if isinstance(current, (URLError, TimeoutError, socket.timeout, json.JSONDecodeError)):
            return True
        current = current.__cause__ or current.__context__
    return False


def _find_http_error(error: BaseException) -> HTTPError | None:
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, HTTPError):
            return current
        current = current.__cause__ or current.__context__
    return None


def _pubtator_retry_delay(error: Exception, attempt: int) -> float:
    http_error = _find_http_error(error)
    retry_after = http_error.headers.get("Retry-After") if http_error and http_error.headers else None
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    return float(2**attempt)


def _request_with_pubtator_text_fields(request: FetchInput) -> FetchInput:
    fields = request.fields_for("pubtator3")
    if fields is None:
        return request
    fields_per_source = dict(request.fields_per_source or {})
    fields_per_source["pubtator3"] = fields | {"pmid", "title", "abstract"}
    return replace(request, fields_per_source=fields_per_source)


def _request_for_pmids(request: FetchInput, pmids: list[str]) -> FetchInput:
    if request.kind == "pmid" and len(pmids) == 1:
        return FetchInput.from_pmid(
            pmids[0],
            fields=request.fields,
            fields_per_source=request.fields_per_source,
        )
    return FetchInput.from_pmid_list(
        pmids,
        fields=request.fields,
        fields_per_source=request.fields_per_source,
    )


def _merge_metadata_only(base: Document, extra: Document, fields: frozenset[str] | None) -> None:
    metadata = extra.metadata if isinstance(extra.metadata, dict) else {}
    record = metadata.get("pubmed_record")
    if isinstance(record, dict):
        selected_record = (
            record
            if fields is None
            else {key: value for key, value in record.items() if key in fields or key == "pmid"}
        )
        if selected_record:
            existing = base.metadata.get("pubmed_record")
            if isinstance(existing, dict):
                for key, value in selected_record.items():
                    existing.setdefault(key, value)
            else:
                base.metadata["pubmed_record"] = selected_record

    if "pmcid" in metadata and (fields is None or "pmcid" in fields):
        base.metadata.setdefault("pmcid", metadata["pmcid"])
    if extra.year and (fields is None or "year" in fields) and not base.year:
        base.year = extra.year

    origins = base.metadata.get("origin_sources")
    if not isinstance(origins, list):
        origins = [base.source] if base.source else ["pubtator3"]
    if extra.source not in origins:
        origins.append(extra.source)
    base.metadata["origin_sources"] = origins


# C. Default wiring

@dataclass(slots=True)
class _PmidSafeDefaultFetchOrchestrator(FetchOrchestrator):
    """Keep PMID text on PubTator3 while retaining the generic PMCID fetch behavior."""

    def fetch(
        self,
        request: FetchInput,
        *,
        prefer: str | Iterable[str] | None = None,
        strict: bool = True,
    ) -> list[Document]:
        if request.kind in {"pmid", "pmid_list"}:
            return PubtatorFirstOrchestrator(
                pubtator=self.get("pubtator3"),
                entrez=self.get("entrez"),
            ).fetch(request, prefer=prefer)
        return super().fetch(request, prefer=prefer, strict=strict)


def default_fetch_orchestrator() -> FetchOrchestrator:
    """Default fetcher: PubTator3-only PMID text, optional Entrez metadata."""

    return _PmidSafeDefaultFetchOrchestrator(
        sources=[
            PubTator3Source(),
            EntrezSource(),
            EuropePmcSource(),
        ]
    )


__all__ = [
    "FetchOrchestrator",
    "PubtatorFirstOrchestrator",
    "SourceNotFoundError",
    "default_fetch_orchestrator",
    "unite_into",
]
