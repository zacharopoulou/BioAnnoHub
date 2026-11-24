from __future__ import annotations

import json
from urllib import parse

from bio_annotation.clients.europe_pmc import EuropePmcClient


def test_fetch_by_pmids_splits_large_queries_and_returns_all_records() -> None:
    requests: list[tuple[list[str], int]] = []

    def fake_open(http_request, timeout: int) -> bytes:
        params = parse.parse_qs(parse.urlparse(http_request.full_url).query)
        query = params["query"][0]
        pmids = [term.removeprefix("EXT_ID:") for term in query.removeprefix("(").split(") AND SRC:MED")[0].split(" OR ")]
        requests.append((pmids, int(params["pageSize"][0])))
        return json.dumps(
            {"resultList": {"result": [{"pmid": pmid} for pmid in pmids]}}
        ).encode("utf-8")

    client = EuropePmcClient(opener=fake_open)
    pmids = [str(value) for value in range(1, 206)]

    payload = client.fetch_by_pmids(pmids)

    assert [record["pmid"] for record in payload["resultList"]["result"]] == pmids
    assert [len(batch) for batch, _ in requests] == [100, 100, 5]
    assert [page_size for _, page_size in requests] == [100, 100, 5]


def test_fetch_by_pmids_honors_small_page_size_without_dropping_results() -> None:
    requests: list[list[str]] = []

    def fake_open(http_request, timeout: int) -> bytes:
        params = parse.parse_qs(parse.urlparse(http_request.full_url).query)
        query = params["query"][0]
        pmids = [term.removeprefix("EXT_ID:") for term in query.removeprefix("(").split(") AND SRC:MED")[0].split(" OR ")]
        requests.append(pmids)
        return json.dumps(
            {"resultList": {"result": [{"pmid": pmid} for pmid in pmids]}}
        ).encode("utf-8")

    client = EuropePmcClient(opener=fake_open)

    payload = client.fetch_by_pmids([str(value) for value in range(1, 9)], page_size=3)

    assert [len(batch) for batch in requests] == [3, 3, 2]
    assert len(payload["resultList"]["result"]) == 8


def test_fetch_by_pmids_keeps_successful_batches_when_one_batch_fails(caplog) -> None:
    calls = 0

    def fake_open(http_request, timeout: int) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise TimeoutError("temporary timeout")
        params = parse.parse_qs(parse.urlparse(http_request.full_url).query)
        query = params["query"][0]
        pmids = [term.removeprefix("EXT_ID:") for term in query.removeprefix("(").split(") AND SRC:MED")[0].split(" OR ")]
        return json.dumps(
            {"resultList": {"result": [{"pmid": pmid} for pmid in pmids]}}
        ).encode("utf-8")

    client = EuropePmcClient(opener=fake_open)
    pmids = [str(value) for value in range(1, 206)]

    payload = client.fetch_by_pmids(pmids)

    returned = [record["pmid"] for record in payload["resultList"]["result"]]
    assert returned == pmids[:100] + pmids[200:]
    assert "retaining results from other batches" in caplog.text
