# Data

`inputs/` contains small PMID and text-table examples used by the annotation pipeline.

Use the tracked text table or PMID list with the examples in
[the configuration guide](../configs/README.md). Corpus JSON files can also be
loaded with `input.mode = "corpus"` and `input.corpus_path`.

Generated query outputs such as `query_pmids.txt` are local working files and
are ignored by Git. Keep large corpora and generated payloads outside Git.
