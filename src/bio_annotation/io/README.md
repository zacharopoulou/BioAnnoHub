# PubMed PMID Search

The `search-pmids` CLI command is implemented by `search.py`. It builds PubMed ESearch requests and writes matching PMIDs to a plain text file.

## Query Syntax

`search-pmids` does not define a BioAnnoHub-specific query language. The `--query` value and each `--filter` value are passed to PubMed ESearch syntax.

That means you can use standard PubMed Boolean operators and field tags, including:

- `[MeSH Terms]`
- `[Publication Type]`
- `[Language]`
- `[Date - Publication]`

Each repeated `--filter` value is appended to the query with `AND`.

## Examples

Free-text search:

```bash
uv run totalannotator search-pmids \
  --query 'glioblastoma AND microRNA' \
  --output data/inputs/query_pmids.txt
```

MeSH search:

```bash
uv run totalannotator search-pmids \
  --query '"Glioblastoma"[MeSH Terms] AND "MicroRNAs"[MeSH Terms]' \
  --output data/inputs/query_pmids.txt
```

Publication type filter:

```bash
uv run totalannotator search-pmids \
  --query 'glioblastoma AND microRNA' \
  --filter '"Review"[Publication Type]' \
  --output data/inputs/query_pmids.txt
```

Multiple filters with date bounds:

```bash
uv run totalannotator search-pmids \
  --query '"Glioblastoma"[MeSH Terms]' \
  --filter '"Review"[Publication Type]' \
  --filter 'english[Language]' \
  --date-from 2020 \
  --date-to 2024 \
  --output data/inputs/query_pmids.txt
```

## Output

The command writes one PMID per line to the path passed with `--output`.

It also prints a JSON summary after the search completes. Progress messages are written to stderr so stdout remains usable by scripts. During longer searches, the command reports each publication-date window, when a large window is split, and the number of PMIDs collected so far.

## Large Result Sets

PubMed ESearch returns at most 10,000 PMIDs per request. When a query is larger than that cap, BioAnnoHub splits the publication-date range into smaller windows and merges the resulting PMIDs.
