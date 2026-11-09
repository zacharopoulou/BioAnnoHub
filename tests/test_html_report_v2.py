from __future__ import annotations

import json
import re
from pathlib import Path

from bio_annotation.report import html_report_v2_path
from bio_annotation.report.html_report_v2 import build_entity_data, write_html_report_v2


def _annotation(source: str, text: str, start: int, entity_type: str, canonical_id: str | None = None) -> dict:
    return {
        "document_id": "PMID:1",
        "source": source,
        "span_text": text,
        "entity_type": entity_type,
        "canonical_id": canonical_id,
        "canonical_name": None,
        "start": start,
        "end": start + len(text),
    }


TITLE = "BRCA1 in breast cancer"
ABSTRACT = "Breast cancer type 1 protein is studied. BRCA1 and tamoxifen were tested. TP53 is unrelated."
OFFSET = len(TITLE) + 2  # the abstract starts two characters after the title


def _payload() -> dict:
    abstract = lambda text, nth=0: OFFSET + [i for i in range(len(ABSTRACT)) if ABSTRACT.startswith(text, i)][nth]
    return {
        "document_count": 1,
        "annotation_summary": {"annotation_count": 6},
        "documents": [{"document_id": "PMID:1", "pmid": "1", "title": TITLE, "abstract": ABSTRACT}],
        "annotations": [
            _annotation("pubtator3", "BRCA1", 0, "gene", "672"),
            _annotation("bern2", "Breast cancer type 1 protein", abstract("Breast cancer type 1 protein"), "gene", "NCBIGene:672"),
            _annotation("flair", "BRCA1", abstract("BRCA1"), "gene"),
            _annotation("pubtator3", "breast cancer", 9, "disease", "MESH:D001943"),
            _annotation("pubtator3", "tamoxifen", abstract("tamoxifen"), "drug", "MESH:D013629"),
            _annotation("flair", "TP53", abstract("TP53"), "gene"),
        ],
    }


def _entity(data: dict, label_or_form: str) -> int:
    return data["lookup"][label_or_form.lower()]


def test_entities_with_the_same_id_are_one_entity() -> None:
    payload = _payload()
    data = build_entity_data(payload["documents"], payload["annotations"])
    brca1 = _entity(data, "BRCA1")
    # same ID (672 and NCBIGene:672) and same text without an ID: all one entity
    assert _entity(data, "Breast cancer type 1 protein") == brca1
    assert data["entities"][brca1]["ids"] == [{"id": "NCBIGene:672", "url": "https://www.ncbi.nlm.nih.gov/gene/672"}]
    assert "Breast cancer type 1 protein" in data["entities"][brca1]["forms"]
    # different text, no shared ID: separate entities
    assert len({_entity(data, name) for name in ("BRCA1", "breast cancer", "tamoxifen", "TP53")}) == 4
    mentions_of_brca1 = [m for m in data["mentions"] if m[0] == brca1]
    assert len(mentions_of_brca1) == 3


def test_mentions_point_into_their_sentence() -> None:
    payload = _payload()
    data = build_entity_data(payload["documents"], payload["annotations"])
    sentences = data["docs"][0]["sentences"]
    for entity, _doc, sentence, _source, _family, start, end in data["mentions"]:
        text = sentences[sentence][start:end].lower()
        entity_data = data["entities"][entity]
        assert text in {form.lower() for form in [entity_data["label"], *entity_data["forms"]]}


def test_v2_report_has_entity_types_tabs_and_explorer(tmp_path: Path) -> None:
    html = write_html_report_v2(_payload(), tmp_path / "results_v2.html").read_text(encoding="utf-8")
    # one "Entity types" button, opening a pop-up with two tabs
    assert 'data-open-dialog="entity-types-dialog"' in html
    assert re.search(r'<dialog[^>]*id="entity-types-dialog"[^>]*data-tabs', html)
    assert 'data-tab="distribution"' in html and 'data-tab="bioconcepts"' in html
    # Bioconcepts only inside pop-ups: the run's in the tabs, each document's behind its own button
    summary = html[html.index('<section class="summary">'):html.index("</section>")]
    assert "stats-panel" not in summary
    assert 'data-open-dialog="bioconcepts-doc-pmid-1"' in html
    # the explorer replaces the co-mention graph
    assert 'id="entity-explorer"' in html and 'id="entity-graph"' not in html
    data = json.loads(re.search(r'<script type="application/json" id="explorer-data">(.*?)</script>', html, re.S).group(1))
    assert data["entities"] and data["mentions"]
    for control in ("search", "family", "source", "mode"):
        assert f'data-explorer="{control}"' in html
    assert 'class="explore-button"' in html  # "Show in entity explorer" in the side bar


def test_v2_report_without_annotations(tmp_path: Path) -> None:
    html = write_html_report_v2({"documents": [], "annotations": []}, tmp_path / "r.html").read_text(encoding="utf-8")
    assert "No documents in this run." in html
    assert 'id="entity-explorer"' not in html


def test_v2_report_is_written_next_to_the_first_report() -> None:
    assert html_report_v2_path(Path("run/results/results.json")) == Path("run/results/results_v2.html")
