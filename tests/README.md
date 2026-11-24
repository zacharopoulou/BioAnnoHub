# Tests

Run the unit and local flow tests from the repository root:

```bash
uv sync
uv run pytest -m 'not integration'
```

These tests use supplied annotator responses and temporary files. They cover
document ingestion, config validation, annotator adapters, report exports,
terminal setup, CLI errors, and saved run reproducibility. They do not require
optional model installations or live services.

For live PubMed integration checks:

```bash
uv run pytest -m integration
```

Integration checks require network access. Live model inference and external
annotator services should also be checked in their configured environments.

A local example that requires no network or models is:

```bash
uv run bioannohub demo
```
