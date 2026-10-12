# RadGraph-XL - local benchmark data

**No data is committed here, and none may be.** RadGraph-XL is PhysioNet
credentialed data (PhysioNet Credentialed Health Data License 1.5.0), which
may not be shared. Everything in this folder except this README is in
`.gitignore`. 

## Getting the data

1. Prerequisite to get credentialed PhysioNet access and sign the data use agreement for
   https://physionet.org/content/radgraph-xl/1.0.0/
2. Then the zip can be dwnloaded.
3. Convert it to `radgraph_xl.jsonl`. If the zip is still in your
   Downloads folder under its original name, no path is needed; otherwise
   add the zip's path at the end. The script first checks that the file is
   the official 1.0.0 release.

```
uv run python benchmarks/scripts/radgraph_xl.py [path/to/the.zip]
```

4. Optionally, write a summary (`RADGRAPH_XL_ANALYTICS_SUMMARY.md`, kept
   local):

```
uv run python benchmarks/analytics/radgraph_xl_analytics.py
```

## What it contains

RadGraph-XL (Delbrouck et al., Findings of ACL 2024): radiology reports
annotated by radiologists. The PhysioNet release has only the **MIMIC**
reports: 100 chest CT, 100 abdomen/pelvis CT and 100 brain MR, with **no
train/test split**. Each document is one report (`{part}_{doc_key}`, for
example `mimic-chest-ct_12`). The source has tokens only, so the text is
the tokens joined by single spaces.

| Type | Mentions |
|---|---|
| Anatomy::definitely present / absent / uncertain | 13,243 / 18 / 14 |
| Observation::definitely present / absent / uncertain | 11,505 / 2,597 / 754 |

- Anatomy: body parts. Observation: findings and diseases.
- No normalization. 20,778 of the 28,131 mentions are a single token:
  RadGraph annotates short units and links them with relations.
- 23 spans carry two labels; both are kept.
- 21,289 relations: `modify` 11,765, `located_at` 8,566, `suggestive_of` 958.

## For evaluating stanza_radiology

A fair test: Stanza radiology was trained on 150 chest CT reports
(Hassanpour and Langlotz, 2016), not on RadGraph-XL. Compare `Anatomy`
with Anatomy::* and `Observation` with Observation::*.

- **Uncertainty** cannot be scored directly: RadGraph puts the certainty on
  the finding (`Observation::uncertain`), not on the hedging word.
- **Spans are shorter** than Stanza's, so report lenient (overlap) matching
  alongside exact matching, and report each part separately.
