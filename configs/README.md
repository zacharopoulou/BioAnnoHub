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

## PMID Text and Metadata

For PMID inputs, PubTator3 provides the title, abstract, and optional full text used for annotation. Entrez and Europe PMC provide metadata only; they do not supply or replace annotation text.

The metadata sources are requested as follows:

- With no metadata fields or enrichments selected, BioAnnoHub fetches from PubTator3 only.
- Selecting Entrez metadata requests both Entrez and Europe PMC metadata.
- Selecting only Europe PMC metadata requests Europe PMC without Entrez.

Metadata is attached only to PMIDs for which PubTator3 returned usable text. If PubTator3 does not return usable text, BioAnnoHub skips that PMID and reports it. If an optional metadata service fails, the run keeps the PubTator3 document and any metadata returned by the other service. Use `input.fields_per_source` to select metadata fields:

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

## Results and Metadata Export

Each run writes a JSON file, a document TSV, keyword and annotation TSVs, and an HTML report. The document TSV uses the JSON output's base name (for example, `results.documents.tsv`) and has one row per loaded document. It includes the PubTator3 title and text source, plus selected metadata in columns prefixed with `entrez_` or `europe_pmc_`. Lists and structured values are JSON-encoded within their TSV cells. Entrez `title` and `abstract` are not exported as metadata columns because PubTator3 supplies the annotation text.

## Optional Enrichments

Related records and citation data can be enabled under `[enrichment].sources`. Enrichments are off by default. Results are retained in `metadata.pubmed_record.elinks` in JSON and in the `entrez_elinks` column of `results.documents.tsv` (the TSV cell contains JSON).

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
