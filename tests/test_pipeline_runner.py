from __future__ import annotations

import builtins
import csv
import json
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO

import pytest


def _without_durations(statuses):
    return [{k: v for k, v in status.items() if k != "duration_seconds"} for status in statuses]


@pytest.fixture(autouse=True)
def _skip_live_retraction_lookup(monkeypatch):
    monkeypatch.setattr("bio_annotation.pipeline.runner.find_retracted_pmids", lambda pmids: [])

from bio_annotation.cli import main
from bio_annotation.annotators.pubtator3 import parse_pubtator3_response
from bio_annotation.fetch import FetchOrchestrator, PubTator3Source
from bio_annotation.fetch.input import FetchInput, FetchKind
from bio_annotation.deps import DISABLE_ENV_VAR
from bio_annotation.schemas.document import Document
from bio_annotation.pipeline_runner import (
    _aggregate_annotator_statuses,
    _load_flair_tagger,
    _read_bern2_options,
    _read_flair_options,
    _read_pubtator3_options,
    _read_stanza_options,
    build_keyword_annotations,
    filter_annotations_by_type,
    run_pipeline_from_config,
    run_selected_annotators,
    run_selected_annotators_with_status,
    write_pipeline_tsv_outputs,
)
from bio_annotation.schemas.entity import Annotation
from bio_annotation.schemas.document import Document


@dataclass
class FakeLabel:
    value: str
    score: float


@dataclass
class FakeSpan:
    text: str
    start_position: int
    end_position: int
    labels: list[FakeLabel]


@dataclass(slots=True)
class _StubEntrezSource:
    name: str = "entrez"
    supported_inputs: frozenset[FetchKind] = frozenset({"pmid", "pmid_list"})
    fields_provided: frozenset[str] = frozenset()

    def fetch(self, request: FetchInput) -> list[Document]:
        return [
            Document(
                document_id=f"PMID:{pmid}",
                pmid=pmid,
                title="PTEN regulates glioblastoma",
                abstract="PTEN is important in glioblastoma.",
                source="entrez",
                year="2024",
                metadata={
                    "pubmed_record": {
                        "pmid": pmid,
                        "pmcid": "PMC1234567",
                        "title": "PTEN regulates glioblastoma",
                        "abstract": "PTEN is important in glioblastoma.",
                        "year": "2024",
                    },
                    "pmcid": "PMC1234567",
                },
            )
            for pmid in request.pmids
        ]


def _stub_orchestrator() -> FetchOrchestrator:
    return FetchOrchestrator(sources=[_StubEntrezSource()])


def test_run_pipeline_from_config_with_pmids(tmp_path) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                'source = "entrez"',
                "",
                "[enrichment]",
                'sources = ["elinks", "crossref"]',
                "",
                "[annotators]",
                'enabled = ["bern2", "pubtator3"]',
                "",
                "[annotators.pubtator3]",
                'runtime = "remote_api"',
                'endpoint = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"',
                'format = "biocjson"',
                "timeout = 45",
                "",
                "[filters]",
                'entity_types = ["gene", "disease"]',
                "",
                "[output]",
                'path = "outputs/test.json"',
            ]
        ),
        encoding="utf-8",
    )

    payload = run_pipeline_from_config(
        config_path,
        orchestrator_factory=_stub_orchestrator,
        bern2_request_fn=lambda document: {
            "annotations": [
                {"mention": "PTEN", "span": {"begin": 0, "end": 4}, "type": "Gene", "id": "NCBIGene:5728"}
            ]
        },
        pubtator3_request_fn=lambda document: {
            "documents": [
                {
                    "passages": [
                        {
                            "annotations": [
                                {
                                    "text": "glioblastoma",
                                    "infons": {"type": "Disease", "identifier": "D005909"},
                                    "locations": [{"offset": 19, "length": 12}],
                                }
                            ]
                        }
                    ]
                }
            ]
        },
    )

    assert payload["document_count"] == 1
    assert payload["stage"] == "corpus"
    assert payload["input"]["mode"] == "pmids"
    assert payload["pipeline"]["mode"] == "ingestion_and_annotation"
    assert payload["pipeline"]["annotators_enabled"] == ["bern2", "pubtator3"]
    assert payload["documents"][0]["metadata"]["pubmed_record"]["pmcid"] == "PMC1234567"
    assert payload["annotation_summary"]["annotation_count"] == 2
    assert payload["annotator_summary"]["configured"] == ["bern2", "pubtator3"]
    assert payload["annotator_summary"]["produced"] == ["bern2", "pubtator3"]
    assert payload["annotator_summary"]["not_produced"] == []
    assert payload["document_annotations"][0]["sources"] == ["bern2", "pubtator3"]
    assert _without_durations(payload["document_annotations"][0]["annotators"]) == [
        {
            "name": "bern2",
            "status": "produced_annotations",
            "annotation_count": 1,
            "reason": None,
        },
        {
            "name": "pubtator3",
            "status": "produced_annotations",
            "annotation_count": 1,
            "reason": None,
        },
    ]
    assert len(payload["annotations"]) == 2
    assert payload["document_annotations"][0]["annotation_ids"] == [
        annotation["annotation_id"] for annotation in payload["annotations"]
    ]
    assert "annotations" not in payload["document_annotations"][0]


def _write_retraction_test_config(tmp_path, *, include_retracted: bool | None = None):
    config_path = tmp_path / "retractions.toml"
    lines = [
        "[input]",
        'mode = "pmids"',
        'pmids = ["12345678", "87654321"]',
    ]
    if include_retracted is not None:
        lines.append(f"include_retracted = {str(include_retracted).lower()}")
    lines.extend(["", "[annotators]", "enabled = []", "", "[filters]", "entity_types = []"])
    config_path.write_text("\n".join(lines), encoding="utf-8")
    return config_path


def test_user_pmids_exclude_retracted_by_default_and_report_them(tmp_path, monkeypatch) -> None:
    config_path = _write_retraction_test_config(tmp_path)
    monkeypatch.setattr(
        "bio_annotation.pipeline.runner.find_retracted_pmids",
        lambda pmids: ["12345678"],
    )
    fetched = []

    payload = run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: (
            fetched.append(pmid)
            or {"pmid": pmid, "title": f"title {pmid}", "abstract": "abstract"}
        ),
    )

    assert fetched == ["87654321"]
    assert [document["pmid"] for document in payload["documents"]] == ["87654321"]
    assert payload["input"]["retraction_check"]["excluded_pmids"] == ["12345678"]


def test_user_pmid_file_excludes_retracted_before_fetching(tmp_path, monkeypatch) -> None:
    pmid_file = tmp_path / "pmids.txt"
    pmid_file.write_text("12345678\n87654321\n", encoding="utf-8")
    config_path = tmp_path / "pmid-file.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmid_file"',
                f'pmid_file = "{pmid_file.as_posix()}"',
                "",
                "[annotators]",
                "enabled = []",
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "bio_annotation.pipeline.runner.find_retracted_pmids",
        lambda pmids: ["12345678"],
    )
    fetched = []

    payload = run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: (
            fetched.append(pmid)
            or {"pmid": pmid, "title": f"title {pmid}", "abstract": "abstract"}
        ),
    )

    assert fetched == ["87654321"]
    assert payload["input"]["retraction_check"]["submitted_pmids"] == [
        "12345678",
        "87654321",
    ]
    assert payload["input"]["retraction_check"]["excluded_pmids"] == ["12345678"]


@pytest.mark.parametrize(
    "decision, expected_pmids",
    [(False, ["87654321"]), (True, ["12345678", "87654321"])],
)
def test_include_retracted_option_prompts_and_respects_user_choice(
    tmp_path, monkeypatch, decision, expected_pmids
) -> None:
    config_path = _write_retraction_test_config(tmp_path, include_retracted=True)
    monkeypatch.setattr(
        "bio_annotation.pipeline.runner.find_retracted_pmids",
        lambda pmids: ["12345678"],
    )
    prompted = []

    payload = run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: {
            "pmid": pmid,
            "title": f"title {pmid}",
            "abstract": "abstract",
        },
        confirm_retracted_pmids=lambda pmids: prompted.extend(pmids) or decision,
    )

    assert prompted == ["12345678"]
    assert [document["pmid"] for document in payload["documents"]] == expected_pmids
    check = payload["input"]["retraction_check"]
    assert check["included_pmids"] == (["12345678"] if decision else [])
    assert check["excluded_pmids"] == ([] if decision else ["12345678"])


def test_noninteractive_include_retracted_setting_is_explicit_consent(
    tmp_path, monkeypatch
) -> None:
    from io import StringIO

    config_path = _write_retraction_test_config(tmp_path, include_retracted=True)
    monkeypatch.setattr(
        "bio_annotation.pipeline.runner.find_retracted_pmids",
        lambda pmids: ["12345678"],
    )
    monkeypatch.setattr("bio_annotation.pipeline.runner.sys.stdin", StringIO(""))
    fetched = []

    payload = run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: (
            fetched.append(pmid)
            or {"pmid": pmid, "title": f"title {pmid}", "abstract": "abstract"}
        ),
    )

    assert fetched == ["12345678", "87654321"]
    assert payload["input"]["retraction_check"]["included_pmids"] == ["12345678"]
def test_pipeline_reuses_pubtator3_fetch_response_for_annotations(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                'source = "pubtator3"',
                'fields = ["title", "abstract"]',
                "",
                "[annotators]",
                'enabled = ["pubtator3"]',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )
    response = {
        "documents": [
            {
                "id": "12345678",
                "infons": {"article-id_pmid": "12345678"},
                "passages": [
                    {
                        "offset": 0,
                        "text": "PTEN in cancer",
                        "infons": {"section_type": "TITLE"},
                        "annotations": [
                            {
                                "text": "PTEN",
                                "infons": {"type": "Gene", "identifier": "5728"},
                                "locations": [{"offset": 0, "length": 4}],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    fetch_calls: list[tuple[tuple[str, ...], str, bool]] = []
    passed_responses: list[object] = []

    class CountingClient:
        def fetch_publications_by_pmids(
            self,
            pmids: list[str] | tuple[str, ...],
            *,
            format: str,
            full: bool,
        ) -> dict[str, object]:
            fetch_calls.append((tuple(pmids), format, full))
            return response

    def fake_annotator(document: Document, *, response=None, **kwargs):
        passed_responses.append(response)
        return parse_pubtator3_response(document, response)

    monkeypatch.setattr("bio_annotation.pipeline_runner.annotate_with_pubtator3", fake_annotator)
    orchestrator = FetchOrchestrator(sources=[PubTator3Source(client=CountingClient())])

    payload = run_pipeline_from_config(
        config_path,
        orchestrator_factory=lambda: orchestrator,
    )

    assert fetch_calls == [(("12345678",), "biocjson", False)]
    assert passed_responses == [{"documents": response["documents"]}]
    assert payload["annotation_summary"]["annotation_count"] == 1
    assert payload["annotations"][0]["canonical_id"] == "5728"


def test_run_pipeline_records_annotators_without_results(tmp_path) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                "",
                "[enrichment]",
                "sources = []",
                "",
                "[annotators]",
                'enabled = ["bern2", "flair"]',
                "",
                "[annotators.bern2]",
                'base_url = "http://127.0.0.1:8888"',
                "",
                "[annotators.flair]",
                'model = "hunflair2"',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )

    payload = run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: {
            "pmid": pmid,
            "title": "PTEN regulates glioblastoma",
            "abstract": "PTEN is important in glioblastoma.",
            "year": "2024",
        },
        bern2_request_fn=lambda document: {"annotations": []},
        flair_spans_by_document={"PMID:12345678": []},
    )

    assert payload["annotator_summary"]["configured"] == ["bern2", "flair"]
    assert payload["annotator_summary"]["produced"] == []
    assert payload["annotator_summary"]["not_produced"] == ["bern2", "flair"]
    assert _without_durations(payload["document_annotations"][0]["annotators"]) == [
        {
            "name": "bern2",
            "status": "no_annotations",
            "annotation_count": 0,
            "reason": "No entities found in this document.",
        },
        {
            "name": "flair",
            "status": "no_annotations",
            "annotation_count": 0,
            "reason": "No entities found in this document.",
        },
    ]


def test_clinicalbert_empty_result_after_successful_load_is_no_entities(
    tmp_path, monkeypatch
) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                "",
                "[enrichment]",
                "sources = []",
                "",
                "[annotators]",
                'enabled = ["clinicalbert"]',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "bio_annotation.pipeline.runner.validate_optional_annotator_dependencies",
        lambda config, **kwargs: {},
    )
    monkeypatch.setattr(
        "bio_annotation.pipeline_runner._load_clinicalbert_pipeline",
        lambda model: lambda text: [],
    )
    events = []

    payload = run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: {
            "pmid": pmid,
            "title": "PTEN regulates glioblastoma",
            "abstract": "PTEN is important in glioblastoma.",
        },
        progress=events.append,
    )

    assert any(event.phase == "preflight" and event.event == "done" for event in events)
    assert _without_durations(payload["document_annotations"][0]["annotators"]) == [
        {
            "name": "clinicalbert",
            "status": "no_annotations",
            "annotation_count": 0,
            "reason": "No entities found in this document.",
        }
    ]


def test_clinicalbert_model_load_failure_reports_error_and_setup_hint(
    tmp_path, monkeypatch
) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                "",
                "[enrichment]",
                "sources = []",
                "",
                "[annotators]",
                'enabled = ["clinicalbert"]',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "bio_annotation.pipeline.runner.validate_optional_annotator_dependencies",
        lambda config, **kwargs: {},
    )

    def fail_to_load(_model):
        raise OSError("model config is missing")

    monkeypatch.setattr(
        "bio_annotation.pipeline_runner._load_clinicalbert_pipeline", fail_to_load
    )
    payload = run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: {
            "pmid": pmid,
            "title": "PTEN regulates glioblastoma",
            "abstract": "PTEN is important in glioblastoma.",
        },
    )

    status = payload["document_annotations"][0]["annotators"][0]
    assert status["status"] == "failed"
    assert "model config is missing" in status["reason"]
    assert "uv sync --extra clinicalbert" in status["reason"]


def test_cli_run_config_outputs_payload(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "text_table"',
                f'text_file = "{(tmp_path / "documents.csv").as_posix()}"',
                'format = "csv"',
                'document_id_column = "document_id"',
                'title_column = "title"',
                'abstract_column = "abstract"',
                "",
                "[enrichment]",
                "sources = []",
                "",
                "[annotators]",
                'enabled = ["flair"]',
                "",
                "[filters]",
                'entity_types = ["gene"]',
                "",
                "[output]",
                'path = "outputs/test.json"',
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "documents.csv").write_text(
        "document_id,title,abstract\n"
        "doc1,PTEN regulates glioblastoma,PTEN is important in glioblastoma.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "bio_annotation.cli.run_pipeline_from_config",
        lambda path: {
            "stage": "corpus",
            "document_count": 1,
            "pipeline": {
                "mode": "ingestion_and_annotation",
                "annotators_enabled": ["flair"],
            },
            "entity_types": ["gene"],
            "documents": [],
            "annotation_summary": {
                "annotators_enabled": ["flair"],
                "document_count": 1,
                "annotation_count": 0,
                "keyword_count": 0,
            },
            "document_annotations": [],
            "keywords": [],
            "annotations": [],
            "annotator_summary": {
                "configured": ["flair"],
                "produced": [],
                "not_produced": ["flair"],
                "failed": [],
                "annotators": [],
            },
            "output": {"path": "outputs/20260513-122400/test.json"},
        },
    )

    stream = StringIO()
    with redirect_stdout(stream):
        exit_code = main(["run-config", "--config", str(config_path)])

    output = stream.getvalue()
    assert exit_code == 0
    assert "Pipeline completed." in output
    assert "Output written to: outputs/20260513-122400/test.json" in output
    assert "Documents: 1" in output
    assert "Annotations: 0" in output
    assert "Keywords: 0" in output
    assert "Annotators with results: none" in output
    assert "Annotators without results: flair" in output
    assert not output.lstrip().startswith("{")


def test_cli_run_config_ingestion_only(tmp_path) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "corpus"',
                f'corpus_path = "{(tmp_path / "documents.json").as_posix()}"',
                "",
                "[enrichment]",
                "sources = []",
                "",
                "[annotators]",
                "enabled = []",
                "",
                "[filters]",
                "entity_types = []",
                "",
                "[output]",
                f'path = "{(tmp_path / "outputs" / "test.json").as_posix()}"',
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "documents.json").write_text(
        '{"documents":[{"document_id":"doc1","title":"PTEN regulates glioblastoma","abstract":"PTEN is important.","source":"corpus"}]}',
        encoding="utf-8",
    )

    stream = StringIO()
    with redirect_stdout(stream):
        exit_code = main(["run-config", "--config", str(config_path)])

    output = stream.getvalue()
    assert exit_code == 0
    assert "Pipeline completed." in output
    written = sorted((tmp_path / "outputs").glob("2*/results/test.json"))
    assert len(written) == 1
    assert f"Output written to: {written[0].as_posix()}" in output
    assert "Annotations: 0" in output
    assert "Annotators with results: none" in output
    assert "Annotators without results: none" in output
    assert not output.lstrip().startswith("{")


def test_read_pubtator3_options_parses_settings() -> None:
    options = _read_pubtator3_options(
        {
            "endpoint": "https://www.ncbi.nlm.nih.gov/research/pubtator3-api",
            "timeout": 45,
            "format": "biocjson",
        }
    )

    assert options == {
        "endpoint": "https://www.ncbi.nlm.nih.gov/research/pubtator3-api",
        "timeout": 45,
        "format": "biocjson",
    }


def test_read_bern2_options_prefers_endpoint_then_base_url() -> None:
    assert _read_bern2_options({"base_url": "http://bern2.local"}) == {
        "endpoint": "http://bern2.local"
    }
    assert _read_bern2_options(
        {
            "base_url": "http://bern2.local",
            "endpoint": "http://bern2.local/plain",
        }
    ) == {"endpoint": "http://bern2.local/plain"}


def test_run_selected_annotators_passes_bern2_endpoint(monkeypatch) -> None:
    document = Document(
        document_id="doc1",
        title="PTEN regulates glioblastoma",
        abstract="PTEN is important.",
        source="corpus",
    )
    calls: list[str | None] = []

    def fake_bern2(document: Document, **kwargs: object) -> list[Annotation]:
        calls.append(kwargs.get("endpoint"))
        return []

    monkeypatch.setattr("bio_annotation.pipeline_runner.annotate_with_bern2", fake_bern2)

    run_selected_annotators(
        document,
        ["bern2"],
        bern2_options={"endpoint": "http://127.0.0.1:8888"},
    )

    assert calls == ["http://127.0.0.1:8888"]


def test_read_flair_options_reads_model() -> None:
    assert _read_flair_options({"model": "hunflair2"}) == {
        "model": "hunflair2",
        "linking": False,
        "linkers": ("gene-linker", "disease-linker", "chemical-linker", "species-linker"),
    }
    assert _read_flair_options({"linking": False}) == {
        "model": None,
        "linking": False,
        "linkers": ("gene-linker", "disease-linker", "chemical-linker", "species-linker"),
    }
    assert _read_flair_options({"linkers": {"disease": "custom-disease-linker", "cell_line": "ignored"}}) == {
        "model": None,
        "linking": False,
        "linkers": ("custom-disease-linker",),
    }


def test_load_flair_tagger_reports_optional_dependency(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "flair":
            raise ImportError("No module named 'flair'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="uv sync --extra flair"):
        _load_flair_tagger("hunflair2")


def test_run_pipeline_preflights_missing_flair_dependency(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                "",
                "[annotators]",
                'enabled = ["flair"]',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )
    checked_modules: list[str] = []

    def fake_find_spec(name: str) -> object | None:
        checked_modules.append(name)
        return None

    monkeypatch.setattr("bio_annotation.deps.find_spec", fake_find_spec)
    monkeypatch.setenv(DISABLE_ENV_VAR, "1")

    with pytest.raises(ValueError, match="uv sync --extra flair"):
        run_pipeline_from_config(config_path)

    assert "flair" in checked_modules


def test_run_selected_annotators_passes_flair_model(monkeypatch) -> None:
    document = Document(
        document_id="doc1",
        title="PTEN regulates glioblastoma",
        abstract="PTEN is important.",
        source="corpus",
    )
    fake_linkers = [object()]
    calls: list[tuple[str | None, object]] = []

    def fake_flair(document: Document, **kwargs: object) -> list[Annotation]:
        calls.append((kwargs.get("model"), kwargs.get("linkers")))
        return []

    monkeypatch.setattr("bio_annotation.pipeline_runner.annotate_with_flair", fake_flair)

    run_selected_annotators(
        document,
        ["flair"],
        flair_options={"model": "hunflair2"},
        flair_linkers=fake_linkers,
    )

    assert calls == [("hunflair2", fake_linkers)]


def test_run_pipeline_preloads_flair_linkers_once(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                "",
                "[annotators]",
                'enabled = ["flair"]',
                "",
                "[annotators.flair]",
                'model = "hunflair2"',
                "linking = true",
                'linkers = ["gene-linker", "disease-linker"]',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )
    loaded_taggers: list[str] = []
    loaded_linkers: list[str] = []
    seen_linkers: list[object] = []

    def fake_find_spec(name: str) -> object | None:
        assert name in {"flair", "pyab3p"}
        return object()

    def fake_tagger_loader(model: str) -> object:
        loaded_taggers.append(model)
        return object()

    def fake_linker_loader(model: str) -> object:
        loaded_linkers.append(model)
        return model

    def fake_flair(document: Document, **kwargs: object) -> list[Annotation]:
        seen_linkers.extend(kwargs.get("linkers") or [])
        return []

    monkeypatch.setattr("bio_annotation.deps.find_spec", fake_find_spec)
    monkeypatch.setattr("bio_annotation.pipeline_runner._load_flair_tagger", fake_tagger_loader)
    monkeypatch.setattr("bio_annotation.pipeline_runner._load_flair_linker", fake_linker_loader)
    monkeypatch.setattr("bio_annotation.pipeline_runner.annotate_with_flair", fake_flair)

    run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: {
            "pmid": pmid,
            "title": "PTEN regulates glioblastoma",
            "abstract": "PTEN is important in glioblastoma.",
        },
    )

    assert loaded_taggers == ["hunflair2"]
    assert loaded_linkers == ["gene-linker", "disease-linker"]
    assert seen_linkers == ["gene-linker", "disease-linker"]


def test_run_pipeline_skips_annotator_after_failed_setup(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678", "87654321"]',
                "",
                "[annotators]",
                'enabled = ["bent"]',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )

    def unexpected_bent(document: Document, **kwargs: object) -> list[Annotation]:
        raise AssertionError("bent should be skipped after a failed setup")

    monkeypatch.setattr(
        "bio_annotation.pipeline.execution.ensure_tool_environments",
        lambda annotators, settings: {"bent": "bent setup was skipped."},
    )
    monkeypatch.setattr("bio_annotation.pipeline_runner.annotate_with_bent", unexpected_bent)

    payload = run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: {
            "pmid": pmid,
            "title": "PTEN regulates glioblastoma",
            "abstract": "PTEN is important in glioblastoma.",
        },
    )

    assert len(payload["document_annotations"]) == 2
    for document in payload["document_annotations"]:
        assert _without_durations(document["annotators"]) == [
            {
                "name": "bent",
                "status": "failed",
                "annotation_count": 0,
                "reason": "bent setup was skipped.",
            }
        ]


def test_run_pipeline_skips_annotator_after_failed_preflight(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678", "87654321"]',
                "",
                "[annotators]",
                'enabled = ["flair"]',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )
    load_attempts: list[str] = []

    def failing_tagger_loader(model: str) -> object:
        load_attempts.append(model)
        raise RuntimeError("hunflair2 download failed")

    def unexpected_flair(document: Document, **kwargs: object) -> list[Annotation]:
        raise AssertionError("flair should be skipped after a failed preflight")

    monkeypatch.setattr("bio_annotation.deps.find_spec", lambda name: object())
    monkeypatch.setattr("bio_annotation.pipeline_runner._load_flair_tagger", failing_tagger_loader)
    monkeypatch.setattr("bio_annotation.pipeline_runner.annotate_with_flair", unexpected_flair)

    payload = run_pipeline_from_config(
        config_path,
        pmid_fetcher=lambda pmid: {
            "pmid": pmid,
            "title": "PTEN regulates glioblastoma",
            "abstract": "PTEN is important in glioblastoma.",
        },
    )

    assert load_attempts == ["hunflair2"]
    for document in payload["document_annotations"]:
        assert _without_durations(document["annotators"]) == [
            {
                "name": "flair",
                "status": "failed",
                "annotation_count": 0,
                "reason": (
                    "hunflair2 download failed. The Flair annotator requires the optional "
                    "Flair dependency. Install it with: uv sync --extra flair"
                ),
            }
        ]


def test_run_selected_annotators_passes_scispacy_model(monkeypatch) -> None:
    document = Document(
        document_id="doc1",
        title="PTEN regulates glioblastoma",
        abstract="PTEN is important.",
        source="corpus",
    )
    calls: list[tuple[str, str, object]] = []

    def fake_scispacy(document: Document, **kwargs: object) -> list[Annotation]:
        calls.append((str(kwargs.get("source")), str(kwargs.get("model")), kwargs.get("linker_name")))
        return []

    monkeypatch.setattr("bio_annotation.pipeline_runner.annotate_with_scispacy", fake_scispacy)

    run_selected_annotators(
        document,
        ["scispacy_jnlpba", "scispacy_bc5cdr", "scispacy_bionlp13cg", "scispacy_scibert"],
        scispacy_options={
            "scispacy_jnlpba": {"model": "en_ner_jnlpba_md"},
            "scispacy_bc5cdr": {"model": "en_ner_bc5cdr_md"},
            "scispacy_bionlp13cg": {"model": "en_ner_bionlp13cg_md"},
            "scispacy_scibert": {"model": "en_core_sci_scibert", "linker_name": "umls"},
        },
    )

    assert calls == [
        ("scispacy_jnlpba", "en_ner_jnlpba_md", None),
        ("scispacy_bc5cdr", "en_ner_bc5cdr_md", None),
        ("scispacy_bionlp13cg", "en_ner_bionlp13cg_md", None),
        ("scispacy_scibert", "en_core_sci_scibert", "umls"),
    ]


def test_run_pipeline_preflights_missing_scispacy_dependency(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                "",
                "[annotators]",
                'enabled = ["scispacy_bc5cdr"]',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )
    checked_modules: list[str] = []

    def fake_find_spec(name: str) -> object | None:
        checked_modules.append(name)
        return None

    monkeypatch.setattr("bio_annotation.deps.find_spec", fake_find_spec)
    monkeypatch.setenv(DISABLE_ENV_VAR, "1")

    with pytest.raises(ValueError, match="uv sync --extra scispacy"):
        run_pipeline_from_config(config_path)

    assert "scispacy" in checked_modules


def test_run_selected_annotators_records_failures(monkeypatch, caplog) -> None:
    document = Document(
        document_id="doc1",
        title="PTEN regulates glioblastoma",
        abstract="PTEN is important.",
        source="corpus",
    )

    def broken_flair(document: Document, **kwargs: object) -> list[Annotation]:
        raise RuntimeError("hunflair2 is unavailable")

    monkeypatch.setattr("bio_annotation.pipeline_runner.annotate_with_flair", broken_flair)

    with caplog.at_level("WARNING", logger="bio_annotation.pipeline.progress"):
        results, statuses = run_selected_annotators_with_status(
            document,
            ["flair"],
            flair_options={"model": "hunflair2"},
        )

    assert results == {"flair": []}
    assert _without_durations(statuses) == [
        {
            "name": "flair",
            "status": "failed",
            "annotation_count": 0,
            "reason": "hunflair2 is unavailable",
        }
    ]
    assert "[1/1] Flair / HunFlair failed on doc1" in caplog.text
    assert ": hunflair2 is unavailable" in caplog.text


def test_build_keyword_annotations_groups_by_keyword_with_mentions_and_evidence() -> None:
    keywords = build_keyword_annotations(
        "doc1",
        [
            Annotation(
                annotation_id="pubtator3:1",
                source="pubtator3",
                span_text="GBM",
                start=10,
                end=13,
                entity_type="disease",
                canonical_id="MESH:D005909",
                canonical_name="Glioblastoma",
            ),
            Annotation(
                annotation_id="bern2:1",
                source="bern2",
                span_text="GBM",
                start=10,
                end=13,
                entity_type="disease",
                canonical_id="BERN:glioblastoma",
                canonical_name="Glioblastoma",
                confidence=0.94,
            ),
            Annotation(
                annotation_id="pubtator3:2",
                source="pubtator3",
                span_text="gbm",
                start=40,
                end=43,
                entity_type="disease",
                canonical_id="MESH:D005909",
                canonical_name="Glioblastoma",
            ),
            Annotation(
                annotation_id="flair:1",
                source="flair",
                span_text="tumor",
                start=55,
                end=60,
                entity_type="disease",
            ),
        ],
    )

    assert len(keywords) == 2

    gbm = keywords[0]
    assert gbm["keyword"] == "GBM"
    assert gbm["normalized_keyword"] == "gbm"
    assert gbm["variants"] == ["GBM", "gbm"]
    assert gbm["annotation_count"] == 3
    assert gbm["annotation_ids"] == ["bern2:1", "pubtator3:1", "pubtator3:2"]
    assert gbm["mention_count"] == 2
    assert gbm["annotator_count"] == 2
    assert gbm["labels"] == ["disease"]
    assert gbm["canonical_ids"] == ["BERN:glioblastoma", "MESH:D005909"]
    assert "annotators" not in gbm

    first_mention = gbm["mentions"][0]
    assert first_mention["start"] == 10
    assert first_mention["end"] == 13
    assert first_mention["annotation_count"] == 2
    assert first_mention["annotator_count"] == 2
    assert first_mention["annotation_ids"] == ["bern2:1", "pubtator3:1"]
    assert "annotators" not in first_mention


def test_pipeline_tsv_outputs_resolve_keyword_annotation_ids(tmp_path) -> None:
    annotations = [
        {
            "document_id": "doc1",
            "annotation_id": "bern2:1",
            "source": "bern2",
            "span_text": "GBM",
            "start": 10,
            "end": 13,
            "entity_type": "disease",
            "canonical_id": "BERN:glioblastoma",
            "canonical_name": "Glioblastoma",
            "confidence": 0.94,
        },
        {
            "document_id": "doc1",
            "annotation_id": "pubtator3:1",
            "source": "pubtator3",
            "span_text": "GBM",
            "start": 10,
            "end": 13,
            "entity_type": "disease",
            "canonical_id": "MESH:D005909",
            "canonical_name": "Glioblastoma",
            "confidence": None,
        },
    ]
    payload = {
        "documents": [{"document_id": "doc1", "pmid": "123", "title": "GBM study"}],
        "annotations": annotations,
        "keywords": [
            {
                "document_id": "doc1",
                "keyword": "GBM",
                "annotation_count": 2,
                "annotator_count": 2,
                "labels": ["disease"],
                "canonical_ids": ["BERN:glioblastoma", "MESH:D005909"],
                "annotation_ids": ["bern2:1", "pubtator3:1"],
                "mentions": [
                    {
                        "text": "GBM",
                        "start": 10,
                        "end": 13,
                        "annotation_count": 2,
                        "annotator_count": 2,
                        "annotation_ids": ["bern2:1", "pubtator3:1"],
                    }
                ],
            }
        ],
    }

    write_pipeline_tsv_outputs(payload, tmp_path / "results.json")

    with (tmp_path / "results.keywords.tsv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    assert [(row["keyword"], row["sources"]) for row in rows] == [("GBM", "bern2|pubtator3")]
    assert not (tmp_path / "results.keyword_annotator_evidence.tsv").exists()


def test_filter_annotations_by_type_normalizes_entity_labels() -> None:
    annotations = [
        Annotation(
            annotation_id="bern2:1",
            source="bern2",
            span_text="PTEN",
            start=0,
            end=4,
            entity_type="Gene",
        ),
        Annotation(
            annotation_id="bern2:2",
            source="bern2",
            span_text="glioblastoma",
            start=15,
            end=27,
            entity_type="Disease",
        ),
    ]

    filtered = filter_annotations_by_type(annotations, ["gene"])

    assert [annotation.entity_type for annotation in filtered] == ["Gene"]


def test_read_stanza_options_omitted_package_defaults_to_none():
    # When the config omits package, it must stay None so annotate_with_stanza
    # applies the model-specific default (mimic for i2b2/radiology, craft otherwise).
    # A stray craft default here would override that per-model choice.
    assert _read_stanza_options({})["package"] is None
    assert _read_stanza_options({"package": ""})["package"] is None
    assert _read_stanza_options({"package": "  "})["package"] is None


def test_read_stanza_options_explicit_package_is_kept():
    assert _read_stanza_options({"package": "mimic"})["package"] == "mimic"
    assert _read_stanza_options({"package": " craft "})["package"] == "craft"


def test_aggregate_annotator_statuses_sums_counts_timing_and_errors() -> None:
    statuses = [
        {"name": "bern2", "status": "produced_annotations", "annotation_count": 2, "reason": None, "duration_seconds": 0.5},
        {"name": "medcat", "status": "failed", "annotation_count": 0, "reason": "Connection refused", "duration_seconds": 0.25},
        {"name": "bern2", "status": "failed", "annotation_count": 0, "reason": "timeout", "duration_seconds": 1.0},
        {"name": "medcat", "status": "failed", "annotation_count": 0, "reason": "Connection refused", "duration_seconds": 0.25},
    ]

    assert _aggregate_annotator_statuses(statuses) == [
        {"name": "bern2", "status": "produced_annotations", "annotation_count": 2, "duration_seconds": 1.5, "failed_documents": 1, "errors": ["timeout"]},
        {"name": "medcat", "status": "failed", "annotation_count": 0, "duration_seconds": 0.5, "failed_documents": 2, "errors": ["Connection refused"]},
    ]

    
def test_each_pipeline_run_resets_medcat_failure_reporting(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                'source = "entrez"',
                "",
                "[enrichment]",
                "sources = []",
                "",
                "[annotators]",
                'enabled = ["bern2"]',
                "",
                "[filters]",
                "entity_types = []",
            ]
        ),
        encoding="utf-8",
    )
    resets: list[None] = []
    monkeypatch.setattr("bio_annotation.pipeline_runner.reset_reported_endpoints", lambda: resets.append(None))

    for _ in range(2):
        run_pipeline_from_config(
            config_path,
            orchestrator_factory=_stub_orchestrator,
            bern2_request_fn=lambda document: {"annotations": []},
        )

    assert len(resets) == 2
