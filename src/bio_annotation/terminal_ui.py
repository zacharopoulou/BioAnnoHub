from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from bio_annotation.entity_proposal.apollo_proposer import DEFAULT_APOLLO_MODEL
from bio_annotation.entity_proposal.bent_proposer import DEFAULT_BENT_PROJECT, DEFAULT_BENT_TYPES
from bio_annotation.entity_proposal.bern2_proposer import DEFAULT_BERN2_API_URL
from bio_annotation.entity_proposal.clinicalbert_proposer import DEFAULT_CLINICALBERT_MODEL
from bio_annotation.entity_proposal.d4data_proposer import DEFAULT_D4DATA_MODEL
from bio_annotation.entity_proposal.medcat_proposer import DEFAULT_MEDCAT_API_URL
from bio_annotation.entity_proposal.scispacy_proposer import (
    SCISPACY_LINKER_NAME_BY_ANNOTATOR,
    SCISPACY_MODEL_BY_ANNOTATOR,
)
from bio_annotation.entity_proposal.stanza_proposer import (
    STANZA_ANNOTATORS,
)
from bio_annotation.pipeline_runner import DEFAULT_FLAIR_LINKERS
from bio_annotation.entity_types import (
    ANNOTATOR_CHOICES,
    ANNOTATOR_CAPABILITIES,
    ANNOTATOR_DISPLAY_NAMES,
    ANNOTATOR_ENTITY_TYPES,
    ENTITY_TYPE_CHOICES,
    ENTITY_TYPE_DISPLAY_NAMES,
    annotator_domains,
    annotator_input_modes,
    annotator_tasks_for_selection,
)
from bio_annotation.pipeline_config import load_pipeline_config
from bio_annotation.pipeline_runner import (
    RUN_INPUTS_DIR,
    RUN_RESULTS_DIR,
    SUPPORTED_ANNOTATORS,
    create_run_dir,
    run_pipeline_from_config,
)
from bio_annotation.terminal_text_input import (
    is_text_table_file,
    prompt_existing_file,
    prompt_multiline_text,
    text_table_format,
    write_generated_text_table,
    write_generated_text_table_from_raw_text_file,
)
from bio_annotation.terminal_theme import (
    annotator_capability_lines,
    annotator_results_lines,
    banner_lines,
    choice_lines,
    emit,
    help_lines,
    run_plan_lines,
    run_summary_lines,
    warning_lines,
)

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]
PipelineRunFn = Callable[..., dict[str, Any]]


class _RestartSetup(Exception):
    """Signal that the interactive setup should start over."""


class _ExitSetup(Exception):
    """Signal that the user cancelled interactive setup."""


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    run_dir: Path
    config_path: Path
    results_path: Path
    manifest_path: Path
    pmids_path: Path
    plain_text_path: Path


@dataclass(frozen=True)
class TerminalUIAnswers:
    input_mode: str
    pmids: list[str]
    pmid_file: Path | None
    annotators: list[str]
    entity_types: list[str]
    plain_text_file: Path | None = None
    plain_text_source: str | None = None
    plain_text_content: str | None = None
    plain_text_document_id: str | None = None
    plain_text_title: str | None = None
    plain_text_abstract: str | None = None
    domain: str = "biomedical"
    task: str = "NER"


def run_terminal_annotation_ui(
    *,
    runs_dir: Path = Path("outputs/runs"),
    input_fn: InputFn = input,
    output_fn: OutputFn = print,
    pipeline_run_fn: PipelineRunFn = run_pipeline_from_config,
) -> dict[str, Any]:
    emit(output_fn, banner_lines())
    emit(output_fn, help_lines())
    controlled_input = _setup_control_input(input_fn)
    while True:
        try:
            answers = collect_terminal_ui_answers(
                input_fn=controlled_input,
                output_fn=output_fn,
            )
            emit(
                output_fn,
                run_plan_lines(
                    input_mode=_input_mode_label(answers.input_mode),
                    domain=_domain_label(answers.domain),
                    task=_task_label(answers.task),
                    annotators=[_annotator_label(a) for a in answers.annotators],
                    entity_types=[_entity_type_label(e) for e in answers.entity_types],
                ),
            )
            while True:
                raw = controlled_input(
                    "Press Enter to start annotation (or type 'restart' / 'exit'): "
                ).strip()
                if not raw:
                    break
                output_fn("Press Enter to start, or type 'restart' or 'exit'.")
            break
        except _RestartSetup:
            output_fn("Starting setup over.")
        except _ExitSetup:
            output_fn("Annotation setup cancelled; no run was started.")
            return {"stage": "cancelled", "cancelled": True}

    paths = create_run_paths(runs_dir)
    prepare_input_files(answers, paths)
    write_terminal_ui_config(answers, paths.config_path, paths)
    load_pipeline_config(paths.config_path)
    if "medcat" in answers.annotators:
        medcat_endpoint = medcat_config_endpoint()
        if not _medcat_service_reachable(medcat_endpoint):
            output_fn(
                f"Warning: no MedCAT service reachable at {medcat_endpoint}. "
                "Start CogStack MedCATservice (see the MedCAT section in README) "
                "or set MEDCAT_API_URL; otherwise the MedCAT step will return no "
                "annotations this run."
            )
    output_fn("")
    output_fn("Running annotation...")
    payload = pipeline_run_fn(paths.config_path, run_dir=paths.run_dir)
    output_fn("")
    emit(
        output_fn,
        run_summary_lines(
            document_count=payload.get("document_count", 0),
            annotation_count=payload.get("annotation_summary", {}).get("annotation_count", 0),
            results_path=paths.results_path,
            tsv_paths=terminal_ui_tsv_paths(paths),
            config_path=paths.config_path,
            manifest_path=paths.manifest_path,
        ),
    )
    emit(
        output_fn,
        annotator_results_lines(_terminal_annotator_results(payload)),
    )
    return payload


def _terminal_annotator_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Summarize final, filtered entity counts alongside execution outcomes."""
    pipeline = payload.get("pipeline")
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    summary = payload.get("annotator_summary")
    summary = summary if isinstance(summary, dict) else {}
    configured = pipeline.get("annotators_enabled") or summary.get("configured") or []
    if not isinstance(configured, list):
        configured = []

    rows: dict[str, dict[str, Any]] = {
        str(name): {
            "name": str(name),
            "attempted": 0,
            "failed": 0,
            "produced": 0,
            "entities": 0,
        }
        for name in configured
    }
    statuses = summary.get("annotators", [])
    if isinstance(statuses, list):
        for status in statuses:
            if not isinstance(status, dict) or not status.get("name"):
                continue
            name = str(status["name"])
            row = rows.setdefault(
                name,
                {
                    "name": name,
                    "attempted": 0,
                    "failed": 0,
                    "produced": 0,
                    "entities": 0,
                },
            )
            row["attempted"] += 1
            if status.get("status") == "failed":
                row["failed"] += 1
            elif status.get("status") == "produced_annotations":
                row["produced"] += 1

    annotations = payload.get("annotations", [])
    if isinstance(annotations, list):
        for annotation in annotations:
            if not isinstance(annotation, dict) or not annotation.get("source"):
                continue
            name = str(annotation["source"])
            row = rows.setdefault(
                name,
                {
                    "name": name,
                    "attempted": 0,
                    "failed": 0,
                    "produced": 0,
                    "entities": 0,
                },
            )
            row["entities"] += 1

    results = []
    for row in rows.values():
        attempted = row["attempted"]
        failed = row["failed"]
        produced = row["produced"]
        if attempted == 0:
            status_label = "Not run"
        elif failed == attempted:
            status_label = f"Failed ({failed} docs)"
        elif failed:
            status_label = f"Partial failure ({failed} docs)"
        elif produced == 0:
            status_label = "No annotations"
        else:
            status_label = "Completed"
        results.append(
            {
                "annotator": _annotator_label(row["name"]),
                "status": status_label,
                "entity_count": row["entities"],
            }
        )
    return results


def _setup_control_input(input_fn: InputFn) -> InputFn:
    def controlled_input(prompt: str) -> str:
        value = input_fn(prompt)
        command = value.strip().lower()
        if command in {"restart", ":restart"}:
            raise _RestartSetup
        if command in {"exit", "quit", "q", ":exit", ":q"}:
            raise _ExitSetup
        return value

    return controlled_input


def collect_terminal_ui_answers(*, input_fn: InputFn, output_fn: OutputFn) -> TerminalUIAnswers:
    mode = _prompt_choice(
        input_fn=input_fn,
        output_fn=output_fn,
        title="What do you want to annotate?",
        choices=(
            ("pmids", "PubMed articles by PMID"),
            ("pmid_file", "PubMed articles from a PMID file"),
            ("plain_text", "Plain text"),
        ),
    )
    pmids: list[str] = []
    pmid_file: Path | None = None
    text_source = text_content = None
    text_file: Path | None = None
    if mode == "pmids":
        pmids = _prompt_pmids(input_fn=input_fn)
    elif mode == "pmid_file":
        pmid_file = _prompt_existing_pmid_file(input_fn=input_fn, output_fn=output_fn)
    else:
        text_source = _prompt_choice(
            input_fn=input_fn,
            output_fn=output_fn,
            title="How do you want to provide plain text?",
            choices=(
                ("table_file", "CSV/TSV table file with document_id, title, abstract columns"),
                ("text_file", "Raw text file with one text per line"),
                ("manual_text", "Enter text in the terminal"),
            ),
        )
        if text_source in {"table_file", "text_file"}:
            text_file = prompt_existing_file(input_fn=input_fn, output_fn=output_fn)
            if text_source == "table_file" and not is_text_table_file(text_file):
                raise ValueError("Plain text table files must use .csv or .tsv extension.")
        else:
            text_content = prompt_multiline_text(input_fn=input_fn, output_fn=output_fn)
    domain, task, annotator_choices = _prompt_domain_and_task(
        input_fn=input_fn,
        output_fn=output_fn,
        input_mode=mode,
    )
    annotators = _prompt_multi_choice(
        input_fn=input_fn,
        output_fn=output_fn,
        title="Choose annotators",
        choices=annotator_choices,
        default_values=[],
        # Require an explicit annotator choice, including when only optional
        # local models or services are compatible with the selected workflow.
        allow_empty=False,
        allow_all=True,
        validate_values=lambda selected: _validate_selected_annotators(
            selected, domain=domain, task=task, input_mode=mode
        ),
    )
    emit(
        output_fn,
        annotator_capability_lines(
            _annotator_capability_rows(annotators, task=task)
        ),
    )
    entity_types = _prompt_entity_types(input_fn=input_fn, output_fn=output_fn, annotators=annotators)
    return TerminalUIAnswers(
        mode,
        pmids,
        pmid_file,
        annotators,
        entity_types,
        plain_text_file=text_file,
        plain_text_source=text_source,
        plain_text_content=text_content,
        domain=domain,
        task=task,
    )


def _prompt_domain_and_task(
    *, input_fn: InputFn, output_fn: OutputFn, input_mode: str
) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    input_kind = "plain_text" if input_mode == "plain_text" else "pmid"
    while True:
        domain = _prompt_choice(
            input_fn=input_fn,
            output_fn=output_fn,
            title="Choose the text domain",
            choices=(
                ("biomedical", "Biomedical literature and research text"),
                ("clinical", "Clinical notes and reports"),
                ("both", "Biomedical and clinical annotators"),
            ),
        )
        task = _prompt_choice(
            input_fn=input_fn,
            output_fn=output_fn,
            title="Choose the annotation task",
            choices=(
                ("NER", "Named entity recognition (NER)"),
                ("NEN", "Named entity normalization (NEN)"),
                ("both", "NER, NEN, or both"),
            ),
        )
        annotator_choices = annotator_choices_for(
            domain=domain,
            input_kind=input_kind,
            task=task,
        )
        if annotator_choices:
            return domain, task, annotator_choices
        emit(
            output_fn,
            warning_lines(
                "No compatible annotators",
                [
                    f"No annotator supports {domain} {_task_label(task)} for this input type. "
                    "Choose a different domain or task."
                ],
            ),
        )


def annotator_choices_for(
    *, domain: str, input_kind: str, task: str
) -> tuple[tuple[str, str], ...]:
    required_tasks = {"NER", "NEN"} if task == "both" else {task}
    choices: list[tuple[str, str]] = []
    for annotator, label in ANNOTATOR_CHOICES:
        capability = ANNOTATOR_CAPABILITIES[annotator]
        if not _domain_matches_capability(domain, capability.domains) or input_kind not in capability.input_modes:
            continue
        tasks = set(
            annotator_tasks_for_selection(
                annotator,
                # The terminal enables default linkers whenever NEN is requested.
                flair_linking=task in {"NEN", "both"},
            )
        )
        if required_tasks.intersection(tasks):
            choices.append((annotator, label))
    return tuple(choices)


def _annotator_capability_rows(
    annotators: list[str], *, task: str
) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for annotator in annotators:
        capability = ANNOTATOR_CAPABILITIES[annotator]
        domains = ", ".join(_domain_label(domain) for domain in capability.domains)
        inputs = ", ".join(
            "PMID articles" if mode == "pmid" else "plain text"
            for mode in capability.input_modes
        )
        tasks = ", ".join(
            annotator_tasks_for_selection(
                annotator,
                flair_linking=task in {"NEN", "both"},
            )
        )
        entity_types = ", ".join(
            dict.fromkeys(
                _entity_type_label(entity_type)
                for entity_type in capability.entity_types
            )
        ) or "Defined by the loaded model"
        rows.append(
            (
                capability.label,
                domains,
                inputs,
                tasks,
                entity_types,
            )
        )
    return rows


def create_run_paths(runs_dir: Path, *, now: datetime | None = None) -> RunPaths:
    run_dir = create_run_dir(runs_dir.expanduser().resolve(), now=now)
    return RunPaths(
        run_dir.name,
        run_dir,
        run_dir / "config.toml",
        run_dir / RUN_RESULTS_DIR / "results.json",
        run_dir / "run_manifest.json",
        run_dir / RUN_INPUTS_DIR / "pmids.txt",
        run_dir / RUN_INPUTS_DIR / "plain_text.tsv",
    )


def prepare_input_files(answers: TerminalUIAnswers, paths: RunPaths) -> None:
    if answers.input_mode == "pmid_file" and answers.pmid_file is None:
        raise ValueError("PMID file input mode requires a PMID file path.")
    if answers.input_mode == "plain_text" and not _uses_existing_text_table(answers):
        if answers.plain_text_source == "text_file" and answers.plain_text_file is not None:
            write_generated_text_table_from_raw_text_file(paths.plain_text_path, answers.plain_text_file)
        else:
            text = _plain_text_content(answers)
            write_generated_text_table(paths.plain_text_path, text)


def write_terminal_ui_config(answers: TerminalUIAnswers, config_path: Path, paths: RunPaths) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(build_terminal_ui_config_text(answers, paths), encoding="utf-8")


def medcat_config_endpoint() -> str:
    return os.environ.get("MEDCAT_API_URL") or DEFAULT_MEDCAT_API_URL


def _medcat_service_reachable(endpoint: str, *, timeout: float = 3.0) -> bool:
    """Best-effort check that a MedCATservice answers at the endpoint's /api/info."""
    from urllib import request as urlrequest

    base = endpoint.rstrip("/")
    if base.endswith("/api/process"):
        base = base[: -len("/api/process")]
    try:
        with urlrequest.urlopen(base + "/api/info", timeout=timeout):
            return True
    except Exception:
        return False


def build_terminal_ui_config_text(answers: TerminalUIAnswers, paths: RunPaths) -> str:
    lines = [
        "[workflow]",
        f"domain = {_toml_string(answers.domain)}",
        f"task = {_toml_string(answers.task)}",
        "",
        "[input]",
    ]
    if answers.input_mode == "pmids":
        lines += ['mode = "pmids"', f"pmids = {_toml_string_list(answers.pmids)}"]
    elif answers.input_mode == "pmid_file":
        if answers.pmid_file is None:
            raise ValueError("PMID file input mode requires a PMID file path.")
        lines += ['mode = "pmid_file"', f"pmid_file = {_toml_string(str(answers.pmid_file))}"]
    elif answers.input_mode == "plain_text":
        text_file = _plain_text_config_file(answers, paths)
        lines += [
            'mode = "text_table"',
            f"text_file = {_toml_string(str(text_file))}",
            f"format = {_toml_string(text_table_format(text_file))}",
            'document_id_column = "document_id"',
            'title_column = "title"',
            'abstract_column = "abstract"',
        ]
    else:
        raise ValueError(f"Unsupported terminal UI input mode: {answers.input_mode}")
    lines += ["", "[enrichment]", "sources = []", "", "[annotators]", f"enabled = {_toml_string_list(answers.annotators)}"]
    if "bern2" in answers.annotators:
        lines += [
            "",
            "[annotators.bern2]",
            'runtime = "remote_api"',
            f"endpoint = {_toml_string(DEFAULT_BERN2_API_URL)}",
            "timeout = 30",
        ]
    if "pubtator3" in answers.annotators:
        lines += [
            "",
            "[annotators.pubtator3]",
            'runtime = "remote_api"',
            'endpoint = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"',
            'format = "biocjson"',
            "timeout = 60",
        ]
    if "bent" in answers.annotators:
        lines += ["", "[annotators.bent]", 'runtime = "local_subprocess"', 'mode = "ner_nel"', f"project = {_toml_string(DEFAULT_BENT_PROJECT)}", "timeout = 900", "", "[annotators.bent.types]"]
        lines += [f"{entity_type} = {_toml_string(kb)}" for entity_type, kb in DEFAULT_BENT_TYPES.items()]
    if "clinicalbert" in answers.annotators:
        lines += ["", "[annotators.clinicalbert]", 'runtime = "local_model"', f"model = {_toml_string(DEFAULT_CLINICALBERT_MODEL)}"]
    if "apollo" in answers.annotators:
        lines += ["", "[annotators.apollo]", 'runtime = "local_model"', f"model = {_toml_string(DEFAULT_APOLLO_MODEL)}"]
    if "d4data" in answers.annotators:
        lines += ["", "[annotators.d4data]", 'runtime = "local_model"', f"model = {_toml_string(DEFAULT_D4DATA_MODEL)}"]
    if "flair" in answers.annotators:
        lines += [
            "",
            "[annotators.flair]",
            'runtime = "local_model"',
            'model = "hunflair2"',
            f"linking = {str(answers.task in {'NEN', 'both'}).lower()}",
            f"linkers = {_toml_string_list(DEFAULT_FLAIR_LINKERS.values())}",
        ]
    if "medcat" in answers.annotators:
        lines += ["", "[annotators.medcat]", 'runtime = "remote_api"', f"endpoint = {_toml_string(medcat_config_endpoint())}", "min_acc = 0.3"]
    for annotator in SCISPACY_MODEL_BY_ANNOTATOR:
        if annotator in answers.annotators:
            lines += [
                "",
                f"[annotators.{annotator}]",
                'runtime = "local_model"',
                f"model = {_toml_string(SCISPACY_MODEL_BY_ANNOTATOR[annotator])}",
            ]
            if annotator in SCISPACY_LINKER_NAME_BY_ANNOTATOR:
                lines += [
                    f"linker_name = {_toml_string(SCISPACY_LINKER_NAME_BY_ANNOTATOR[annotator])}"
                ]
    for stanza_annotator in STANZA_ANNOTATORS:
        if stanza_annotator in answers.annotators:
            lines += ["", f"[annotators.{stanza_annotator}]", 'runtime = "local"']
    lines += ["", "[filters]", f"entity_types = {_toml_string_list(answers.entity_types)}", "", "[output]", f"path = {_toml_string(str(paths.run_dir.parent / paths.results_path.name))}", ""]
    return "\n".join(lines)


def terminal_ui_tsv_paths(paths: RunPaths) -> dict[str, Path]:
    return {
        "Keywords TSV": paths.results_path.with_name(f"{paths.results_path.stem}.keywords.tsv"),
        "Annotations TSV": paths.results_path.with_name(f"{paths.results_path.stem}.annotations.tsv"),
    }


def write_plain_text_table(path: Path, *, document_id: str, title: str, abstract: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["document_id", "title", "abstract"], delimiter="\t")
        writer.writeheader()
        writer.writerow({"document_id": document_id, "title": title, "abstract": abstract})


def find_unsupported_entity_types(annotators: list[str], entity_types: list[str]) -> dict[str, list[str]]:
    if not entity_types:
        return {}
    return {
        a: missing
        for a in annotators
        if ANNOTATOR_ENTITY_TYPES.get(a)
        and (missing := [e for e in entity_types if e not in ANNOTATOR_ENTITY_TYPES[a]])
    }


def _entity_type_choices_for(annotators: list[str]) -> tuple[tuple[str, str], ...]:
    # Offer the entity types the selected annotators actually produce, so a
    # clinical annotator like ClinicalBERT adds its own categories (problem /
    # test / treatment) to the menu. Canonical types stay first, in their usual
    # order; extra annotator-specific types follow.
    available: set[str] = set()
    for annotator in annotators:
        available |= ANNOTATOR_ENTITY_TYPES.get(annotator, set())
    if not available:
        return ENTITY_TYPE_CHOICES
    canonical_order = [value for value, _ in ENTITY_TYPE_CHOICES]
    ordered = [value for value in canonical_order if value in available]
    ordered.extend(sorted(available - set(canonical_order)))
    return tuple((value, _entity_type_label(value)) for value in ordered)


def _prompt_entity_types(*, input_fn: InputFn, output_fn: OutputFn, annotators: list[str]) -> list[str]:
    choices = _entity_type_choices_for(annotators)
    if "medcat" in annotators:
        output_fn(
            "MedCAT entity labels depend on its loaded model pack and cannot be "
            "listed in advance. Type 'all' to retain every returned label."
        )
    while True:
        entity_types = _prompt_multi_choice(
            input_fn=input_fn,
            output_fn=output_fn,
            title="Choose entity types to include",
            choices=choices,
            default_values=[],
            allow_all=True,
            all_returns_empty=True,
        )
        if entity_types and "medcat" in annotators:
            emit(
                output_fn,
                warning_lines(
                    "MedCAT filter compatibility is model-dependent",
                    [
                        "Selected filters are matched against MedCAT's returned entity "
                        "labels. Some model packs may use labels outside this list; "
                        "type 'all' to retain every MedCAT result."
                    ],
                ),
            )
            if not _prompt_yes_no(
                input_fn=input_fn,
                prompt="Continue with these filters for MedCAT? [y/N]: ",
            ):
                continue
        unsupported = find_unsupported_entity_types(annotators, entity_types)
        if not unsupported:
            return entity_types
        messages = [
            f"{_annotator_label(annotator)} does not produce: {', '.join(_entity_type_label(e) for e in missing)}"
            for annotator, missing in unsupported.items()
        ]
        emit(output_fn, warning_lines("Entity type compatibility warning", messages))
        if _prompt_yes_no(input_fn=input_fn, prompt="Continue with this selection? [y/N]: "):
            return entity_types


def _prompt_choice(
    *,
    input_fn: InputFn,
    output_fn: OutputFn,
    title: str,
    choices: tuple[tuple[str, str], ...],
    default_value: str | None = None,
) -> str:
    output_fn("")
    default_indexes = [i for i, (value, _) in enumerate(choices, start=1) if value == default_value]
    emit(output_fn, choice_lines(title, choices, default_indexes=default_indexes))
    prompt = f"Choose one [default: {default_indexes[0]}]: " if default_indexes else "Choose one: "
    while True:
        raw = input_fn(prompt).strip()
        if not raw and default_value is not None:
            return default_value
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1][0]
        default_hint = f" or press Enter for default ({default_indexes[0]})" if default_indexes else ""
        output_fn(f"Please choose one of: {', '.join(str(i) for i in range(1, len(choices) + 1))}{default_hint}")


def _prompt_multi_choice(
    *,
    input_fn: InputFn,
    output_fn: OutputFn,
    title: str,
    choices: tuple[tuple[str, str], ...],
    default_values: list[str],
    allow_empty: bool = False,
    allow_all: bool = False,
    all_returns_empty: bool = False,
    validate_values: Callable[[list[str]], None] | None = None,
) -> list[str]:
    output_fn("")
    default_indexes = [i for i, (v, _) in enumerate(choices, start=1) if v in default_values]
    emit(output_fn, choice_lines(title, choices, default_indexes=default_indexes))
    default_hint = f" [default: {', '.join(str(i) for i in default_indexes)}]" if default_indexes else ""
    all_hint = ", or type 'all' for all options" if allow_all else ""
    while True:
        raw = input_fn(f"Choose comma-separated numbers{all_hint}{default_hint}: ").strip()
        if allow_all and raw.lower() == "all":
            selected = [] if all_returns_empty else [value for value, _ in choices]
            if validate_values:
                validate_values(selected)
            return selected
        if not raw and default_values:
            selected = list(default_values)
            if validate_values:
                validate_values(selected)
            return selected
        if not raw and allow_empty:
            return []
        selected: list[str] = []
        ok = True
        for item in re.split(r"[,\s]+", raw):
            if not item:
                continue
            if not item.isdigit() or not 1 <= int(item) <= len(choices):
                ok = False
                break
            value = choices[int(item) - 1][0]
            if value not in selected:
                selected.append(value)
        if ok and (selected or allow_empty):
            if validate_values:
                validate_values(selected)
            return selected
        output_fn("Please choose valid comma-separated numbers.")


def _validate_selected_annotators(
    annotators: list[str],
    *,
    domain: str | None = None,
    task: str | None = None,
    input_mode: str | None = None,
) -> None:
    unsupported = [a for a in annotators if a not in SUPPORTED_ANNOTATORS]
    if unsupported:
        raise ValueError(f"Unsupported annotators requested: {', '.join(unsupported)}")
    if domain is None or task is None or input_mode is None:
        return
    input_kind = "plain_text" if input_mode == "plain_text" else "pmid"
    required_tasks = {"NER", "NEN"} if task == "both" else {task}
    incompatible = []
    for annotator in annotators:
        available_tasks = set(
            annotator_tasks_for_selection(
                annotator,
                flair_linking=task in {"NEN", "both"},
            )
        )
        if (
            not _domain_matches_capability(domain, annotator_domains(annotator))
            or input_kind not in annotator_input_modes(annotator)
            or not required_tasks.intersection(available_tasks)
        ):
            incompatible.append(_annotator_label(annotator))
    if incompatible:
        raise ValueError(
            f"Selected annotators do not support {domain} {task} for {input_kind}: "
            f"{', '.join(incompatible)}"
        )


def _prompt_pmids(*, input_fn: InputFn) -> list[str]:
    while True:
        pmids = parse_pmids(_prompt_required(input_fn, "Enter PMIDs, separated by commas or spaces: "))
        if pmids:
            return pmids


def _prompt_existing_pmid_file(*, input_fn: InputFn, output_fn: OutputFn) -> Path:
    while True:
        raw = input_fn("PMID file path: ").strip()
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        if path.is_file():
            return path
        output_fn(f"File not found: {path}")


def parse_pmids(raw: str) -> list[str]:
    pmids: list[str] = []
    for item in re.split(r"[,\s]+", raw.strip()):
        if item and item not in pmids:
            pmids.append(item)
    return pmids


def _uses_existing_text_table(answers: TerminalUIAnswers) -> bool:
    return answers.plain_text_source == "table_file" and answers.plain_text_file is not None


def _plain_text_config_file(answers: TerminalUIAnswers, paths: RunPaths) -> Path:
    if _uses_existing_text_table(answers):
        assert answers.plain_text_file is not None
        return answers.plain_text_file
    return paths.plain_text_path


def _plain_text_content(answers: TerminalUIAnswers) -> str:
    if answers.plain_text_source == "manual_text":
        return (answers.plain_text_content or "").strip()
    if answers.plain_text_file is None:
        if answers.plain_text_abstract:
            return answers.plain_text_abstract.strip()
        raise ValueError("Plain text input requires a file path or text entered in the terminal.")
    return answers.plain_text_file.read_text(encoding="utf-8").strip()


def _prompt_required(input_fn: InputFn, prompt: str) -> str:
    while True:
        value = input_fn(prompt).strip()
        if value:
            return value


def _prompt_yes_no(*, input_fn: InputFn, prompt: str) -> bool:
    return input_fn(prompt).strip().lower() in {"y", "yes"}


def _input_mode_label(input_mode: str) -> str:
    return {
        "pmids": "PubMed articles by PMID",
        "pmid_file": "PubMed articles from a PMID file",
        "plain_text": "Plain text",
    }.get(input_mode, input_mode)


def _domain_label(domain: str) -> str:
    return {
        "biomedical": "Biomedical",
        "clinical": "Clinical",
        "both": "Biomedical and Clinical",
    }.get(domain, domain)


def _domain_matches_capability(domain: str, supported_domains: tuple[str, ...]) -> bool:
    if domain == "both":
        return bool(supported_domains)
    return domain in supported_domains


def _task_label(task: str) -> str:
    return {"NER": "NER", "NEN": "NEN", "both": "NER, NEN, or both"}.get(task, task)


def _annotator_label(annotator: str) -> str:
    return ANNOTATOR_DISPLAY_NAMES.get(annotator, annotator)


def _entity_type_label(entity_type: str) -> str:
    return ENTITY_TYPE_DISPLAY_NAMES.get(
        entity_type,
        entity_type.replace("_", " ").capitalize(),
    )


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _toml_string_list(values: list[str]) -> str:
    return "[" + ", ".join(_toml_string(v) for v in values) + "]"
