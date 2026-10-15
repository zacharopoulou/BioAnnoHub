# Benchmarks download

`bioannohub download-benchmarks` downloads the benchmark corpora into
`benchmarks/data/`: all of them, or the ones picked from a list. Run it from
the repository:

```
uv run --extra benchmarks bioannohub download-benchmarks            # pick from a list
uv run --extra benchmarks bioannohub download-benchmarks --all      # everything public
uv run bioannohub download-benchmarks --list                        # just shows the table
```

At the prompt, choose by number (`1,3,5-8`), by name (`biored ncbi`) or
`all`. Press Enter to quit.

Each benchmark has its own script in `benchmarks/scripts/`. The command
runs them one after the other and prints a short summary. A benchmark whose
files are already on disk is skipped by its script, so running it again is
safe.

RadGraph-XL is never part of `--all`: it is PhysioNet credentialed data that
each user downloads by hand. Once its zip is in `~/Downloads`, pick it from
the list.

## Analytics

Each benchmark has one script in `benchmarks/analytics/` that reads its downloaded files and writes
`benchmarks/data/<benchmark>/<BENCHMARK>_ANALYTICS_SUMMARY.md`

The summaries are committed, so they can be read without downloading
anything. The RadGraph-XL summary is the exception: it quotes report text,
so it stays local.
