# RaTE-NER - local benchmark data

Only `test.jsonl` is committed; `train.jsonl` and `validation.jsonl` are in
`.gitignore`. To regenerate all three (no extra dependencies):

```
uv run python benchmarks/scripts/rate_ner.py
```

RaTE-NER (Zhao et al., EMNLP 2024) is a **radiology** NER dataset covering
9 imaging modalities and 23 body regions. It is not in BigBIO: the script
downloads it from Hugging Face (`Angelakeke/RaTE-NER`, pinned revision,
licence **CC BY-NC 4.0**) and converts it to `bigbio_kb`. It counts as a
clinical benchmark and is a main test for `stanza_radiology`.

## Only the Radiopaedia part

The **MIMIC-IV** part (real hospital reports, normally credentialed
PhysioNet data) is left out for now. Only the **Radiopaedia** part is used:
sentences from case write-ups on a radiology teaching site.

| Split | Sentences | Mentions | Labels made by |
|---|---|---|---|
| train | 30,005 | 84,218 | GPT-4 and medical knowledge bases |
| validation | 3,600 | 10,025 | GPT-4 and medical knowledge bases |
| test | 3,529 | 10,265 | **by hand** |

No case appears in both train and test.

- Each document is **one sentence**; `document_id` is the Radiopaedia case
  number.
- The text is the tokens joined by single spaces, so punctuation is
  separated, and **all text is lower case**.
- No normalization.

## Entity types

| Type | Meaning | Most frequent in test |
|---|---|---|
| Anatomy | body parts | lungs, liver, spleen |
| Abnormality | radiological findings | enlarged, fracture, thickening |
| Disease | diagnoses | hydrocephalus, pneumothorax |
| Non-Abnormality | a normal finding, or a negated abnormality | normal, clear, intact, (no) effusion |
| Non-Disease | a negated disease | (no) pneumothorax, (no) fracture |

- Spans can overlap (254 pairs in test).
- Labels are not fully consistent: *normal* is Non-Abnormality 54 times
  but Abnormality 42 times, and *mass* is Anatomy 36 times.
- The 4 empty spans in the train file are skipped.

## For evaluating stanza_radiology

A fair test: Stanza radiology was trained on 150 chest CT reports
(Hassanpour and Langlotz, 2016), not on RaTE-NER. Compare:

- `Anatomy` with Anatomy
- `Observation` with Abnormality + Disease + Non-Abnormality + Non-Disease:
  Stanza tags negated findings (*effusion* in "no pleural effusion") and
  normal findings (*clear*, *normal*) as `Observation`.

The modifiers and `Uncertainty` have no counterpart here.
`RATE_NER_ANALYTICS_SUMMARY.md` (from
`benchmarks/analytics/rate_ner_analytics.py`) summarizes all three splits.
