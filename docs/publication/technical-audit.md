# Technical reliability audit

## Scope and test evidence

Source review covered `schemas/{document,entity}.py`, all adapters/proposers, `entity_types.py`, ingestion/configuration, `pipeline_runner.py`, the HTML report, and relevant tests.

Executed locally:

```text
.venv/bin/pytest -q tests/test_pipeline_runner.py tests/test_html_report.py tests/test_annotators.py tests/test_entity_types.py tests/test_ingestion_only_pipeline.py
101 passed in 2.00s
```

This is positive evidence for mocked adapter parsing, selected offset handling, type mapping, output generation, report rendering, status aggregation, and copied run artifacts. It does not verify every test in the repository, live PubMed/BERN2/PubTator3/MedCAT availability, or optional large-model installation and inference. No model downloads or external integrations were run.

## Findings by contract

### Annotation consistency

- `Document.text` uses title plus selected body joined by two newlines; most adapters receive this representation. PubTator3 parser also adjusts BioC passage offsets to this document text. The focused adapter tests include title/body and repeated-mention cases.
- `make_annotation` trusts explicit offsets and only resolves by first text occurrence when offsets are missing. It does not reject negative, out-of-range, reversed, or text-mismatched intervals. Thus repository tests prove selected adapter cases, not the pipeline-wide invariant `document.text[start:end] == span_text`.
- `normalize_entity_type` applies a broad alias table. Mapping a model-specific category to `disease`, `drug`, `gene`, etc. is convenient for grouping, but does not prove that the underlying annotation guidelines are equivalent. The source label is not retained on `Annotation`.
- Each individual annotation remains available in JSON and TSV and is grouped views are ID references; the system does not merge annotator outputs into a winning prediction. However, any raw labels or candidate details already discarded by an adapter cannot be recovered in the report.
- Filtering is post-adapter and based on mapped canonical entity type. An empty filter retains all returned types. An unsupported type can pass through as a normalized/raw category rather than be silently forced into one of the nine README types.

### Normalization handling

- `Annotation` has one `canonical_id`, `canonical_name`, `confidence`, and `normalization_score`; the latter two are separate fields. HunFlair link score is stored separately from NER confidence.
- IDs originate from heterogeneous sources, including NCBI Gene, MeSH, OMIM, DrugBank, NCBI Taxonomy, Cellosaurus, UMLS, and ontology terms. Capability definitions document expected databases and source fields, but the record has no separate `identifier_namespace` or URI field. Some adapters return prefixed IDs; others can return bare numeric IDs. The HTML renderer infers prefixes in limited contexts (for example, a bare gene number), which is a display convenience rather than stored provenance.
- Adapter mappings select a canonical entity type, and source/canonical label distinction is absent. The adapter source identifies which tool produced the record, but reconstructing the precise raw label is not guaranteed.
- Candidate handling is not uniformly lossless: model linkers often expose a top link; adapters generally choose a single value. A paper may claim preservation of each prediction that BioAnnoHub emits, but must not claim preservation of all source-system alternatives without adapter-specific verification.
- Minimal change: extend the annotation record compatibly with `source_entity_type`, `identifier_namespace` (or a structured identifier/URI), and candidate list only where the source actually returns candidates. Preserve existing fields and never infer a namespace from entity type alone.

### Execution robustness

- The execution loop catches per-annotator exceptions, logs a warning, records `status="failed"`, an error reason and duration, then continues. Per-document status records and manifest aggregation distinguish documents with failures and collect distinct error reasons.
- A successful call returning an empty list is `no_annotations`; this is not a proof that the model found no entities. PubTator3 may return none for a non-PMID/PMCID document, and a remote service may be unreachable depending on adapter behavior. Status reasons are explanatory but not always machine-distinguishable between valid zero results and ineligible/unavailable service.
- Several local model loaders are attempted before iteration and exceptions are logged. Adapter calls may retry loading or fail inside the status wrapper. Add a direct test for the observable behavior for unavailable models and ensure it is `failed`/`unavailable`, not ambiguous `no_annotations`.
- Optional dependency preflight exists for extras and separate tool environments. This does not perform universal annotator/entity-type compatibility validation. The terminal interface can warn, but a direct TOML run should be audited as its own path.
- Parser behavior can skip malformed/unrecognized records without an explicit per-record error count. Add summary counts for rejected/malformed annotations if the paper emphasizes reliable interchange.

### Reproducibility and outputs

- When an output path is configured, run directories contain copied `config.toml`, input snapshots, result JSON, grouped and per-annotation TSV, standalone HTML, and `run_manifest.json`. Manifest captures start time, duration, source/input description, counts, selected types and annotator statuses.
- The JSON contains source documents, metadata, annotations, and grouped keywords. It is useful as a research data artifact, though no formal schema version or external interchange standard is declared.
- The manifest does not currently establish the exact BioAnnoHub git revision, Python/environment lock identity, resolved model revision or checksum, external service model/deployment version, or request ID. `uv.lock` pins Python dependencies for this checkout but cannot pin a remote model/service response by itself.
- Saved config can be rerun against copied document input where applicable. PMID workflows may fetch updated records and APIs/models may change; remote results therefore are not guaranteed to reproduce bit-for-bit. The run artifacts preserve the previous output, but remote request/response records and endpoint state are not uniformly captured.
- Cross-file consistency is tested for selected pipeline outputs. There is no independent export-schema validation that JSON annotation IDs, document references, TSV records, and manifest counts all reconcile for every path, including partial failures.

### Test coverage

- Good evidence: adapter fixtures test multiple parsers and offsets; tests cover canonical type mapping, normalization scores, overlapping report rendering, pipeline output generation, statuses, and run snapshots.
- Limits: tests often inject fake service responses, fake local model outputs, or subprocess functions. The selected 101 pass confirms these code paths under controlled responses, not external integrations. The integration marker exists in pytest config; this audit did not run live integration tests.
- Keep all heavy model/service tests opt-in. Add fast contract tests around invariants and failure semantics, and keep one documented manual/release smoke workflow for live dependencies.

## Prioritized issues

| ID / severity | Evidence | Consequence for paper | Minimal fix and acceptance condition |
|---|---|---|---|
| T1 — High (P0) | `entity_proposal/_shared.py::resolve_offsets` casts supplied offsets but does not validate bounds or compare the slice; only selected adapter tests assert exact spans. | Misaligned highlights or corrupted downstream offsets would undermine the core interoperable annotation claim. | Add a common validation stage that rejects/flags invalid spans while retaining the original record/error context. Contract tests cover each adapter fixture and assert valid bounds and text equality when offsets exist; tests verify missing-offset behavior is explicit. |
| T2 — High (P0) | `schemas/entity.py` lacks source label and ID namespace; `entity_types.py` keeps capability/database expectations separately. | “Lossless” or “provenance-aware harmonization” would overstate current stored data. Bare IDs can be misinterpreted downstream. | Preserve raw source label and explicit namespace/URI with backward-compatible serialization; adapter fixtures assert exact round-trip. Do not infer namespace except as a clearly marked unresolved value. |
| T3 — High (P0) | `run_selected_annotators_with_status` separates thrown exceptions from empty results, but no-annotation reason is broad and preloading failures are logged earlier; service-ineligible cases may also return empty. | A user cannot reliably tell no detected terms from unavailable/inapplicable annotation and may treat missing output as biological evidence. | Define machine-readable statuses such as `succeeded_with_annotations`, `succeeded_empty`, `failed`, `unsupported_input`, `unavailable`; test service failure, valid empty, unsupported PubTator3 input, and model load failure. |
| T4 — Medium (P1) | Manifest fields omit code/model/service provenance; `uv.lock` exists but manifest does not identify it. | Config and inputs alone are insufficient to recreate model-backed/remote runs. | Record package version and git revision; adapter/model ID plus resolved revision/hash when discoverable; endpoint (sanitized), time, and provider result metadata where available. Record unknown values explicitly. |
| T5 — Medium (P1) | Current JSON/TSV are portable but lack declared schema version and validation; arbitrary returned candidate detail may not survive. | Dataset reuse is practical but downstream consumers lack stable interpretation guarantees. | Declare a versioned output schema and document canonical types/offset convention/ID semantics; preserve candidate arrays only for adapters that supply them. Add fixture round-trip/export consistency checks. |
| T6 — Medium (P1) | Capability registry is detailed, but no universal check ties selected types to each adapter's verified capabilities for config workflows. | Workflow may execute an adapter that cannot produce requested categories, making empty results misleading. | Preflight selected type compatibility from capability metadata while retaining an opt-in “keep all output types” mode; tests for unsupported-type warning/status, not silent remapping. |
| T7 — Low (P2) | README and some docs contain stale name, placeholder clone URL, outdated short adapter roster and stale claims; `pyproject.toml` version is `0.1.0`. | Reviewers/users may misunderstand current interface and installation scope. | Update quickstart/capability tables in release-prep branch, document tested install paths, release version and archive DOI. |

T1–T3 should be resolved before manuscript claims rely on validated, traceable, comparable outputs. T4–T6 are the minimum work to support reusable research-dataset claims. No issue requires benchmarking expansion.
