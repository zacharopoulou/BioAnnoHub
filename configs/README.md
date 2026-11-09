# Config Guide

A config makes a run repeatable. Copy an example from [`examples/`](examples/) and change its inputs and options.

## Run a config

```bash
uv run bioannohub run-config --config configs/examples/pmid-single.toml
```

To find PMIDs first:

```bash
uv run bioannohub search-pmids \
  --query 'glioblastoma AND microRNA' \
  --output data/inputs/query_pmids.txt
```

Set `input.mode = "pmid_file"` and `input.pmid_file` to that file in your config. Run progress is shown by default; add `--log-level DEBUG` before `run-config` for detailed service logs.

## PMID text and metadata

PubTator3 provides the title and abstract for annotation. Entrez and Europe PMC add metadata; they do not replace the annotation text. Metadata is attached when PubTator3 returns usable text. If a source fails, the run keeps any results received from the other sources.

For example, request Entrez and Europe PMC metadata and a few enrichments:

```toml
[input]
mode = "pmid_file"
pmid_file = "data/inputs/query_pmids.txt"
source = ["pubtator3", "entrez"]

[enrichment]
sources = ["elinks", "crossref"]
```

Selecting `entrez` also requests Europe PMC metadata. Enrichments are optional; supported values are `elinks`, `crossref`, `europe_pmc`, `semantic_scholar`, `unpaywall`, and `biorxiv`. Unpaywall requires `NCBI_EMAIL`.

Use `input.fields_per_source` to limit metadata saved in the JSON:

```toml
[input.fields_per_source]
entrez = ["authors", "journal", "mesh_terms", "year"]
europe_pmc = ["citation_count", "is_open_access", "license"]
```

## Output files

Each run writes JSON, document/keyword/annotation TSVs, and an HTML report to a timestamped folder next to the configured output path. The JSON retains returned metadata and nested enrichment results, subject to the requested fields and service availability. The document TSV has one row per paper and a fixed set of compact columns; large nested fields such as references remain in JSON.
