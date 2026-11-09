from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

from bio_annotation.pipeline_config import SUPPORTED_ENRICHMENT_SOURCES, load_pipeline_config
from bio_annotation.pipeline.progress import ProgressReporter
from bio_annotation.terminal_ui import (
    TerminalUIAnswers,
    _prompt_domain_and_task,
    _terminal_annotator_results,
    _entity_type_choices_for,
    annotator_choices_for,
    build_terminal_ui_config_text,
    create_run_paths,
    find_unsupported_entity_types,
    parse_pmids,
    run_terminal_annotation_ui,
)
from bio_annotation.terminal_theme import run_plan_lines


def test_parse_pmids_deduplicates_common_separators() -> None:
    assert parse_pmids("123, 456\n123 789") == ["123", "456", "789"]


def test_entity_type_choices_are_annotator_aware() -> None:
    # Without a clinical annotator, no clinical types like sign_symptom are offered.
    without_clinical = [value for value, _ in _entity_type_choices_for(["pubtator3", "bern2", "flair"])]
    assert "disease" in without_clinical
    assert "sign_symptom" not in without_clinical

    # The bio types a pubtator3 selection offers, used as the expected leading prefix
    # for a clinical selection that shares pubtator3 (but not bern2's cell/dna/rna).
    bio = [value for value, _ in _entity_type_choices_for(["pubtator3"])]

    # Selecting MACCROBAT-based local models surfaces clinical types as selectable
    # choices, with the canonical bio types still listed first.
    with_apollo = _entity_type_choices_for(["pubtator3", "apollo"])
    values = [value for value, _ in with_apollo]
    expected_prefix = [value for value in bio if value in values]
    assert values[: len(expected_prefix)] == expected_prefix
    assert "sign_symptom" in values
    assert "lab_value" in values
    labels = dict(with_apollo)
    assert labels["sign_symptom"] == "Sign symptom"

    with_d4data = _entity_type_choices_for(["pubtator3", "d4data"])
    d4data_values = [value for value, _ in with_d4data]
    expected_d4data_prefix = [value for value in bio if value in d4data_values]
    assert d4data_values[: len(expected_d4data_prefix)] == expected_d4data_prefix
    assert "sign_symptom" in d4data_values
    assert "lab_value" in d4data_values


def test_find_unsupported_entity_types_reports_exact_compatibility() -> None:
    assert find_unsupported_entity_types(["bern2", "flair"], ["variant", "cell_line", "cell_type"]) == {
        "flair": ["variant", "cell_type"],
    }


def test_build_terminal_ui_config_for_plain_text(tmp_path) -> None:
    source_text = tmp_path / "doc1.txt"
    source_text.write_text("PTEN is important in glioblastoma.", encoding="utf-8")
    paths = create_run_paths(tmp_path / "out")
    answers = TerminalUIAnswers(
        input_mode="plain_text",
        pmids=[],
        pmid_file=None,
        plain_text_file=source_text,
        plain_text_document_id="doc1",
        plain_text_title="PTEN regulates glioblastoma",
        annotators=["bern2"],
        entity_types=["gene", "disease"],
    )

    config_path = paths.run_dir / "config.toml"
    config_path.write_text(build_terminal_ui_config_text(answers, paths), encoding="utf-8")
    paths.plain_text_path.parent.mkdir()
    paths.plain_text_path.write_text(
        "document_id\ttitle\tabstract\n"
        "doc1\tPTEN regulates glioblastoma\tPTEN is important in glioblastoma.\n",
        encoding="utf-8",
    )

    config = load_pipeline_config(config_path)

    assert config.input_mode == "text_table"
    assert config.text_file == paths.plain_text_path
    assert config.text_format == "tsv"
    assert config.annotators == ["bern2"]
    assert config.entity_types == ["gene", "disease"]
    assert paths.run_dir.parent == (tmp_path / "out").resolve()
    assert config.output_path == paths.run_dir.parent / "results.json"


def test_build_terminal_ui_config_for_pmid_file(tmp_path) -> None:
    pmid_file = tmp_path / "pmids.txt"
    pmid_file.write_text("123\n456\n", encoding="utf-8")
    paths = create_run_paths(tmp_path / "out")
    answers = TerminalUIAnswers(
        input_mode="pmid_file",
        pmids=[],
        pmid_file=pmid_file,
        annotators=["pubtator3"],
        entity_types=[],
        enrichment_sources=["elinks", "crossref"],
    )

    config_path = paths.run_dir / "config.toml"
    config_path.write_text(build_terminal_ui_config_text(answers, paths), encoding="utf-8")

    config = load_pipeline_config(config_path)

    assert config.input_mode == "pmid_file"
    assert config.pmid_file == pmid_file
    assert config.annotators == ["pubtator3"]
    assert config.enrichment_sources == ["elinks", "crossref"]
    assert config.annotator_settings["pubtator3"]["format"] == "biocjson"


def test_build_terminal_ui_config_includes_bern2_endpoint(tmp_path) -> None:
    paths = create_run_paths(tmp_path / "out")
    answers = TerminalUIAnswers(
        input_mode="pmids",
        pmids=["123"],
        pmid_file=None,
        annotators=["bern2"],
        entity_types=["gene"],
    )

    config_text = build_terminal_ui_config_text(answers, paths)

    assert "[annotators.bern2]" in config_text
    assert 'endpoint = "https://bern2.korea.ac.kr/plain"' in config_text


def test_build_terminal_ui_config_includes_scispacy_models(tmp_path) -> None:
    paths = create_run_paths(tmp_path / "out")
    answers = TerminalUIAnswers(
        input_mode="pmids",
        pmids=["12345678"],
        pmid_file=None,
        annotators=[
            "scispacy_jnlpba",
            "scispacy_bc5cdr",
            "scispacy_bionlp13cg",
            "scispacy_scibert",
        ],
        entity_types=[],
    )

    config_text = build_terminal_ui_config_text(answers, paths)

    assert "[annotators.scispacy_jnlpba]" in config_text
    assert 'model = "en_ner_jnlpba_md"' in config_text
    assert "[annotators.scispacy_bc5cdr]" in config_text
    assert 'model = "en_ner_bc5cdr_md"' in config_text
    assert "[annotators.scispacy_bionlp13cg]" in config_text
    assert 'model = "en_ner_bionlp13cg_md"' in config_text
    assert "[annotators.scispacy_scibert]" in config_text
    assert 'model = "en_core_sci_scibert"' in config_text
    assert 'linker_name = "umls"' in config_text


def test_run_terminal_annotation_ui_writes_reproducible_plain_text_run(tmp_path) -> None:
    source_text = tmp_path / "doc1.txt"
    source_text.write_text("PTEN is important in glioblastoma.\nEGFR is also relevant.\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    prompts = iter(
        [
            "3",  # plain text
            "2",  # raw text file
            str(source_text),
            "1",  # biomedical domain
            "1",  # NER task
            "1",  # BERN2 (PubTator3 is not offered for plain text)
            "1,2",  # Gene, Disease
            "",  # start annotation
        ]
    )
    messages: list[str] = []

    def fake_input(prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        messages.append(message)

    def fake_pipeline_run(
        config_path: Path,
        *,
        run_dir: Path | None = None,
        progress: ProgressReporter | None = None,
    ) -> dict[str, object]:
        config = load_pipeline_config(config_path)
        assert config.input_mode == "text_table"
        assert config.annotators == ["bern2"]
        assert config.entity_types == ["gene", "disease"]
        assert config.text_file is not None
        assert config.text_file.read_text(encoding="utf-8") == (
            "document_id\ttitle\tabstract\n"
            "text-1\t\tPTEN is important in glioblastoma.\n"
            "text-2\t\tEGFR is also relevant.\n"
        )
        payload = {
            "document_count": 2,
            "annotation_summary": {
                "annotators_enabled": ["bern2"],
                "document_count": 2,
                "annotation_count": 2,
            },
            "documents": [],
            "annotations": [],
            "document_annotations": [],
        }
        assert config_path == run_dir / "config.toml"
        assert config.text_file == run_dir / "inputs" / "plain_text.tsv"
        return payload

    payload = run_terminal_annotation_ui(
        runs_dir=output_dir,
        input_fn=fake_input,
        output_fn=fake_output,
        pipeline_run_fn=fake_pipeline_run,
    )

    (run_dir,) = output_dir.iterdir()
    assert (run_dir / "config.toml").exists()
    assert (run_dir / "inputs" / "plain_text.tsv").exists()
    assert payload["document_count"] == 2
    assert not any("PubTator3" in message for message in messages)
    assert any("Run complete" in message for message in messages)
    assert any("Documents TSV" in message for message in messages)
    assert any("Keywords TSV" in message for message in messages)
    assert any("Annotations TSV" in message for message in messages)


def test_run_terminal_annotation_ui_uses_one_raw_text_line_per_document(tmp_path) -> None:
    source_text = tmp_path / "doc1.txt"
    source_text.write_text("\nPTEN is important in glioblastoma.\n\nEGFR is also relevant.\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    prompts = iter(
        [
            "3",  # plain text
            "2",  # raw text file
            str(source_text),
            "1",  # biomedical domain
            "1",  # NER task
            "1",  # BERN2
            "all",  # all entity types
            "",  # start annotation
        ]
    )

    def fake_input(prompt: str) -> str:
        return next(prompts)

    def fake_pipeline_run(
        config_path: Path,
        *,
        run_dir: Path | None = None,
        progress: ProgressReporter | None = None,
    ) -> dict[str, object]:
        config = load_pipeline_config(config_path)
        assert config.text_file is not None
        assert config.text_file.read_text(encoding="utf-8") == (
            "document_id\ttitle\tabstract\n"
            "text-1\t\tPTEN is important in glioblastoma.\n"
            "text-2\t\tEGFR is also relevant.\n"
        )
        return {
            "document_count": 2,
            "annotation_summary": {"annotation_count": 0},
            "documents": [],
            "annotations": [],
            "document_annotations": [],
        }

    run_terminal_annotation_ui(
        runs_dir=output_dir,
        input_fn=fake_input,
        output_fn=lambda message: None,
        pipeline_run_fn=fake_pipeline_run,
    )

    (run_dir,) = output_dir.iterdir()
    assert (run_dir / "inputs" / "plain_text.tsv").read_text(encoding="utf-8").count("text-") == 2


def test_run_terminal_annotation_ui_uses_existing_pmid_file(tmp_path) -> None:
    output_dir = tmp_path / "out"
    pmid_file = tmp_path / "pmids.txt"
    pmid_file.write_text("123\n456\n", encoding="utf-8")
    prompts = iter(
        [
            "2",  # PMID file
            str(pmid_file),
            "2",  # no additional metadata
            "1",  # biomedical domain
            "1",  # NER task
            "1",  # pubtator3
            "all",  # all entity types
            "",  # start annotation
        ]
    )

    def fake_input(prompt: str) -> str:
        return next(prompts)

    def fake_pipeline_run(
        config_path: Path,
        *,
        run_dir: Path | None = None,
        progress: ProgressReporter | None = None,
    ) -> dict[str, object]:
        config = load_pipeline_config(config_path)
        assert config.input_mode == "pmid_file"
        assert config.pmid_file == pmid_file.resolve()
        assert config.pmid_file.read_text(encoding="utf-8") == "123\n456\n"
        assert config.enrichment_sources == []
        return {
            "document_count": 2,
            "annotation_summary": {"annotation_count": 0},
            "documents": [],
            "annotations": [],
            "document_annotations": [],
        }

    run_terminal_annotation_ui(
        runs_dir=output_dir,
        input_fn=fake_input,
        output_fn=lambda message: None,
        pipeline_run_fn=fake_pipeline_run,
    )

    (run_dir,) = output_dir.iterdir()
    assert (run_dir / "config.toml").exists()


def test_run_terminal_annotation_ui_selects_all_compatible_annotators(tmp_path) -> None:
    output_dir = tmp_path / "out"
    prompts = iter(
        [
            "1",  # PMIDs
            "123",
            "1",  # fetch additional metadata
            "1",  # biomedical domain
            "1",  # NER task
            "all",  # all compatible annotators
            "all",  # all entity types
            "",  # start annotation
        ]
    )
    seen_prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        seen_prompts.append(prompt)
        return next(prompts)

    def fake_pipeline_run(
        config_path: Path,
        *,
        run_dir: Path | None = None,
        progress: ProgressReporter | None = None,
    ) -> dict[str, object]:
        config = load_pipeline_config(config_path)
        assert config.input_mode == "pmids"
        assert config.enrichment_sources == SUPPORTED_ENRICHMENT_SOURCES
        expected = [
            annotator
            for annotator, _ in annotator_choices_for(
                domain="biomedical", input_kind="pmid", task="NER"
            )
        ]
        assert config.annotators == expected
        return {
            "document_count": 1,
            "annotation_summary": {"annotation_count": 0},
            "documents": [],
            "annotations": [],
            "document_annotations": [],
        }

    run_terminal_annotation_ui(
        runs_dir=output_dir,
        input_fn=fake_input,
        output_fn=lambda message: None,
        pipeline_run_fn=fake_pipeline_run,
    )

    assert "Choose comma-separated numbers, or type 'all' for all options: " in seen_prompts


def test_run_terminal_annotation_ui_warns_for_unsupported_entity_types(tmp_path) -> None:
    source_text = tmp_path / "doc1.txt"
    source_text.write_text("PTEN is important in glioblastoma.", encoding="utf-8")
    prompts = iter(
        [
            "3",  # plain text
            "2",  # raw text file
            str(source_text),
            "1",  # biomedical domain
            "1",  # NER task
            "1,2",  # BERN2, Flair
            "5,6",  # Variant / mutation, Cell line
            "y",
            "",  # start annotation
        ]
    )
    messages: list[str] = []

    def fake_input(prompt: str) -> str:
        return next(prompts)

    def fake_pipeline_run(
        config_path: Path,
        *,
        run_dir: Path | None = None,
        progress: ProgressReporter | None = None,
    ) -> dict[str, object]:
        config = load_pipeline_config(config_path)
        assert config.annotators == ["bern2", "flair"]
        assert config.entity_types == ["variant", "cell_line"]
        return {
            "document_count": 1,
            "annotation_summary": {"annotation_count": 0},
            "documents": [],
            "annotations": [],
            "document_annotations": [],
        }

    run_terminal_annotation_ui(
        runs_dir=tmp_path / "out",
        input_fn=fake_input,
        output_fn=messages.append,
        pipeline_run_fn=fake_pipeline_run,
    )

    assert any("Entity type compatibility warning" in message for message in messages)
    assert any("Flair / HunFlair does not produce: Variant / mutation" in message for message in messages)
    assert not any("BERN2 does not produce" in message for message in messages)


@pytest.mark.parametrize("input_kind", ["pmid", "plain_text"])
def test_domain_and_task_filters_offer_compatible_annotators(input_kind) -> None:
    def choices(domain, task):
        return {name for name, _ in annotator_choices_for(domain=domain, input_kind=input_kind, task=task)}

    clinical = {"clinicalbert", "apollo", "d4data", "medcat", "stanza_i2b2", "stanza_radiology"}
    assert choices("clinical", "both") == clinical
    assert choices("clinical", "NEN") == {"medcat"}
    biomedical_nen = {"bern2", "flair", "scispacy_scibert", "scispacy_md", "bent"}
    if input_kind == "pmid":
        biomedical_nen.add("pubtator3")
    assert choices("biomedical", "NEN") == biomedical_nen
    biomedical = choices("biomedical", "NER")
    assert biomedical.isdisjoint(clinical)
    assert "stanza_bc5cdr" in biomedical - biomedical_nen
    assert choices("biomedical", "both") == biomedical | biomedical_nen
    assert choices("both", "both") == biomedical | biomedical_nen | clinical
    assert ("pubtator3" in choices("both", "both")) == (input_kind == "pmid")


def test_selection_prompts_and_run_plan_describe_filters() -> None:
    prompts = iter(["3", "3"])
    messages = []
    domain, task, choices = _prompt_domain_and_task(
        input_fn=lambda _: next(prompts), output_fn=messages.append, input_mode="pmids"
    )
    assert (domain, task) == ("both", "both")
    assert "stanza_bc5cdr" in dict(choices)  # All tasks also includes NER-only tools.
    text = " ".join(re.sub(r"\x1b\[[0-9;]*m", "", "\n".join(messages)).split())
    assert "Filter annotators by domain" in text
    assert "Filter annotators by supported task" in text
    assert "All domains" in text
    assert "All tasks (NER and/or NEN)" in text
    plan = "\n".join(run_plan_lines(
        input_mode="PMIDs", domain="All domains", task="All tasks (NER and/or NEN)",
        annotators=["BERN2"], entity_types=[],
    ))
    assert "Domain filter" in plan
    assert "Task filter" in plan


@pytest.mark.parametrize("task, linking", [("NER", False), ("NEN", True), ("both", True)])
def test_config_saves_selection_as_comments_and_flair_linking_as_a_setting(tmp_path, task, linking) -> None:
    paths = create_run_paths(tmp_path / "runs")
    answers = TerminalUIAnswers(
        input_mode="pmids", pmids=["123"], pmid_file=None,
        annotators=["flair"], entity_types=[], domain="both", task=task,
    )
    text = build_terminal_ui_config_text(answers, paths)
    raw = tomllib.loads(text)
    assert "workflow" not in raw
    assert "# Domain: All domains" in text
    assert "# Supported task:" in text
    paths.config_path.write_text(text, encoding="utf-8")
    config = load_pipeline_config(paths.config_path)
    assert config.annotators == ["flair"]
    assert config.annotator_settings["flair"]["linking"] is linking
    assert config.annotator_settings["flair"]["linkers"]


@pytest.mark.parametrize("answers", [
    ["exit"],
    ["1", "123", "2", "1", "1", "2", "all", "exit"],
    ["1", "123", "2", "1", "1", "2", "all", "restart", "exit"],
])
def test_cancelled_setup_never_creates_a_run_or_calls_the_pipeline(tmp_path, answers) -> None:
    prompts = iter(answers)
    runs = tmp_path / "runs"

    def unexpected_pipeline(*args, **kwargs):
        pytest.fail("Cancelled setup must not run the pipeline")

    payload = run_terminal_annotation_ui(
        runs_dir=runs, input_fn=lambda _: next(prompts), output_fn=lambda _: None,
        pipeline_run_fn=unexpected_pipeline,
    )
    assert payload == {"stage": "cancelled", "cancelled": True}
    assert not runs.exists()


def test_restart_discards_previous_answers_before_creating_one_run(tmp_path) -> None:
    prompts = iter([
        "1", "123", "2", "1", "1", "2", "all", "restart",
        "1", "456", "2", "1", "2", "2", "all", "",
    ])
    runs = tmp_path / "runs"
    calls = []

    def fake_input(_):
        assert not runs.exists()  # No files are written until setup is confirmed.
        return next(prompts)

    def fake_pipeline(config_path, *, run_dir, progress=None):
        config = load_pipeline_config(config_path)
        calls.append(config)
        assert config.pmids == ["456"]
        assert config.annotators == ["bern2"]
        assert "# Supported task: NEN-capable" in config_path.read_text(encoding="utf-8")
        return {"document_count": 1, "annotation_summary": {"annotation_count": 0}}

    run_terminal_annotation_ui(
        runs_dir=runs, input_fn=fake_input, output_fn=lambda _: None,
        pipeline_run_fn=fake_pipeline,
    )
    assert len(calls) == 1
    assert len(list(runs.iterdir())) == 1


@pytest.mark.parametrize("task_choice, expects_linker_notice", [("1", False), ("2", True), ("3", True)])
def test_flair_linker_notice_matches_the_selected_task(tmp_path, task_choice, expects_linker_notice) -> None:
    prompts = iter(["1", "123", "2", "1", task_choice, "3", "all", "exit"])
    messages = []
    run_terminal_annotation_ui(
        runs_dir=tmp_path / "runs", input_fn=lambda _: next(prompts), output_fn=messages.append,
    )
    assert ("Flair entity linkers will be enabled for NEN." in messages) is expects_linker_notice
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("statuses, annotations, expected_status, expected_count", [
    (["failed"], [], "Failed (1 docs)", 0),
    (["produced_annotations", "failed"], [{"source": "bern2"}], "Partial failure (1 docs)", 1),
    (["no_annotations"], [], "No annotations", 0),
    (["produced_annotations"], [], "Completed", 0),  # All entities removed by filters.
])
def test_terminal_results_keep_execution_status_separate_from_filtered_counts(
    statuses, annotations, expected_status, expected_count,
) -> None:
    rows = _terminal_annotator_results({
        "pipeline": {"annotators_enabled": ["bern2"]},
        "annotator_summary": {"annotators": [{"name": "bern2", "status": status} for status in statuses]},
        "annotations": annotations,
    })
    assert rows == [{"annotator": "BERN2", "status": expected_status, "entity_count": expected_count}]

