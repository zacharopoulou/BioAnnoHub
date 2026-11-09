from __future__ import annotations

from email.message import Message
from urllib.error import HTTPError
from urllib.parse import parse_qs
import xml.etree.ElementTree as ET

from bio_annotation.fetch.entrez import EntrezSource
from bio_annotation.fetch.input import FetchInput
from bio_annotation.io.readers import fetch_pubmed_records


def _article(pmid: str, title: str) -> ET.Element:
    article = ET.Element("PubmedArticle")
    citation = ET.SubElement(article, "MedlineCitation")
    ET.SubElement(citation, "PMID").text = pmid
    record = ET.SubElement(citation, "Article")
    ET.SubElement(record, "ArticleTitle").text = title
    journal = ET.SubElement(record, "Journal")
    issue = ET.SubElement(journal, "JournalIssue")
    ET.SubElement(issue, "PubDate")
    return article


def _batch_xml(*articles: ET.Element) -> bytes:
    root = ET.Element("PubmedArticleSet")
    root.extend(articles)
    return ET.tostring(root)


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.payload


def test_fetch_pubmed_records_posts_ids_and_parses_each_record(monkeypatch) -> None:
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return _Response(
            _batch_xml(
                _article("38123456", "First title"),
                _article("38123457", "Second title"),
            )
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    records = fetch_pubmed_records(["38123456", "38123457", "38123456"])

    assert [record["pmid"] for record in records] == ["38123456", "38123457"]
    assert [record["title"] for record in records] == ["First title", "Second title"]
    request, timeout = requests[0]
    assert request.method == "POST"
    assert parse_qs(request.data.decode())["id"] == ["38123456,38123457"]
    assert timeout == 15


class _FakeBatchClient:
    def __init__(self, fail_batch=None, fail_forever=False, omit_pmid=None):
        self.calls: list[list[str]] = []
        self.fail_batch = fail_batch
        self.fail_forever = fail_forever
        self.omit_pmid = omit_pmid

    def fetch_pubmed_many(self, pmids, *, enrichments=None):
        batch = list(pmids)
        self.calls.append(batch)
        if self.fail_batch is not None and batch == self.fail_batch:
            if self.fail_forever or self.calls.count(batch) == 1:
                headers = Message()
                headers["Retry-After"] = "0"
                raise HTTPError("https://eutils.ncbi.nlm.nih.gov", 429, "rate limited", headers, None)
        if "bad" in batch:
            raise ValueError("response did not contain a valid record for every PMID")
        return [
            {"pmid": pmid, "title": f"Title {pmid}", "authors": []}
            for pmid in batch
            if pmid != self.omit_pmid or len(batch) == 1
        ]


def test_entrez_source_splits_bad_batch_and_keeps_good_pmids() -> None:
    client = _FakeBatchClient()
    source = EntrezSource(client=client)

    documents = source.fetch(FetchInput.from_pmid_list(["good-1", "bad", "good-2"]))

    assert [document.pmid for document in documents] == ["good-1", "good-2"]
    assert client.calls[0] == ["good-1", "bad", "good-2"]
    assert [len(batch) for batch in client.calls[1:]] == [1, 2, 1, 1]


def test_entrez_source_retries_only_pmids_omitted_from_response() -> None:
    client = _FakeBatchClient(omit_pmid="2")
    source = EntrezSource(client=client)

    documents = source.fetch(FetchInput.from_pmid_list(["1", "2", "3"]))

    assert [document.pmid for document in documents] == ["1", "3", "2"]
    assert client.calls == [["1", "2", "3"], ["2"]]


def test_entrez_source_retries_429_then_returns_metadata(monkeypatch) -> None:
    monkeypatch.setattr("bio_annotation.fetch.entrez.time.sleep", lambda _delay: None)
    client = _FakeBatchClient(fail_batch=["38123456"])
    source = EntrezSource(client=client)

    documents = source.fetch(FetchInput.from_pmid("38123456"))

    assert [document.pmid for document in documents] == ["38123456"]
    assert len(client.calls) == 2


def test_entrez_source_keeps_prior_batch_when_later_batch_is_rate_limited(monkeypatch) -> None:
    monkeypatch.setattr("bio_annotation.fetch.entrez.time.sleep", lambda _delay: None)
    pmids = [str(index) for index in range(101)]
    client = _FakeBatchClient(fail_batch=pmids[100:], fail_forever=True)
    source = EntrezSource(client=client)

    documents = source.fetch(FetchInput.from_pmid_list(pmids))

    assert len(documents) == 100
    assert [document.pmid for document in documents] == pmids[:100]
    assert [len(batch) for batch in client.calls] == [100, 1, 1, 1, 1]


def test_entrez_source_keeps_configured_enrichment_when_fields_are_filtered() -> None:
    class _EnrichmentClient:
        def fetch_pubmed_many(self, pmids, *, enrichments=None):
            assert enrichments == ["crossref"]
            return [
                {
                    "pmid": pmid,
                    "authors": [{"name": "Ada Author"}],
                    "elinks": {"crossref_references": [{"DOI": "10.1000/example"}]},
                }
                for pmid in pmids
            ]

    source = EntrezSource(client=_EnrichmentClient(), enrichments=("crossref",))
    request = FetchInput.from_pmid(
        "1",
        fields_per_source={"entrez": frozenset({"authors"})},
    )

    (document,) = source.fetch(request)

    assert document.metadata["pubmed_record"]["authors"] == [{"name": "Ada Author"}]
    assert document.metadata["pubmed_record"]["elinks"] == {
        "crossref_references": [{"DOI": "10.1000/example"}]
    }
