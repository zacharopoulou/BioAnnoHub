from __future__ import annotations

import csv
import json

from bio_annotation.pipeline.output import write_pipeline_tsv_outputs


def test_documents_tsv_includes_selected_entrez_metadata(tmp_path) -> None:
    payload = {
        "documents": [
            {
                "document_id": "PMID:1",
                "pmid": "1",
                "title": "PubTator title",
                "year": "2024",
                "source": "pubtator3",
                "metadata": {
                    "pmcid": "PMC123",
                    "origin_sources": ["pubtator3", "entrez"],
                    "pubmed_record": {
                        "pmid": "1",
                        "title": "Entrez title",
                        "abstract": "Entrez abstract",
                        "year": "2024",
                        "authors": [{"name": "Ada Author"}],
                        "journal": "Journal of Tests",
                        "mesh_terms": ["Gene Expression", "Neoplasms"],
                        "elinks": {
                            "crossref_references": [{"DOI": "10.1000/example"}],
                            "s2_citations": [{"paperId": "s2-paper"}],
                        },
                    },
                    "citation_count": 27,
                    "is_open_access": True,
                    "europe_pmc_year": "2023",
                    "epmc_meta": {
                        "citedByCount": 27,
                        "isOpenAccess": "Y",
                        "pubYear": "2023",
                        "title": "Europe PMC title must not replace text",
                        "abstractText": "Europe PMC abstract must not replace text",
                        "fullTextUrlList": [{"url": "https://example.test/full-text"}],
                        "firstPublicationDate": "2023-01-02",
                    },
                },
            },
            {
                "document_id": "PMID:2",
                "pmid": "2",
                "title": "Another PubTator title",
                "source": "pubtator3",
                "metadata": {"origin_sources": ["pubtator3"]},
            },
        ],
        "annotations": [],
        "keywords": [],
    }

    write_pipeline_tsv_outputs(payload, tmp_path / "results.json")

    with (tmp_path / "results.documents.tsv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
        fieldnames = reader.fieldnames

    assert fieldnames is not None
    assert "entrez_authors" in fieldnames
    assert "entrez_mesh_terms" in fieldnames
    assert "entrez_title" not in fieldnames
    assert "europe_pmc_citation_count" in fieldnames
    assert "europe_pmc_authors" not in fieldnames
    assert "europe_pmc_title" not in fieldnames
    assert len(rows) == 2
    assert rows[0]["source"] == "pubtator3"
    assert rows[0]["title"] == "PubTator title"
    assert rows[0]["pmcid"] == "PMC123"
    assert rows[0]["origin_sources"] == "pubtator3|entrez"
    assert rows[0]["entrez_journal"] == "Journal of Tests"
    assert json.loads(rows[0]["entrez_authors"]) == [{"name": "Ada Author"}]
    assert json.loads(rows[0]["entrez_mesh_terms"]) == ["Gene Expression", "Neoplasms"]
    assert json.loads(rows[0]["entrez_elinks"]) == {
        "crossref_references": [{"DOI": "10.1000/example"}],
        "s2_citations": [{"paperId": "s2-paper"}],
    }
    assert rows[0]["europe_pmc_citation_count"] == "27"
    assert rows[0]["europe_pmc_is_open_access"] == "True"
    assert rows[0]["europe_pmc_year"] == "2023"
    assert json.loads(rows[0]["europe_pmc_full_text_urls"]) == [
        {"url": "https://example.test/full-text"}
    ]
    assert rows[0]["europe_pmc_firstPublicationDate"] == "2023-01-02"
    assert rows[1]["entrez_journal"] == ""
