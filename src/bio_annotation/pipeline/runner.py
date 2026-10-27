from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from bio_annotation.pipeline.execution import build_pipeline_output, validate_optional_annotator_dependencies
from bio_annotation.pipeline.manifest import build_run_manifest, copy_run_inputs, create_run_dir, update_latest_run_link
from bio_annotation.pipeline.options import RUN_MANIFEST_NAME, RUN_RESULTS_DIR
from bio_annotation.pipeline.output import write_pipeline_output
from bio_annotation.pipeline_config import load_pipeline_config
from bio_annotation.preprocessing.document_loader import (
    load_documents_from_config,
    load_documents_from_pmid_file,
    load_documents_from_pmids,
)
from bio_annotation.schemas.document import Document

def run_pipeline_from_config(
    config_path: Path,
    *,
    orchestrator_factory: Callable[[], Any] | None = None,
    pmid_fetcher: Callable[[str], dict[str, Any]] | None = None,
    bern2_request_fn: Callable[[Document], Any] | None = None,
    pubtator3_request_fn: Callable[[Document], Any] | None = None,
    flair_spans_by_document: dict[str, list[Any]] | None = None,
    bent_request_fn: Callable[[Document], Any] | None = None,
    clinicalbert_responses_by_document: dict[str, list[Any]] | None = None,
    apollo_responses_by_document: dict[str, list[Any]] | None = None,
    d4data_responses_by_document: dict[str, list[Any]] | None = None,
    medcat_request_fn: Callable[[Document], Any] | None = None,
    scispacy_responses_by_document: dict[str, dict[str, list[Any]]] | None = None,
    stanza_entities_by_document: dict[str, dict[str, list[Any]]] | None = None,
    run_dir: Path | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    config = load_pipeline_config(config_path)
    validate_optional_annotator_dependencies(
        config,
        flair_spans_by_document=flair_spans_by_document,
        clinicalbert_responses_by_document=clinicalbert_responses_by_document,
        apollo_responses_by_document=apollo_responses_by_document,
        d4data_responses_by_document=d4data_responses_by_document,
        scispacy_responses_by_document=scispacy_responses_by_document,
        stanza_entities_by_document=stanza_entities_by_document,
    )
    if pmid_fetcher is not None and config.input_mode == "pmids":
        documents = load_documents_from_pmids(
            config.pmids,
            fetcher=pmid_fetcher,
            enrichment_sources=config.enrichment_sources,
        )
    elif pmid_fetcher is not None and config.input_mode == "pmid_file":
        if config.pmid_file is None:
            raise ValueError("input.pmid_file must be set when input.mode = 'pmid_file'.")
        documents = load_documents_from_pmid_file(
            config.pmid_file,
            fetcher=pmid_fetcher,
            enrichment_sources=config.enrichment_sources,
        )
    else:
        documents = load_documents_from_config(
            config,
            orchestrator_factory=orchestrator_factory,
        )
    payload = build_pipeline_output(
        documents,
        config,
        bern2_request_fn=bern2_request_fn,
        pubtator3_request_fn=pubtator3_request_fn,
        flair_spans_by_document=flair_spans_by_document,
        bent_request_fn=bent_request_fn,
        clinicalbert_responses_by_document=clinicalbert_responses_by_document,
        apollo_responses_by_document=apollo_responses_by_document,
        d4data_responses_by_document=d4data_responses_by_document,
        medcat_request_fn=medcat_request_fn,
        scispacy_responses_by_document=scispacy_responses_by_document,
        stanza_entities_by_document=stanza_entities_by_document,
    )
    if config.output_path is not None:
        run_dir = run_dir or create_run_dir(config.output_path.parent)
        actual_output_path = run_dir / RUN_RESULTS_DIR / config.output_path.name
        payload["output"] = {
            "configured_path": config.output_path.as_posix(),
            "path": actual_output_path.as_posix(),
            "run_dir": run_dir.as_posix(),
            "manifest_path": (run_dir / RUN_MANIFEST_NAME).as_posix(),
        }
        write_pipeline_output(payload, actual_output_path)
        input_files = copy_run_inputs(config, config_path, run_dir)
        manifest = build_run_manifest(
            payload,
            run_dir=run_dir,
            output_path=actual_output_path,
            input_files=input_files,
            started_at=started_at,
            duration_seconds=time.perf_counter() - started,
        )
        (run_dir / RUN_MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        update_latest_run_link(run_dir)
    return payload
