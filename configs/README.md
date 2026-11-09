# Configuration Guide

This directory contains runnable pipeline configurations for BioAnnoHub.

## Files

- `pipeline.toml`
  Default config, set up for a first live PubTator3 PMID run.
- `examples/`
  Small runnable configs for common input modes, plus one advanced multi-source fetch example.

## Main Sections

Each pipeline config is organized around:

- `[input]`
- `[enrichment]`
- `[annotators]`
- `[filters]`
- `[output]`

## Fetch Defaults

PMID-based annotation always uses PubTator3 for title, abstract, and optional full text. If `[input].source` is omitted, BioAnnoHub fetches text from PubTator3 only. When metadata is requested, Entrez is called when its source or fields are selected, and Europe PMC is called alongside it (or by itself when Europe PMC fields are selected). Europe PMC does not provide annotation text.

Entrez and Europe PMC metadata are attached only to PMIDs returned by PubTator3. Neither source fills or replaces the annotation text. PMIDs PubTator3 does not return with usable text are skipped and reported in a warning. Use `input.fields_per_source` to select metadata fields:

```toml
[input]
mode = "pmid_file"
pmid_file = "data/inputs/example_pmids.txt"
source = ["pubtator3", "entrez"]

[input.fields_per_source]
entrez = ["mesh_terms", "authors", "journal", "year"]
europe_pmc = ["citation_count", "is_open_access", "license"]
```

Add `"full_text"` to `input.fields` and enable `[input.pubtator3].full_text = true` to request PubTator3 full text where available.

## Optional Enrichments

Additional cross-references can be enabled under `[enrichment].sources`. They are off by default. Results are retained inside `metadata.pubmed_record.elinks` in JSON and in the `entrez_elinks` column of `results.documents.tsv`.

```toml
[enrichment]
sources = ["elinks", "crossref"]
```

Supported values are `elinks`, `crossref`, `europe_pmc`, `semantic_scholar`, `unpaywall`, and `biorxiv`. These add related PMID lists, DOI reference data, citation/reference records, open-access details, or preprint details depending on the selected service. Some services make several requests per PMID. Unpaywall also requires `NCBI_EMAIL` to be set. Use only the enrichments your workflow needs.

## Annotator Tables

Annotator runtime metadata is defined under nested annotator tables.

Example:

```toml
[annotators]
enabled = ["pubtator3"]

[annotators.pubtator3]
runtime = "remote_api"
endpoint = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
format = "biocjson"
timeout = 60
```

The pipeline reads these settings and uses them at runtime for the matching annotator.

## Current Examples

- `examples/pmid-single.toml`
  Inline PMID input using PubTator3 text without an Entrez request.
- `examples/pmid-file.toml`
  PMID batch input using PubTator3 text without an Entrez request.
- `examples/corpus-file.toml`
  Local text-table input annotated with Flair (PubTator3 only annotates PubMed/PMC publications).
- `examples/fetch-merge.toml`
  PMID batch example where PubTator3 supplies all text and Entrez plus Europe PMC add selected metadata only.
