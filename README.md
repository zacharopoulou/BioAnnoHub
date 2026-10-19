# BioAnnoHub

BioAnnoHub builds biomedical literature corpora, runs selected named entity annotators, and saves results in a format that can be inspected and reused.

Use it from the terminal for an interactive run, or use a TOML config for a repeatable workflow. Inputs include PubMed IDs, PMID files, and local text tables. Runs save their configuration, annotations, and summary files together.

## Get started

Requirements: Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/zacharopoulou/BioAnnoHub.git
cd BioAnnoHub
uv sync
uv run bioannohub annotate
```

The terminal workflow guides you through choosing documents, annotators, and entity types. Local annotators may need optional dependencies, model downloads, or a separate setup; the app will explain what is needed when you select one.

## Common commands

Run a saved example config:

```bash
uv run bioannohub run-config --config configs/examples/pmid-single.toml
```

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

Run the standalone NCBI Disease benchmark review:

```bash
uv sync --extra benchmarks
uv run bioannohub evaluate-ncbi-review
```

## Documentation

- [Configuration guide](configs/README.md): config structure and runnable examples.
- [Project docs](docs/README.md): workflow overview and design notes.
- [Benchmark review guide](src/bio_annotation/benchmarking/README.md): dataset, evaluation options, outputs, and limitations.
- [Benchmark data notes](data/benchmarks/README.md): local benchmark data conventions.
- [Data guide](data/README.md): inputs, corpora, and generated data.
- [Tests guide](tests/README.md): test coverage and development checks.
- [Workflow specification](docs/workflow-spec.md): the broader workflow model and supported input types.

## Output

Runs are saved in timestamped folders under `outputs/runs/` by default. Each folder contains the config and manifest, a copy of the input where applicable, and results in JSON, TSV, and HTML formats. Config-based runs use the parent directory of the configured output path as the runs directory.

## Development

Run the local demo or the test suite with:

```bash
uv run bioannohub demo
uv run pytest
```
