"""NCBI E-utilities fetch via :class:`~bio_annotation.clients.entrez.EntrezClient`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError

from bio_annotation.clients.entrez import EntrezClient
from bio_annotation.fetch.input import FetchInput, FetchKind, check_supports
from bio_annotation.schemas.document import Document

FetchRecordFn = Callable[[str], dict[str, Any]]

_CORE_FIELDS = frozenset({"pmid", "title", "abstract", "year"})
ENTREZ_BATCH_SIZE = 100
_MAX_BATCH_RETRIES = 3

logger = logging.getLogger(__name__)


class _BatchUnavailable(RuntimeError):
    """A transient Entrez outage remained after retries; stop sending requests."""


@dataclass(slots=True)
class EntrezSource:
    """PubMed records for known PMIDs (efetch). No query support."""

    name: str = "entrez"
    supported_inputs: frozenset[FetchKind] = frozenset({"pmid", "pmid_list"})
    fields_provided: frozenset[str] = frozenset(
        {
            "pmid",
            "pmcid",
            "doi",
            "title",
            "abstract",
            "structured_abstract",
            "year",
            "authors",
            "affiliations",
            "journal",
            "journal_abbrev",
            "volume",
            "issue",
            "pages",
            "language",
            "publication_type",
            "country",
            "pub_date",
            "epub_date",
            "received_date",
            "accepted_date",
            "medline_date",
            "entrez_date",
            "revision_date",
            "keywords",
            "mesh_terms",
            "chemicals",
            "gene_symbols",
            "supplemental_mesh",
            "grants",
            "elinks",
        }
    )

    timeout: int = 30
    enrichments: tuple[str, ...] = ()
    _last_request_at: float | None = field(default=None, init=False, repr=False)

    client: EntrezClient | None = None
    fetch_record: FetchRecordFn | None = field(default=None)

    def __post_init__(self) -> None:
        if self.client is None:
            object.__setattr__(self, "client", EntrezClient(timeout=self.timeout))

    def fetch(self, request: FetchInput) -> list[Document]:
        check_supports(self, request)

        effective_fields = request.fields_for(self.name)
        if self.enrichments and effective_fields is not None:
            # A configured enrichment is an explicit request to retain its result.
            effective_fields = effective_fields | {"elinks"}
        documents: list[Document] = []
        if self.fetch_record is not None:
            # Preserve the per-record injection point used by callers and tests,
            # while keeping one failed record from discarding earlier results.
            for pmid in request.pmids:
                try:
                    document = self._fetch_one(pmid, effective_fields)
                except Exception as exc:
                    logger.warning("Entrez metadata fetch failed for PMID %s: %s", pmid, exc)
                    continue
                if document is not None:
                    documents.append(document)
            return documents

        for start in range(0, len(request.pmids), ENTREZ_BATCH_SIZE):
            pmid_batch = list(request.pmids[start : start + ENTREZ_BATCH_SIZE])
            batch_documents, stop = self._fetch_batch_with_fallback(pmid_batch, effective_fields)
            documents.extend(batch_documents)
            if stop:
                logger.warning(
                    "Stopping Entrez metadata fetch after a transient error; "
                    "keeping metadata from %d successful record(s)",
                    len(documents),
                )
                break

        return documents

    def _fetch_batch_with_fallback(
        self,
        pmids: list[str],
        fields: frozenset[str] | None,
    ) -> tuple[list[Document], bool]:
        try:
            records = self._fetch_batch_with_retry(pmids)
        except _BatchUnavailable as exc:
            logger.warning(
                "Entrez could not fetch a batch of %d PMID(s): %s",
                len(pmids),
                exc,
            )
            return [], True
        except Exception as exc:
            if len(pmids) == 1:
                logger.warning("Entrez metadata fetch failed for PMID %s: %s", pmids[0], exc)
                return [], False
            midpoint = len(pmids) // 2
            logger.warning(
                "Entrez metadata batch failed for %d PMIDs; splitting and retrying: %s",
                len(pmids),
                exc,
            )
            first_documents, stop = self._fetch_batch_with_fallback(pmids[:midpoint], fields)
            if stop:
                return first_documents, True
            remaining_documents, stop = self._fetch_batch_with_fallback(pmids[midpoint:], fields)
            return first_documents + remaining_documents, stop

        records_by_pmid = {
            _coerce_str(record.get("pmid")): record
            for record in records
            if isinstance(record, dict)
            and _coerce_str(record.get("pmid")) in pmids
        }
        documents = [
            _record_to_document(
                records_by_pmid[pmid],
                fields=fields,
                fallback_pmid=pmid,
            )
            for pmid in pmids
            if pmid in records_by_pmid
        ]
        missing_pmids = [pmid for pmid in pmids if pmid not in records_by_pmid]
        if not missing_pmids:
            return documents, False

        if len(pmids) == 1:
            # A singleton response with no matching PMID cannot be split further.
            logger.warning(
                "Entrez returned no record matching requested PMID %s",
                pmids[0],
            )
            return documents, False
        logger.warning(
            "Entrez returned %d of %d requested PMID records; retrying %d missing PMID(s)",
            len(records_by_pmid),
            len(pmids),
            len(missing_pmids),
        )
        missing_documents, stop = self._fetch_batch_with_fallback(missing_pmids, fields)
        return documents + missing_documents, stop

    def _fetch_batch_with_retry(self, pmids: list[str]) -> list[dict[str, Any]]:
        assert self.client is not None
        for attempt in range(_MAX_BATCH_RETRIES + 1):
            self._respect_request_rate()
            try:
                return self.client.fetch_pubmed_many(
                    pmids,
                    enrichments=list(self.enrichments) if self.enrichments else None,
                )
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise
                if attempt >= _MAX_BATCH_RETRIES:
                    raise _BatchUnavailable(
                        f"HTTP {exc.code} fetching a batch of {len(pmids)} PMID(s)"
                    ) from exc
                delay = _retry_delay(exc, attempt)
                logger.warning(
                    "Entrez returned HTTP %d for a batch of %d PMID(s); "
                    "retrying in %.1f seconds (%d/%d)",
                    exc.code,
                    len(pmids),
                    delay,
                    attempt + 1,
                    _MAX_BATCH_RETRIES,
                )
                time.sleep(delay)
            except URLError as exc:
                if attempt >= _MAX_BATCH_RETRIES:
                    raise _BatchUnavailable(
                        f"Network error fetching a batch of {len(pmids)} PMID(s): {exc}"
                    ) from exc
                delay = float(2**attempt)
                logger.warning(
                    "Entrez network error for a batch of %d PMID(s); "
                    "retrying in %.1f seconds (%d/%d): %s",
                    len(pmids),
                    delay,
                    attempt + 1,
                    _MAX_BATCH_RETRIES,
                    exc,
                )
                time.sleep(delay)
        return []

    def _respect_request_rate(self) -> None:
        minimum_interval = 1.0 / 3.0
        now = time.monotonic()
        if self._last_request_at is not None:
            delay = minimum_interval - (now - self._last_request_at)
            if delay > 0:
                time.sleep(delay)
        self._last_request_at = time.monotonic()

    def _fetch_one(
        self,
        pmid: str,
        fields: frozenset[str] | None,
    ) -> Document | None:
        assert self.fetch_record is not None
        record = self.fetch_record(pmid)
        if not isinstance(record, dict):
            return None
        return _record_to_document(record, fields=fields, fallback_pmid=pmid)

# A. Record to Document

def _record_to_document(
    record: dict[str, Any],
    *,
    fields: frozenset[str] | None,
    fallback_pmid: str,
) -> Document:
    pmid = _coerce_str(record.get("pmid")) or _coerce_str(fallback_pmid)
    title = _coerce_str(record.get("title"))
    abstract = _coerce_str(record.get("abstract"))
    year = _coerce_optional_str(record.get("year"))
    pmcid = _coerce_optional_str(record.get("pmcid"))

    filtered = _filter_record(record, fields)

    metadata: dict[str, Any] = {"pubmed_record": filtered}
    if pmcid:
        metadata["pmcid"] = pmcid

    document_id = f"PMID:{pmid}" if pmid else f"ENTREZ:{id(record)}"

    return Document(
        document_id=document_id,
        pmid=pmid or None,
        title=title,
        abstract=abstract,
        full_text=None,
        source="entrez",
        year=year,
        metadata=metadata,
    )


def _filter_record(
    record: dict[str, Any],
    fields: frozenset[str] | None,
) -> dict[str, Any]:
    if fields is None:
        return dict(record)
    keep = fields | _CORE_FIELDS
    return {key: value for key, value in record.items() if key in keep}


# B. Internal helpers

def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _retry_delay(error: HTTPError, attempt: int) -> float:
    retry_after = error.headers.get("Retry-After") if error.headers is not None else None
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


__all__ = ["EntrezSource", "FetchRecordFn"]
