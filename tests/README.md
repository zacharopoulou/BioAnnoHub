# Tests

Tests run inside the BioAnnoHub image, so they use the same environment as users. From the repository root, after `docker build -t bioannohub .`:

```bash
docker run --rm --entrypoint python -w /repository bioannohub -m pytest -m 'not integration'
```

To test local edits without rebuilding, mount your source over the image's copy:

```bash
docker run --rm --entrypoint python -w /repository \
  -v "$PWD/src:/repository/src" -v "$PWD/tests:/repository/tests" -v "$PWD/configs:/repository/configs" \
  bioannohub -m pytest -m 'not integration'
```

These tests use supplied annotator responses and temporary files. They cover
document ingestion, config validation, annotator adapters, report exports,
terminal setup, CLI errors, and saved run reproducibility. They do not run the
models or call live services.

For live PubMed integration checks, which need network access, replace
`-m 'not integration'` with `-m integration`. Live model inference and external
annotator services should also be checked in their configured environments.

A local example that requires no network or models is:

```bash
docker run --rm bioannohub demo
```
