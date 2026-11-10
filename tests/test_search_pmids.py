from __future__ import annotations

import json
import re
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path

import pytest

from bio_annotation.cli import main
from bio_annotation.io.search import search_pubmed_pmids, write_pmids


def test_write_pmids_writes_one_per_line(tmp_path: Path) -> None:
    output = tmp_path / "pmids.txt"
    write_pmids(output, ["38123456", "31452104"])
    assert output.read_text(encoding="utf-8") == "38123456\n31452104\n"


@pytest.mark.parametrize("include_retracted", [False, True])
def test_retraction_exclusion_is_default_and_can_be_disabled(include_retracted) -> None:
    terms = []

    def fake(term):
        terms.append(term)
        return {"count": 1, "pmids": ["1"]}

    options = {"include_retracted": True} if include_retracted else {}
    assert search_pubmed_pmids("glioblastoma OR microRNA", esearch_fn=fake, **options) == ["1"]
    expected = "(glioblastoma OR microRNA)"
    if not include_retracted:
        expected += ' NOT (hasretractionin OR "Retracted Publication"[Publication Type])'
    assert terms[0].startswith(expected + " AND (")


@pytest.mark.parametrize("include_retracted", [False, True])
def test_retraction_setting_is_preserved_across_split_windows(include_retracted) -> None:
    terms = []

    def fake(term):
        terms.append(term)
        return {"count": 20_000, "pmids": []} if len(terms) == 1 else {"count": 1, "pmids": [str(len(terms))]}

    search_pubmed_pmids(
        "glioblastoma", date_from="2020/01/01", date_to="2020/01/02",
        include_retracted=include_retracted, esearch_fn=fake,
    )
    assert len(terms) == 3
    exclusion = 'NOT (hasretractionin OR "Retracted Publication"[Publication Type])'
    assert all((exclusion in term) is not include_retracted for term in terms)


def test_default_upper_date_is_today() -> None:
    terms = []

    def fake(term):
        terms.append(term)
        return {"count": 0, "pmids": []}

    search_pubmed_pmids("glioblastoma", esearch_fn=fake)
    assert f'"{date.today():%Y/%m/%d}"[Date - Publication]' in terms[0]


def test_progress_reports_splits_and_caps_the_collected_count() -> None:
    events = []
    responses = iter([
        {"count": 20_000, "pmids": []},
        {"count": 5, "pmids": ["1", "2", "3", "4", "5"]},
        {"count": 1, "pmids": ["6"]},
    ])
    pmids = search_pubmed_pmids(
        "glioblastoma", date_from="2020/01/01", date_to="2020/01/02", max_results=3,
        esearch_fn=lambda _: next(responses), progress_callback=events.append,
    )
    assert pmids == ["1", "2", "3"]
    assert [event["stage"] for event in events] == [
        "searching", "window_complete", "splitting", "searching", "window_complete", "collected",
        "searching", "window_complete", "collected",
    ]
    assert all(event["collected"] <= 3 for event in events)
    assert events[-1]["collected"] == 3


@pytest.mark.parametrize("flag, expected", [([], False), (["--include-retracted"], True)])
def test_cli_passes_retraction_option_and_keeps_progress_off_stdout(tmp_path, monkeypatch, capsys, flag, expected) -> None:
    options = {}

    def fake_search(query, **kwargs):
        options.update(kwargs)
        kwargs["progress_callback"]({"stage": "collected", "collected": 2, "max_results": 2})
        return ["1", "2"]

    monkeypatch.setattr("bio_annotation.cli.search_pubmed_pmids", fake_search)
    output = tmp_path / "pmids.txt"
    assert main(["search-pmids", "--query", "glioblastoma", "--output", str(output), *flag]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["pmid_count"] == 2
    assert "Collected 2 PMID(s) so far (output cap reached)." in captured.err
    assert options["include_retracted"] is expected
    assert output.read_text(encoding="utf-8") == "1\n2\n"


def test_cli_help_explains_retraction_override(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["search-pmids", "--help"])
    assert exc.value.code == 0
    text = capsys.readouterr().out
    assert "--include-retracted" in text
    assert "excluded by default" in text
    assert "always excluded" not in text


def test_small_query_single_call() -> None:
    calls = []

    def fake(term: str) -> dict:
        calls.append(term)
        return {"count": 3, "pmids": ["1", "2", "3"]}

    assert search_pubmed_pmids("glioblastoma", esearch_fn=fake) == ["1", "2", "3"]
    assert len(calls) == 1


def test_bisects_when_over_cap() -> None:
    responses = iter(
        [
            {"count": 25_000, "pmids": []},
            {"count": 500, "pmids": [f"a{i}" for i in range(500)]},
            {"count": 700, "pmids": [f"b{i}" for i in range(700)]},
        ]
    )
    pmids = search_pubmed_pmids(
        "glioblastoma",
        date_from="2020/01/01",
        date_to="2020/12/31",
        esearch_fn=lambda t: next(responses),
    )
    assert len(pmids) == 1200


def test_bisection_windows_are_disjoint() -> None:
    windows: list[tuple[str, str]] = []

    def fake(term: str) -> dict:
        match = re.search(r'"(\d{4}/\d{2}/\d{2})".*?"(\d{4}/\d{2}/\d{2})"', term)
        assert match is not None
        windows.append((match.group(1), match.group(2)))
        return {"count": 25_000 if len(windows) == 1 else 100, "pmids": []}

    search_pubmed_pmids(
        "glioblastoma",
        date_from="2020/01/01",
        date_to="2020/12/31",
        esearch_fn=fake,
    )

    leaves = sorted(windows[1:])
    for (_, end_a), (start_b, _) in zip(leaves, leaves[1:]):
        assert end_a < start_b


def test_raises_on_unbisectable_leaf() -> None:
    try:
        search_pubmed_pmids(
            "glioblastoma",
            date_from="2020/06/15",
            date_to="2020/06/15",
            esearch_fn=lambda t: {"count": 15_000, "pmids": []},
        )
    except ValueError as exc:
        assert "exceeds" in str(exc)
    else:
        raise AssertionError("Expected ValueError.")


def test_respects_max_results() -> None:
    pmids = search_pubmed_pmids(
        "glioblastoma",
        max_results=3,
        esearch_fn=lambda t: {"count": 5, "pmids": ["1", "2", "3", "4", "5"]},
    )
    assert pmids == ["1", "2", "3"]


def test_cli_search_pmids_writes_output(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "query_pmids.txt"
    monkeypatch.setattr(
        "bio_annotation.cli.search_pubmed_pmids",
        lambda query, **kwargs: ["38123456", "31452104"],
    )

    stream = StringIO()
    with redirect_stdout(stream):
        exit_code = main(
            [
                "search-pmids",
                "--query",
                "glioblastoma",
                "--output",
                str(output),
            ]
        )

    payload = json.loads(stream.getvalue())
    assert exit_code == 0
    assert payload["pmid_count"] == 2
    assert output.read_text(encoding="utf-8") == "38123456\n31452104\n"
