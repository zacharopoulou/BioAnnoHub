# Scripts

This folder is reserved for small project scripts when they become necessary.

## Current state

The main runnable entrypoints currently live in the CLI:

- `uv run bioannohub inspect-config`
- `uv run bioannohub load-documents`
- `uv run bioannohub run-config`
- `uv run bioannohub search-pmids`

If dedicated scripts are added later, they should support the current repo
direction:

- corpus preparation
- query helpers
- benchmark preparation
- evaluation utilities
