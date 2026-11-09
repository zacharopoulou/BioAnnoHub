# BioAnnoHub

BioAnnoHub builds biomedical literature corpora, runs selected named entity annotators, and saves results in a format that can be inspected and reused.

Use it from the terminal for an interactive run, or use a TOML config for a repeatable workflow. Inputs include PubMed IDs, PMID files, and local text tables. Runs save their configuration, annotations, and summary files together.

## Get started

Requirements: Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/zacharopoulou/BioAnnoHub.git
cd BioAnnoHub
uv sync
uv run bioannohub run-config --config configs/examples/pmid-single.toml
```

This example runs PubTator3 on two PMIDs using its remote service, so it needs an internet connection but does not download local models. Results are saved in a timestamped run folder under `outputs/examples/`.

For an interactive run, use:

```bash
uv run bioannohub annotate
```

The terminal guides you through choosing documents, annotators, and entity types. For a first interactive run, choose PubMed articles by PMID and select PubTator3 only. Selecting local annotators can install optional dependencies and download model files; choosing all annotators may take a while and need extra system tools. See the [annotator guide](docs/annotators.md) before choosing tools.

Domain and supported-task choices narrow the annotators offered in the terminal. Entity-type choices filter saved results; they do not change what a selected tool produces. Choosing `NEN-capable` or `All tasks` enables Flair's entity linkers when Flair is selected.

## Common commands

Search PubMed and save matching PMIDs:

```bash
uv run bioannohub search-pmids \
  --query 'glioblastoma AND microRNA' \
  --output data/inputs/query_pmids.txt
```

Preview a config before running it:

```bash
uv run bioannohub inspect-config --config configs/examples/pmid-single.toml
uv run bioannohub load-documents --config configs/examples/pmid-single.toml
```

## Documentation

- [Annotator guide](docs/annotators.md): domains, supported tasks, and entity types.
- [Configuration guide](configs/README.md): config structure and runnable examples.
- [PubMed PMID search guide](src/bio_annotation/io/README.md): query syntax, filters, date bounds, and progress output.
- [Documentation index](docs/README.md): links to the other project guides.
- [Tests guide](tests/README.md): test coverage and development checks.

## Output

Runs are saved in timestamped folders under `outputs/runs/` by default. Each folder contains the config and manifest, a copy of the input where applicable, and results in JSON, TSV, and HTML formats. Config-based runs use the parent directory of the configured output path as the runs directory.

## Development

Run the local demo or the test suite with:

```bash
uv run bioannohub demo
uv run pytest -m 'not integration'
```

