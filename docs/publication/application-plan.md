# Publication application plan

## Purpose

Demonstrate that BioAnnoHub can execute heterogeneous biomedical annotators on the same small, inspectable corpus, preserve source-specific outputs, harmonize labels where mappings are declared, and package the run for reuse. Do not score systems against a gold standard or rank them.

## Proposed corpus

Use **six to ten PubMed abstracts** about glioblastoma and microRNAs. Define a reproducible query in PubMed, for example:

```text
(glioblastoma[Title/Abstract]) AND (microRNA[Title/Abstract] OR miRNA[Title/Abstract])
```

At corpus assembly time, set a documented publication-date range and sort order, select a small cap, then freeze the exact PMID list and fetched title/abstract text with retrieval date and source metadata. The query is a discovery recipe, not the run-time source of truth: saving the exact input snapshot prevents future indexing changes from silently changing the example. Do not publish licensed full text; abstracts and IDs are sufficient.

If the query produces too few or overly repetitive records, broaden only the saved search strategy and record the final exact PMIDs. This audit does not invent PMIDs or report annotation counts.

## Annotators and entity types

Primary demonstration: **PubTator3 and BERN2**, configured on the same frozen documents. Both have remote adapters and exercise different response parsers; their availability must be checked when the actual application run is prepared. Request gene/protein, disease, chemical/drug, and species only if those categories are meaningful for all included tools. Keep the full raw output returned by each adapter even where a requested category is unsupported.

Optional local contrast: add one manageable local model (for example, scispaCy BC5CDR for disease/chemical mentions) only if its dependency/model installation is successfully verified and the scope is explicitly limited to those types. Do not add it merely to increase adapter count. Use the capability registry and model documentation to describe supported types; do not equate mapped labels with identical annotation guidelines.

## Configuration and execution

Create one TOML configuration with:

- PMID-file or frozen corpus input;
- both remote adapters, their endpoint and timeout settings;
- explicit output directory and relevant entity-type filter;
- no enrichment unless it is needed for the document metadata;
- documented adapter/model settings and environment versions.

Run the exact saved config in a clean, documented environment. Retain config, copied input snapshot, package lock/environment summary, outputs, and manifest. For each service record run date, endpoint, any model/version header or response metadata available, and whether the service was reachable. Redact secrets from configuration and artifacts.

## Expected output and what it establishes

| Artifact / example | What it demonstrates |
|---|---|
| Frozen PMID list plus document JSON/TSV | The input corpus is identifiable and does not depend on re-running a changing search. |
| TOML config and run manifest | A reader can see selected sources, requested types, timing, counts, statuses, and paths; it also surfaces remote/service failure rather than disguising it as model performance. |
| Per-annotation JSON and TSV | Each emitted prediction remains attached to its adapter, span, mapped label, identifier/value, and scores where available. Present records separately; do not collapse disagreement into a “correct” result. |
| Grouped keyword TSV and HTML report | Users can inspect overlap/agreement patterns, entity labels, spans, and linked IDs. State that overlap is descriptive and is not accuracy or consensus. |
| Repeat-run comparison | Re-running from frozen inputs/config creates the same document set and valid output schema. Counts/annotations from remote APIs may vary and should be reported as observed, not promised stable. |

Choose two or three representative mentions, including at least one entity where annotators agree and one where the boundary, mapped label, normalization, or presence differs. Show the underlying individual records and the report view. This illustrates why per-source provenance matters; it does not imply which prediction is correct.

## Technical validation before manuscript use

1. Run all fast unit tests and record exact command, versions, and result; run existing live integration tests only where endpoints are available and explicitly mark them as live checks.
2. Validate every emitted span against the stored document text. Record missing offsets and reject/flag invalid intervals.
3. Check output consistency: each annotation references an existing document; IDs are unique; TSV rows reconcile to JSON records; manifest counts reconcile; report loads from the exported JSON.
4. Verify each service status with a deliberate valid empty result, a failure, and an unsupported-input condition so those cases are distinguished.
5. Repeat from the copied config/input. Compare schema, document identity, provenance, and artifact completeness; treat changed remote predictions as possible service/model variability.
6. Install and run any selected local model from a fresh environment with model version/hash recorded. Do not use a mocked test as evidence of real model operation.

## Manuscript figure and supplement

Main figure: one architecture/workflow diagram showing (1) frozen PMID corpus, (2) adapter-specific execution (remote and optional local), (3) per-tool source record plus harmonized fields, and (4) JSON/TSV/HTML and manifest artifacts. Draw each prediction as retained independently; place grouping/reporting downstream as an inspection view.

Supplement: exact query/date and PMID list; complete TOML; software and model versions; capability table with verification status; example input and output records; canonical schema/offset/namespace definitions; installation and rerun steps; test command/results; known remote variability. Avoid performance tables, ranking, inferred agreement accuracy, or claims based on annotation count.
