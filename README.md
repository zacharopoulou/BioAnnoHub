# BioAnnoHub

BioAnnoHub collects biomedical papers, runs named entity recognition and normalization tools, and saves the results for review.

## Install

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/zacharopoulou/BioAnnoHub.git
cd BioAnnoHub
uv sync
```

## Run

Start the interactive workflow and follow the prompts:

```bash
uv run bioannohub annotate
```

Or run a saved config:

```bash
uv run bioannohub run-config --config configs/examples/pmid-single.toml
```

To search PubMed and save matching IDs:

```bash
uv run bioannohub search-pmids \
  --query 'glioblastoma AND microRNA' \
  --output data/inputs/query_pmids.txt
```

`run-config` shows concise progress by default. Add `--log-level DEBUG` before the command for detailed service logs.

## Results

Each run creates a timestamped folder with the config, input, JSON results, TSV tables, and HTML report. The JSON keeps returned metadata and nested enrichment data. The document TSV has compact columns for filtering; keyword and annotation TSVs contain the extracted results.

For PMID runs, PubTator3 supplies the title and abstract used for annotation. Entrez and Europe PMC add metadata. A PMID without usable PubTator3 text is skipped.
The terminal asks whether to fetch additional metadata for PMID inputs; choosing yes enables all supported enrichment sources.

## Help

- [Config guide](configs/README.md): prepare PMID inputs, metadata, and enrichments.
- [Example configs](configs/examples/): ready-to-run workflows.
- [PubMed search guide](src/bio_annotation/io/README.md): query syntax and filters.
- [Workflow specification](docs/workflow-spec.md): detailed design and supported inputs.

Use `uv run bioannohub --help` to see all commands.
