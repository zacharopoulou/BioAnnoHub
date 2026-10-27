# Source Package

This package contains the current implementation of the BioAnnoHub pipeline.

## Implemented areas

- `schemas/`: shared `Document` and `Annotation` contracts
- `io/`: PubMed search plus PMID metadata readers and enrichments
- `preprocessing/`: canonical document loading from PMIDs, files, and corpora
- `annotators/`: primary annotator adapter API
- `entity_proposal/`: compatibility layer for the older annotator package name
- `pipeline_config.py`: config parsing and validation
- `pipeline/`: pipeline orchestration split across runner, execution, options, output, manifest, and progress modules
- `pipeline_runner.py`: backward-compatible imports for the pipeline package
- `cli.py`: repo-facing command-line entry points

## Direction

The next repo-level additions should support:

- benchmark dataset ingestion
- evaluation and comparison outputs
- richer annotator runtime integration
