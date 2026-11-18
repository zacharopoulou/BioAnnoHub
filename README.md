# BioAnnoHub

BioAnnoHub brings together 24 annotator and model integrations for biomedical and clinical text. The terminal menu filters them by input, domain, and task; see the [annotator guide](docs/annotators.md) for the full catalog.

Use it from the terminal for an interactive run, or use a TOML config for a repeatable workflow. Inputs include PubMed IDs, PMID files, and local text tables. Runs save their configuration, annotations, and summary files together.

## Get started

Requirements: [Docker](https://docs.docker.com/get-docker/). Everything else, including the annotator models, is inside the image.

Get the image and name it `bioannohub`, the name the commands below use:

```bash
docker pull biogemt/bioannohub:0.1.0
docker tag biogemt/bioannohub:0.1.0 bioannohub
```

This is the slim image, which ships the commonly used annotators. The full image, `biogemt/bioannohub:0.1.0-full`, adds BENT, the other Stanza and scispaCy models, and the Flair entity linkers. [`images.toml`](images.toml) lists the annotators in each image. Selecting one that is not in your image stops the run with a message pointing at the full image.

The commands below use the configs in this repository, so run them from a clone:

```bash
git clone https://github.com/zacharopoulou/BioAnnoHub.git
cd BioAnnoHub
```

Run an example:

```bash
docker run --rm -it -u "$(id -u):$(id -g)" -v "$PWD:/work" bioannohub \
  run-config --config configs/examples/pmid-single.toml
```

The command mounts the current folder at `/work` and runs as your user so output files belong to you. The container only sees that folder, so keep configs and input files inside it.

This example runs PubTator3 on two PMIDs using its remote service, so it needs an internet connection but does not download local models. Results are saved in a timestamped run folder under `outputs/examples/`.

For an interactive run, use:

```bash
docker run --rm -it -u "$(id -u):$(id -g)" -v "$PWD:/work" bioannohub annotate
```

The terminal guides you through choosing documents, annotators, and entity types. For a first interactive run, choose PubMed articles by PMID and select PubTator3 only. Local models are already in the image; choosing many of them makes a run slower. See the [annotator guide](docs/annotators.md) before choosing tools.

Domain and supported-task choices narrow the annotators offered in the terminal. Entity-type choices filter saved results; they do not change what a selected tool produces. Choosing `NEN-capable` or `All tasks` enables Flair's entity linkers when Flair is selected.

## Common commands

Search PubMed and save matching PMIDs:

```bash
docker run --rm -it -u "$(id -u):$(id -g)" -v "$PWD:/work" bioannohub \
  search-pmids \
  --query 'glioblastoma AND microRNA' \
  --output data/inputs/query_pmids.txt
```

Preview a config before running it:

```bash
docker run --rm -it -u "$(id -u):$(id -g)" -v "$PWD:/work" bioannohub \
  inspect-config --config configs/examples/pmid-single.toml
docker run --rm -it -u "$(id -u):$(id -g)" -v "$PWD:/work" bioannohub \
  load-documents --config configs/examples/pmid-single.toml
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

Development happens in the same image users run. Build it from the repository:

```bash
docker build -t bioannohub .
docker build --build-arg IMAGE=full -t bioannohub:full .
```

Run the tests against the code built into the image:

```bash
docker run --rm --entrypoint python -w /repository bioannohub -m pytest -m 'not integration'
```

To test local edits without rebuilding, mount your source over the image's copy:

```bash
docker run --rm --entrypoint python -w /repository \
  -v "$PWD/src:/repository/src" -v "$PWD/tests:/repository/tests" -v "$PWD/configs:/repository/configs" \
  bioannohub -m pytest -m 'not integration'
```

Changes to `pyproject.toml`, `uv.lock`, or the `Dockerfile` need a rebuild. See the [tests guide](tests/README.md) for more.

### Releasing

1. Set `version` in `pyproject.toml` (for example `0.2.0`) and merge it into `main`.
2. Tag that commit and push the tag: `git tag v0.2.0 && git push origin v0.2.0`. The Publish workflow checks the tag matches the version, then builds, tests and pushes `biogemt/bioannohub:0.2.0`.
3. Publish the full image from a machine with about 100 GB of free disk: `docker login`, then `tools/publish_full.sh v0.2.0`. It pushes `biogemt/bioannohub:0.2.0-full`.
4. Update the version in the Get started commands above.
