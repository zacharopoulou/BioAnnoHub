from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from bio_annotation.pipeline.options import RUN_CONFIG_NAME, RUN_INPUTS_DIR
from bio_annotation.pipeline.output import pipeline_tsv_output_paths
from bio_annotation.pipeline.progress import _aggregate_annotator_statuses
from bio_annotation.pipeline_config import PipelineConfig

def create_run_dir(base_dir: Path, *, now: datetime | None = None) -> Path:
    run_dir = base_dir / (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def copy_run_inputs(config: PipelineConfig, config_path: Path, run_dir: Path) -> list[str]:
    """Copy the config and input files into the run folder so the run is self-contained."""
    config_text = config_path.read_text(encoding="utf-8")
    inputs_dir = run_dir / RUN_INPUTS_DIR
    inputs_dir.mkdir(exist_ok=True)
    input_files: list[str] = []
    if config.input_mode == "pmids":
        pmids_path = inputs_dir / "pmids.txt"
        pmids_path.write_text("".join(f"{pmid}\n" for pmid in config.pmids), encoding="utf-8")
        input_files = [pmids_path.as_posix()]
    else:
        key, source = {
            "pmid_file": ("pmid_file", config.pmid_file),
            "text_table": ("text_file", config.text_file),
            "corpus": ("corpus_path", config.corpus_path),
        }.get(config.input_mode, (None, None))
        if source is not None and source.is_file():
            target = inputs_dir / source.name
            if source.resolve() != target.resolve():
                shutil.copyfile(source, target)
            config_text = _point_config_input_at(config_text, key, target)
            input_files = [target.as_posix()]
    (run_dir / RUN_CONFIG_NAME).write_text(config_text, encoding="utf-8")
    return input_files


def _point_config_input_at(config_text: str, key: str, path: Path) -> str:
    """Rewrite the `[input]` path key so the run's config.toml references the copied input."""
    lines = config_text.splitlines(keepends=True)
    section = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped
        elif section == "[input]" and re.match(rf"{key}\s*=", stripped):
            lines[index] = f"{key} = {json.dumps(path.resolve().as_posix())}\n"
            break
    return "".join(lines)


def build_run_manifest(
    payload: dict[str, Any],
    *,
    run_dir: Path,
    output_path: Path,
    input_files: list[str],
    started_at: datetime,
    duration_seconds: float,
) -> dict[str, Any]:
    annotation_summary = payload.get("annotation_summary", {})
    return {
        "run_id": run_dir.name,
        "started_at": started_at.isoformat(),
        "duration_seconds": round(duration_seconds, 3),
        "input": {**payload.get("input", {}), "files": input_files},
        "annotators_enabled": payload.get("pipeline", {}).get("annotators_enabled", []),
        "entity_types": payload.get("entity_types", []),
        "document_count": payload.get("document_count", 0),
        "annotation_count": annotation_summary.get("annotation_count", 0),
        "keyword_count": annotation_summary.get("keyword_count", 0),
        "annotators": _aggregate_annotator_statuses(
            payload.get("annotator_summary", {}).get("annotators", [])
        ),
        "files": {
            "config": (run_dir / RUN_CONFIG_NAME).as_posix(),
            "results_json": output_path.as_posix(),
            **{
                name: path.as_posix()
                for name, path in pipeline_tsv_output_paths(output_path).items()
            },
            "html_report": output_path.with_suffix(".html").as_posix(),
        },
    }


def update_latest_run_link(run_dir: Path) -> None:
    latest = run_dir.parent / "latest"
    try:
        if latest.is_symlink():
            latest.unlink()
        elif latest.exists():
            logger.warning("Not updating %s: it exists and is not a symlink.", latest)
            return
        latest.symlink_to(run_dir.name, target_is_directory=True)
    except OSError as exc:
        logger.warning("Could not update %s: %s", latest, exc)
