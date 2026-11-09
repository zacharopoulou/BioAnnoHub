"""Entity-oriented version of the HTML report (results_v2.html), written next to results.html.

Differences from html_report.py:
- the "Bioconcepts" panels move into pop-ups: the summary's "Entity types" button opens
  the distribution and the run's Bioconcepts as two tabs, and each document has its own button;
- the co-mention graph is replaced by an entity explorer: search for an entity (or pick one
  from the list of all entities, by type) and see the entities it is mentioned with, one at a time;
- entities with the same ID count as one entity, whatever text they were written with.

Everything else (highlights, side bar contents, comparison table) reuses html_report.py.
"""
from __future__ import annotations

import json
from bisect import bisect_right
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

from bio_annotation.report.html_report import (
    _ANNOTATOR_LABELS,
    _FAMILY_LABELS,
    _anchor_for,
    _annotated_text,
    _compute_stats,
    _database_link,
    _format_canonical_id,
    _is_real_canonical_id,
    _json_safe,
    _render_annotator_table,
    _render_comparison_table,
    _render_config,
    _render_documents_overview,
    _render_filter_bar,
    _render_stats_panel,
    _render_type_histogram,
    _source_priority,
    _span_key,
    _split_annotations_by_region,
    _trim_spans,
    _type_label,
    entity_family,
    group_annotations_by_span,
    sentence_spans,
)

_TEMPLATE_PATH = Path(__file__).resolve().parent / "template_v2.html"


def write_html_report_v2(payload: dict[str, Any], output_path: Path) -> Path:
    """Writes the entity-oriented report. Returns the absolute path of the file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    output_path.write_text(template.replace("<!--CONTENT-->", _render_body(payload)), encoding="utf-8")
    return output_path.resolve()


def _render_body(payload: dict[str, Any]) -> str:
    summary = payload.get("annotation_summary") or {}
    documents = list(payload.get("documents") or [])
    annotations = list(payload.get("annotations") or [])

    annotators_used = sorted(
        {a.get("source") for a in annotations if a.get("source")}, key=_source_priority
    )
    total_annotations = summary.get("annotation_count", len(annotations))
    document_count = payload.get("document_count", len(documents))

    parts: list[str] = ['<section class="summary">', '<div class="summary-headline">']
    parts.append(
        f'<p class="lede"><span class="big-number">{total_annotations}</span> '
        f'annotation{"s" if total_annotations != 1 else ""} across '
        f'<span class="big-number">{document_count}</span> '
        f'document{"s" if document_count != 1 else ""}</p>'
    )
    if annotations:
        parts.append(
            '<button type="button" class="dist-button" data-open-dialog="entity-types-dialog">'
            "Entity types</button>"
        )
        parts.append(_render_annotator_table(annotators_used, annotations))
    else:
        parts.append('<p class="meta">Annotators: none</p>')
    parts.append("</div></section>")

    if annotations:
        parts.append(_render_entity_types_dialog(annotations))
        if documents:
            parts.append(_render_explorer(documents, annotations, annotators_used))
    if len(documents) > 1:
        parts.append(_render_documents_overview(documents, annotations))
    if annotations:
        parts.append(_render_filter_bar(annotators_used, annotations))

    for document in documents:
        parts.append(_render_document(document, annotations, annotators_used))
    if not documents:
        parts.append('<p class="hint">No documents in this run.</p>')

    parts.append(_render_config(annotators_used, annotations))
    return "\n".join(parts)


def _dialog(dialog_id: str, title: str, body: str, *, tabs: bool = False) -> str:
    """A pop-up (<dialog>) with a title and a close button; opened by a data-open-dialog button."""
    return (
        f'<dialog class="dist-dialog" id="{escape(dialog_id, quote=True)}" aria-labelledby="{escape(dialog_id, quote=True)}-title"'
        f'{" data-tabs" if tabs else ""}>'
        '<div class="dist-dialog-body"><div class="dist-dialog-header">'
        f'<h3 id="{escape(dialog_id, quote=True)}-title">{escape(title)}</h3>'
        '<button type="button" class="entity-popup-close" data-close-dialog aria-label="Close">&times;</button></div>'
        f"{body}</div></dialog>"
    )


def _render_entity_types_dialog(annotations: list[dict[str, Any]]) -> str:
    """The summary's "Entity types" pop-up: Distribution and Bioconcepts tabs."""
    bioconcepts = _render_stats_panel(_compute_stats(annotations), heading="Bioconcepts in this run", css_class="stats-run")
    body = (
        '<div class="tabs" role="tablist">'
        '<button type="button" class="tab" role="tab" data-tab="distribution" aria-selected="true">Distribution</button>'
        '<button type="button" class="tab" role="tab" data-tab="bioconcepts" aria-selected="false">Bioconcepts</button>'
        "</div>"
        f'<div class="tab-panel" data-tab-panel="distribution">{_render_type_histogram(annotations)}</div>'
        '<div class="tab-panel" data-tab-panel="bioconcepts" hidden>'
        '<p class="hint">Click a keyword to explore it in the entity explorer.</p>'
        f"{bioconcepts}</div>"
    )
    return _dialog("entity-types-dialog", "Entity types", body, tabs=True)


def _render_document(
    document: dict[str, Any],
    all_annotations: list[dict[str, Any]],
    annotators: list[str] | None = None,
) -> str:
    """One document, as in html_report.py, with its Bioconcepts behind a button."""
    document_id = document.get("document_id")
    document_annotations = [a for a in all_annotations if a.get("document_id") == document_id]
    comparison_rows = group_annotations_by_span(document_annotations)
    cross_lookup = {_span_key(row["keyword"]): row["by_source"] for row in comparison_rows}

    title_text = (document.get("title") or "").strip()
    abstract_text = (document.get("abstract") or "").strip()
    title_annotations, abstract_annotations = _split_annotations_by_region(document_annotations, len(title_text))

    title_html = (
        _annotated_text("span", "annotated-title", title_text, title_annotations, cross_lookup)
        if title_text
        else escape(str(document_id or "Document"))
    )
    pmid = document.get("pmid")
    pmid_html = (
        f' | PMID: <a href="https://pubmed.ncbi.nlm.nih.gov/{escape(str(pmid))}/" target="_blank" rel="noopener">{escape(str(pmid))}</a>'
        if pmid else ""
    )

    anchor = _anchor_for(str(document_id or ""))
    plain_title = escape(title_text) if title_text else escape(str(document_id or "Document"))
    annotation_count = len(document_annotations)
    count_label = f'{annotation_count} annotation{"s" if annotation_count != 1 else ""}'
    stats = _compute_stats(document_annotations)

    parts: list[str] = [f'<details class="document" id="{escape(anchor, quote=True)}" open>']
    parts.append(
        f'<summary class="doc-summary"><span class="doc-summary-title">{plain_title}</span>'
        f'<span class="doc-summary-count">{count_label}</span></summary>'
    )
    parts.append('<div class="doc-body">')
    parts.append(f"<h2>{title_html}</h2>")
    parts.append(f'<p class="meta">{pmid_html}{" | " if pmid else ""}{count_label} on this document</p>')
    if stats:
        dialog_id = f"bioconcepts-{anchor}"
        parts.append(
            f'<button type="button" class="dist-button" data-open-dialog="{escape(dialog_id, quote=True)}">'
            "Bioconcepts in this document</button>"
        )
        parts.append(_dialog(
            dialog_id,
            "Bioconcepts in this document",
            '<p class="hint">Click a keyword to explore it in the entity explorer.</p>'
            + _render_stats_panel(stats, heading="Bioconcepts in this document", css_class="stats-doc"),
        ))
    parts.append('<div class="doc-main">')
    parts.append("<h3>Abstract</h3>")
    parts.append('<p class="hint">Highlights show entities found by any annotator. Click a highlight for full details across annotators.</p>')
    if abstract_text:
        parts.append(_annotated_text("div", "annotated-text", abstract_text, abstract_annotations, cross_lookup))
    else:
        parts.append('<div class="annotated-text"><span class="hint">No abstract available.</span></div>')
    parts.append("</div>")

    parts.append(
        f'<details class="comparison-section" open>'
        f'<summary><h3>Comparison across annotators</h3>'
        f'<span class="hint">{len(comparison_rows)} unique keyword'
        f'{"s" if len(comparison_rows) != 1 else ""} found by at least one annotator</span></summary>'
    )
    parts.append('<div class="comparison-scroll">')
    parts.append(_render_comparison_table(comparison_rows, annotators))
    parts.append("</div></details>")
    parts.append("</div></details>")
    return "\n".join(parts)


def _text_key(text: str) -> str:
    return "t:" + _span_key(text)


def _id_key(canonical_id: Any, entity_type: str | None) -> str:
    return "i:" + _format_canonical_id(canonical_id, (entity_type or "").lower())


def build_entity_data(documents: list[dict[str, Any]], annotations: list[dict[str, Any]]) -> dict[str, Any]:
    """Entities, documents and mentions for the entity explorer.

    Mentions are grouped into entities by their text (case and extra spaces ignored)
    and by their ID: two mentions with the same ID, or the same text, are the same
    entity. So "BRCA1" and "breast cancer type 1 protein", both NCBIGene:672, are one
    entity, and so is an annotator's "BRCA1" without an ID.

    Each mention is [entity, document, sentence, annotator, family, start, end],
    with start and end inside the sentence, so the page can mark it.
    """
    docs: list[dict[str, Any]] = []
    raw_mentions: list[tuple[str, list[Any], dict[str, Any], str]] = []

    # union-find over text and ID keys: everything joined by a mention is one entity
    parent: dict[str, str] = {}

    def find(key: str) -> str:
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for document in documents:
        document_id = document.get("document_id")
        title_text = (document.get("title") or "").strip()
        abstract_text = (document.get("abstract") or "").strip()
        document_annotations = [a for a in annotations if a.get("document_id") == document_id]
        title_annotations, abstract_annotations = _split_annotations_by_region(document_annotations, len(title_text))

        sentences: list[str] = []
        doc_number = len(docs)
        for region_text, region_annotations in ((title_text, title_annotations), (abstract_text, abstract_annotations)):
            spans = sentence_spans(region_text) if region_text else []
            if not spans:
                continue
            starts = [start for start, _ in spans]
            first_sentence = len(sentences)
            sentences.extend(region_text[start:end] for start, end in spans)
            for annotation in _trim_spans(region_text, region_annotations):
                start, end = annotation.get("start"), annotation.get("end")
                if start is None or end is None or end <= start:
                    continue
                surface = " ".join(region_text[start:end].split())
                if not surface:
                    continue
                text_key = _text_key(surface)
                find(text_key)
                if _is_real_canonical_id(annotation.get("canonical_id")):
                    union(text_key, _id_key(annotation.get("canonical_id"), annotation.get("entity_type")))
                sentence = max(bisect_right(starts, start) - 1, 0)
                sentence_start, sentence_end = spans[sentence]
                raw_mentions.append((
                    text_key,
                    [
                        doc_number,
                        first_sentence + sentence,
                        annotation.get("source") or "unknown",
                        entity_family(annotation.get("entity_type")),
                        max(start - sentence_start, 0),
                        min(end, sentence_end) - sentence_start,
                    ],
                    annotation,
                    surface,
                ))
        docs.append(
            {
                "id": str(document_id or ""),
                "pmid": str(document.get("pmid") or ""),
                "title": title_text or str(document_id or "Document"),
                "anchor": _anchor_for(str(document_id or "")),
                "sentences": sentences,
            }
        )

    entity_of_root: dict[str, int] = {}
    forms: list[Counter] = []
    families: list[Counter] = []
    types: list[set[str]] = []
    ids: list[dict[str, str | None]] = []
    names: list[Counter] = []
    mentions: list[list[Any]] = []
    for text_key, mention, annotation, surface in raw_mentions:
        root = find(text_key)
        if root not in entity_of_root:
            entity_of_root[root] = len(forms)
            forms.append(Counter())
            families.append(Counter())
            types.append(set())
            ids.append({})
            names.append(Counter())
        entity = entity_of_root[root]
        entity_type = annotation.get("entity_type")
        forms[entity][surface] += 1
        families[entity][mention[3]] += 1
        types[entity].add(_type_label(entity_type))
        canonical_id = annotation.get("canonical_id")
        if _is_real_canonical_id(canonical_id):
            shown = _format_canonical_id(canonical_id, (entity_type or "").lower())
            ids[entity].setdefault(shown, _database_link(shown, (entity_type or "").lower()))
        if annotation.get("canonical_name"):
            names[entity][str(annotation["canonical_name"])] += 1
        mentions.append([entity, *mention])

    entities = []
    for entity in range(len(forms)):
        label = forms[entity].most_common(1)[0][0]
        entities.append(
            {
                "label": label,
                "fam": families[entity].most_common(1)[0][0],
                "types": sorted(types[entity]),
                "forms": [form for form, _ in forms[entity].most_common() if _span_key(form) != _span_key(label)],
                "ids": [{"id": shown, "url": url} for shown, url in sorted(ids[entity].items())],
                "names": [name for name, _ in names[entity].most_common(5)],
            }
        )
    # text keys of every entity, so a highlight or a Bioconcepts keyword can find its entity
    lookup = {key[2:]: entity_of_root[find(key)] for key in parent if key.startswith("t:") and find(key) in entity_of_root}
    return {"docs": docs, "entities": entities, "mentions": mentions, "lookup": lookup}


def _render_explorer(
    documents: list[dict[str, Any]], annotations: list[dict[str, Any]], annotators: list[str]
) -> str:
    """The entity explorer: search and filters, the list of entities, and the graph of one entity."""
    data = build_entity_data(documents, annotations)
    if not data["entities"]:
        return ""
    present_families = {entity["fam"] for entity in data["entities"]}
    family_options = "".join(
        f'<option value="{family}">{escape(label)}</option>'
        for family, label in _FAMILY_LABELS.items()
        if family in present_families
    )
    source_options = "".join(
        f'<option value="{escape(name, quote=True)}">{escape(_ANNOTATOR_LABELS.get(name, name))}</option>'
        for name in annotators
    )
    document_control = ""
    if len(data["docs"]) > 1:
        options = []
        for number, doc in enumerate(data["docs"]):
            name = doc["title"] if len(doc["title"]) <= 60 else doc["title"][:57] + "..."
            prefix = f'PMID {doc["pmid"]}: ' if doc["pmid"] else ""
            options.append(f'<option value="{number}">{escape(prefix + name)}</option>')
        document_control = (
            '<label>Document <select data-explorer="doc"><option value="all">All documents</option>'
            f'{"".join(options)}</select></label>'
        )
    # "</" cannot appear inside a <script> element, so escape it in the JSON.
    payload = json.dumps(_json_safe(data), ensure_ascii=False).replace("</", "<\\/")
    return (
        '<section class="explorer-section" id="entity-explorer">'
        "<h3>Entity explorer</h3>"
        '<p class="hint">Search for an entity, or pick one from the list, to see the entities it is '
        "mentioned with. Click a connected entity to explore it next. Entities with the same ID count as one.</p>"
        '<div class="explorer-controls">'
        '<div class="explorer-search">'
        '<input type="search" data-explorer="search" placeholder="Search an entity or an ID" '
        'autocomplete="off" aria-label="Search an entity">'
        '<ul class="explorer-suggestions" role="listbox" hidden></ul></div>'
        f'<label>Type <select data-explorer="family"><option value="all">All types</option>{family_options}</select></label>'
        f'<label>Annotator <select data-explorer="source"><option value="all">All annotators</option>{source_options}</select></label>'
        f"{document_control}"
        '<label>Linked when in the same <select data-explorer="mode">'
        '<option value="sentence">sentence</option><option value="document">document</option></select></label>'
        "</div>"
        '<div class="explorer-nav" hidden>'
        '<button type="button" class="explorer-nav-button" data-explorer="back">&larr; Back</button>'
        '<button type="button" class="explorer-nav-button" data-explorer="list">All entities</button>'
        '<span class="explorer-trail"></span></div>'
        '<div class="explorer-list"></div>'
        '<div class="graph-layout explorer-view" hidden>'
        '<div class="graph-canvas"><svg role="img" aria-label="Entities mentioned with the selected entity"></svg>'
        '<p class="graph-empty hint" hidden>No connected entities with the current filters.</p></div>'
        '<aside class="graph-panel"></aside>'
        "</div>"
        f'<script type="application/json" id="explorer-data">{payload}</script>'
        "</section>"
    )
