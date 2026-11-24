from __future__ import annotations

import csv
import json

from bio_annotation.pipeline.output import write_pipeline_output


def test_documents_tsv_has_stable_compact_metadata_columns(tmp_path) -> None:
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
                        "doi": "10.1000/example",
                        "authors": [{"name": "Ada Author"}],
                        "journal": "Journal of Tests",
                        "issn": ["1234-5678", "8765-4321"],
                        "volume": "12",
                        "issue": "3",
                        "pages": "10-20",
                        "pub_date": "2024-03-01",
                        "publication_type": ["Journal Article"],
                        "keywords": ["glioblastoma", "RNA"],
                        "mesh_terms": [
                            {"descriptor": "Gene Expression"},
                            {"descriptor": "Neoplasms"},
                        ],
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

    write_pipeline_output(payload, tmp_path / "results.json")
    saved_payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    saved_metadata = saved_payload["documents"][0]["metadata"]
    assert (
        saved_metadata["pubmed_record"]["elinks"]
        == payload["documents"][0]["metadata"]["pubmed_record"]["elinks"]
    )
    assert saved_metadata["epmc_meta"]["fullTextUrlList"] == [
        {"url": "https://example.test/full-text"}
    ]

    with (tmp_path / "results.documents.tsv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
        fieldnames = reader.fieldnames

    assert fieldnames is not None
    assert fieldnames == [
        "document_id",
        "pmid",
        "pmcid",
        "title",
        "year",
        "source",
        "origin_sources",
        "doi",
        "entrez_country",
        "entrez_journal",
        "entrez_journal_abbrev",
        "entrez_issn",
        "entrez_volume",
        "entrez_issue",
        "entrez_pages",
        "entrez_pub_date",
        "entrez_publication_type",
        "entrez_keywords",
        "entrez_mesh_terms",
        "europe_pmc_citation_count",
        "europe_pmc_is_open_access",
        "europe_pmc_license",
        "europe_pmc_first_publication_date",
    ]
    assert "entrez_mesh_terms" in fieldnames
    assert "entrez_authors" not in fieldnames
    assert "entrez_elinks" not in fieldnames
    assert "europe_pmc_citation_count" in fieldnames
    assert "europe_pmc_full_text_urls" not in fieldnames
    assert len(rows) == 2
    assert rows[0]["source"] == "pubtator3"
    assert rows[0]["title"] == "PubTator title"
    assert rows[0]["pmcid"] == "PMC123"
    assert rows[0]["origin_sources"] == "pubtator3|entrez"
    assert rows[0]["doi"] == "10.1000/example"
    assert rows[0]["entrez_journal"] == "Journal of Tests"
    assert rows[0]["entrez_issn"] == "1234-5678|8765-4321"
    assert rows[0]["entrez_publication_type"] == "Journal Article"
    assert rows[0]["entrez_keywords"] == "glioblastoma|RNA"
    assert rows[0]["entrez_mesh_terms"] == "Gene Expression|Neoplasms"
    assert rows[0]["europe_pmc_citation_count"] == "27"
    assert rows[0]["europe_pmc_is_open_access"] == "True"
    assert rows[0]["europe_pmc_first_publication_date"] == "2023-01-02"
    assert rows[1]["entrez_journal"] == ""
