from __future__ import annotations

import csv

from bio_annotation.pipeline_runner import write_pipeline_tsv_outputs


def test_tsv_outputs_include_normalization_score(tmp_path) -> None:
    payload = {
        "documents": [
            {
                "document_id": "doc1",
                "pmid": "1",
                "title": "PTEN study",
            }
        ],
        "annotations": [
            {
                "document_id": "doc1",
                "annotation_id": "ann1",
                "source": "flair",
                "span_text": "PTEN",
                "start": 0,
                "end": 4,
                "entity_type": "gene",
                "canonical_id": "NCBIGene:5728",
                "canonical_name": "PTEN",
                "confidence": 0.99,
                "normalization_score": 211.5,
            }
        ],
        "keywords": [
            {
                "document_id": "doc1",
                "keyword": "PTEN",
                "annotation_count": 1,
                "annotator_count": 1,
                "labels": ["gene"],
                "canonical_ids": ["NCBIGene:5728"],
                "annotation_ids": ["ann1"],
                "mentions": [
                    {
                        "start": 0,
                        "end": 4,
                        "annotation_ids": ["ann1"],
                    }
                ],
            }
        ],
    }

    write_pipeline_tsv_outputs(payload, tmp_path / "results.json")

    with (tmp_path / "results.annotations.tsv").open(
        encoding="utf-8", newline=""
    ) as handle:
        annotation_row = next(csv.DictReader(handle, delimiter="\t"))

    with (tmp_path / "results.keyword_annotator_evidence.tsv").open(
        encoding="utf-8", newline=""
    ) as handle:
        evidence_row = next(csv.DictReader(handle, delimiter="\t"))

    for row in (annotation_row, evidence_row):
        assert row["confidence"] == "0.99"
        assert row["normalization_score"] == "211.5"
