# BioAnnoHub publication readiness

## Executive summary

BioAnnoHub's strongest current contribution is a configuration-driven Python workflow that brings heterogeneous biomedical and clinical annotators into one run model, retains each prediction as a source-attributed record, and writes inspectable JSON, TSV, HTML, configuration, input snapshots, and run metadata. Its useful distinction is the practical combination of PubMed/document ingestion, local models, remote services, and separate-environment tools in a research-oriented CLI workflow. This is a promising application, but not yet a defensible novelty claim by itself.

The repository already implements the primary workflow and has focused unit tests. On 19 October 2026, 101 selected pipeline, report, adapter, entity-type, and ingestion tests passed in 2.00 seconds. They exercise mocked adapters and local transformations; they do not establish successful installation of every optional model, live availability of remote services, or stable external model versions.

The most important publication risk is semantic provenance. Output rows contain the adapter source and harmonized entity type, but the canonical `Annotation` does not separately retain the raw source label or an explicit identifier namespace. Some IDs are prefixed, some are bare, and capability tables describe expected identifier databases without binding an explicit namespace to each returned record. Also, the single ID/name/score representation cannot faithfully express every candidate list returned by tools. This weakens claims of lossless harmonization and reproducible downstream reuse. A second risk is that no common post-adapter validation enforces `0 <= start <= end <= len(document.text)` and `document.text[start:end] == span_text`; tests establish this for selected adapters and examples, not as an invariant across all adapters.

### What is already implemented and verified

- PMID/PMID-file, local text-table, and JSONL corpus inputs; PubTator3, Entrez, and Europe PMC retrieval paths are declared and implemented.
- Multiple remote, local-model, and separate-environment annotator adapters with canonical type mapping and capability metadata.
- Individual annotation records in JSON and TSV; grouped mention views; an HTML report with overlapping annotation inspection.
- TOML-driven and terminal workflows, copied run inputs/configuration, and manifests with counts, timing, annotator statuses, and errors.
- Selected unit tests pass, including checks for adapter offsets, normalization fields, reports, status aggregation, and run artifact creation.

“Verified” here means covered by the cited source/tests and the selected local test run. Live endpoints and optional heavyweight models remain unverified.

### What is missing for the first publication

1. Make span/offset validity a tested pipeline-wide contract and ensure invalid spans are surfaced rather than silently reported as usable annotations.
2. Preserve source entity labels and identifier namespace/URI explicitly, retaining every returned candidate where an adapter provides several.
3. Add reproducibility metadata for BioAnnoHub revision, adapter and model identifiers/versions, remote endpoint and retrieval time; document what remote services prevent pinning.
4. Demonstrate one frozen, small document corpus through a repeatable configuration and validate the generated artifacts and failure states end to end.
5. Replace stale quickstart/annotator claims in publication-facing documentation as release preparation, with a capability table tied to current adapters and verification level.

These are bounded interoperability and reliability improvements. A new annotation UI, additional adapters, or a benchmark expansion is not needed to make the first paper convincing.

### What should be developed next

Start with P0 technical stabilization of span checks and status distinctions, followed by P1 annotation provenance/schema and a compact dataset export/replay example. Then complete P2 packaging, installation, documentation, and archival evidence. The detailed acceptance criteria and dependencies are in [the development roadmap](development-roadmap.md).

### What belongs to publication 2

Systematic comparison against multiple compatible gold datasets, precision/recall/F1 and normalization metrics, cross-corpus generalization, training-data-overlap analysis, performance rankings, and evidence-based annotator recommendations belong to the separate benchmarking paper. The existing NCBI Disease review module is preliminary infrastructure; it is not evidence of the multi-corpus evaluation described for that paper. Benchmark-informed automatic annotator selection belongs to a later BioAnnoHub release.

## Audit documents

- [Feature inventory](feature-inventory.md)
- [Technical audit](technical-audit.md)
- [Related tools and positioning](related-tools.md)
- [Application plan](application-plan.md)
- [Prioritized development roadmap](development-roadmap.md)

## Audit scope and evidence

Repository evidence is from `main` at `dcd0b38` (`Remove annotators (#82)`), fetched from `origin/main` on 19 October 2026. The audit branch was created from that commit. Working-tree untracked spreadsheets and benchmark corpus directories were present and left untouched. No production source, tests, or top-level README were changed.

The audit reviewed `src/bio_annotation/{schemas,annotators,entity_proposal,entity_types,fetch,preprocessing,pipeline_config.py,pipeline_runner.py,report,clients}`, `tests`, `configs`, `pyproject.toml`, and user-facing documentation. Test execution was limited to the five selected test files listed in the technical audit. Related-tool claims are based on cited primary publications and official documentation; an undocumented capability is marked “unclear,” not absent.
