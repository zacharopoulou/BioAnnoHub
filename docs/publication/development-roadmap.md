# Minimal publication-oriented development roadmap

The sequence below addresses the reliability and evidence gaps that affect the proposed software contribution. It intentionally excludes a benchmarking study and broad feature growth.

## P0 — Publication blockers

| Task | Problem and repository evidence | Minimal change | Why it matters | Acceptance criteria | Dependencies | Suggested branch |
|---|---|---|---|---|---|---|
| P0.1 Span contract and validation | `entity_proposal/_shared.py::resolve_offsets` trusts explicit offsets; coordinate conversion is adapter-specific. Existing adapter/report tests cover selected cases only. | Validate bounds and exact `document.text[start:end]` at a shared boundary; mark invalid offsets explicitly or reject those records with a reason. Preserve `None` offsets only where source omits them, rather than guessing silently. | Offsets are the core link between annotation records and text; bad ranges break report inspection and downstream use. | Contract tests cover every adapter fixture for negative/reversed/out-of-range/mismatch cases, repeated spans, title/body shifts, and `None`; no invalid span is silently output as valid. | None | `publication-span-contract` |
| P0.2 Distinguish execution outcomes | Runner distinguishes thrown errors from empty output, but generic no-annotation reasons also cover ineligible/unavailable cases; loader failures are logged before processing. | Use explicit machine-readable success-with-results, success-empty, failed, unavailable, and unsupported-input outcomes. Keep human-readable reasons. | Without this, absent annotations can be misread as evidence about the text or model. | Tests independently exercise valid empty results, service exception/timeout, missing local model, and PubTator3 without PMID/PMCID; manifest and JSON preserve distinct statuses. | None; can run alongside P0.1 | `publication-run-statuses` |
| P0.3 Preserve source annotation semantics | `schemas/entity.py::Annotation` stores mapped type and generic canonical ID/name; source label/namespace are absent. Adapter tests show different ID forms. | Add backward-compatible raw source label, explicit identifier namespace/URI, and candidate list only when returned. Keep the mapped field for grouping; do not collapse records. | This is necessary for a defensible interoperability and downstream-reuse claim. | Adapter fixtures assert raw label, mapped label, ID namespace/value and candidate retention; JSON/TSV/report preserve fields; bare/unresolved ID namespaces are not guessed. | Select a schema evolution/versioning strategy (P1.1 can follow immediately) | `publication-annotation-provenance` |

## P1 — High-value publication improvements

| Task | Problem and repository evidence | Minimal change | Why it matters | Acceptance criteria | Dependencies | Suggested branch |
|---|---|---|---|---|---|---|
| P1.1 Version and document the output schema | JSON contains full documents/annotations and grouped views, but does not declare a schema version or formal field/offset/ID semantics. | Publish a compact schema description and `schema_version`; document offsets as zero-based half-open indices into `Document.text`, raw vs harmonized labels, status meanings, and namespace rules. | Lets other research code consume outputs without reverse-engineering internals. | A checked-in example validates against documented schema; schema version appears in JSON and manifest; compatibility policy is stated. | May be coordinated with P0.3 | `publication-output-schema` |
| P1.2 Record execution provenance | Manifest has config/input copies, counts, duration, status and errors; it does not capture repository revision or resolved local/remote model identity. | Record BioAnnoHub version/git commit, Python/platform and lockfile digest, adapter/model ID and resolved model revision/hash when available, endpoint host, timestamp and returned service version/request ID when available. Represent unknowns explicitly; exclude credentials. | Strengthens the central provenance/reproducibility contribution while acknowledging remote variability. | A run manifest distinguishes recorded vs unavailable provenance fields, includes no secrets, and a test checks expected local and remote fields. | P0.2 status taxonomy helpful | `publication-run-provenance` |
| P1.3 Validate artifact reconciliation and frozen-corpus replay | Existing run-artifact tests cover selected output paths; there is no single exported-artifact consistency validator. | Add a small validation command or reusable check for annotation/document references, ID uniqueness, JSON↔TSV counts and manifest totals; include a frozen 6–10 PMID corpus and TOML example. | Converts “reusable output” into a concrete, inspectable use case. | Example can be run offline from copied inputs; outputs validate and HTML opens; live adapter run instructions explicitly note possible service drift. | P0.1–P0.3 and P1.1 | `publication-reusable-example` |
| P1.4 Verify adapter capability metadata | Registry lists types and normalization databases, but declared capability is not equivalent to successfully tested implementation; config workflow compatibility preflight is limited. | Generate a capability matrix from registry/adapters and label each entry as source-declared, fixture-tested, or live-verified. Add a clear warning/status when requested type is unsupported. | Prevents false equivalence and communicates real scope accurately. | Supplementary matrix matches adapter code and tests; users can distinguish unsupported from empty result. | P0.2 | `publication-capability-evidence` |

## P2 — Release preparation

| Task | Problem and repository evidence | Minimal change | Why it matters | Acceptance criteria | Dependencies | Suggested branch |
|---|---|---|---|---|---|---|
| P2.1 Refresh user-facing docs | README has stale project naming, clone placeholder, old three-adapter description, and says “reproducible” without discussing remote/version limits. | Update quickstart, adapter/runtime table, optional installation cost, input formats, outputs, failure semantics, and limitations. Keep a short primary workflow and link to detailed docs. | Reviewers need a truthful account of what they can install and rerun. | Clean-install instructions work in a documented environment; no stale names/placeholders; supported feature claims link to capability evidence. | After P0/P1 semantics stabilize | `publication-docs-release` |
| P2.2 Clean install and smoke run | Optional extras include large model packages, and AIONER/BENT use separate environments; audit did not install them. | Define a small supported install matrix: base + selected remote workflow, and one optional local adapter. Run from a fresh environment and record actual commands/resource needs. | Establishes practical entry path without promising every optional tool is equally easy to install. | CI or release checklist verifies base installation and fast tests; local smoke run records model/version and expected output; optional integrations are labeled. | P1.4 | `publication-install-smoke` |
| P2.3 Archive release and manuscript evidence | Current package version is `0.1.0`; the reviewed checkout is not itself an archived publication release. | Prepare tagged release, changelog, license/software citation metadata, and archival DOI (for example Zenodo integration) after fixes. Check current journal Application Note constraints during manuscript submission preparation. | Makes the cited software artifact and application reproducible. | Tagged source matches tested commit; citation metadata and archive resolve; manuscript links to tag/archive and reports tested version. | P0/P1/P2.1–2.2 | `publication-release-archive` |

## Out of scope for this paper

- Exhaustive entity-type benchmarking or new benchmark dataset integration.
- Annotator performance rankings or accuracy claims.
- Automatic annotator recommendations or selection based on isolated F1 values.
- Unrelated refactoring or new annotators without a specific application need.
- A full web application or large architectural replacement.
- Treating inter-annotator agreement as accuracy or consensus.

## Recommended order

1. Complete P0.1 and P0.2 before relying on span or status claims.
2. Complete P0.3 with P1.1 so the record and export contract evolve together.
3. Add P1.2 and the frozen-corpus artifact validation in P1.3.
4. Produce the P1.4 capability evidence and run the application plan.
5. Finish P2 installation/docs/release work after behavior stabilizes.

This is primarily a combination of **targeted technical stabilization, stronger annotation provenance, and publication evidence**. A new full dataset platform or broad increase in functionality is not justified by the audit.
