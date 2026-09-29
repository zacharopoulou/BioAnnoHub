from __future__ import annotations

import json
from dataclasses import dataclass

from bio_annotation.fetch import FetchOrchestrator
from bio_annotation.fetch.input import FetchInput, FetchKind
from bio_annotation.pipeline_runner import run_pipeline_from_config
from bio_annotation.schemas.document import Document


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


def test_run_pipeline_from_config_without_annotators(tmp_path) -> None:
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "pmids"',
                'pmids = ["12345678"]',
                'source = "entrez"',
                "",
                "[annotators]",
                "enabled = []",
                "",
                "[filters]",
                "entity_types = []",
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
    )

    assert payload["document_count"] == 1
    assert payload["stage"] == "corpus"
    assert payload["input"]["mode"] == "pmids"
    assert payload["pipeline"]["mode"] == "ingestion_only"
    assert payload["pipeline"]["annotators_enabled"] == []
    assert payload["documents"][0]["metadata"]["pubmed_record"]["pmid"] == "12345678"
    assert payload["documents"][0]["metadata"]["pubmed_record"]["pmcid"] == "PMC1234567"
    assert payload["annotation_summary"]["annotation_count"] == 0
    assert payload["document_annotations"] == []
    assert payload["annotations"] == []


def test_run_pipeline_from_config_writes_output_file(tmp_path) -> None:
    output_path = tmp_path / "outputs" / "pipeline.json"
    config_path = tmp_path / "pipeline.toml"
    config_path.write_text(
        "\n".join(
            [
                "[input]",
                'mode = "corpus"',
                f'corpus_path = "{(tmp_path / "documents.json").as_posix()}"',
                "",
                "[annotators]",
                "enabled = []",
                "",
                "[filters]",
                "entity_types = []",
                "",
                "[output]",
                f'path = "{output_path.as_posix()}"',
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "documents.json").write_text(
        '{"documents":[{"document_id":"doc1","title":"PTEN regulates glioblastoma","abstract":"PTEN is important.","source":"corpus"}]}',
        encoding="utf-8",
    )

    payload = run_pipeline_from_config(config_path)

    assert payload["document_count"] == 1
    (run_dir,) = sorted(output_path.parent.glob("2*"))
    assert payload["output"]["path"] == (run_dir / "pipeline.json").as_posix()
    for name in (
        "pipeline.json",
        "pipeline.keywords.tsv",
        "pipeline.keyword_annotator_evidence.tsv",
        "pipeline.annotations.tsv",
        "pipeline.html",
        "config.toml",
        "documents.json",
        "run_manifest.json",
    ):
        assert (run_dir / name).exists(), name
    assert (output_path.parent / "latest").resolve() == run_dir.resolve()

    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == run_dir.name
    assert manifest["input"]["mode"] == "corpus"
    assert manifest["input"]["files"] == [(run_dir / "documents.json").as_posix()]
    assert manifest["document_count"] == 1
    assert manifest["files"]["html_report"] == (run_dir / "pipeline.html").as_posix()
