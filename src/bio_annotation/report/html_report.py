from __future__ import annotations

import json
import math
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from typing import Any

_TEMPLATE_PATH = Path(__file__).resolve().parent / "template.html"

# When annotators overlap on the same span, the first one in this order is drawn;
# any annotator not listed comes after these, in alphabetical order.
_SOURCE_PRIORITY: dict[str, int] = {"pubtator3": 0, "bern2": 1, "flair": 2}

# Show each annotator by its canonical display name (the same label used in the
# terminal menu), not its internal id. Falls back to the raw id for anything not
# in the capability registry.
from bio_annotation.entity_types import ANNOTATOR_DISPLAY_NAMES
from bio_annotation.report.umls_semantic_types import UMLS_SEMANTIC_TYPE_NAMES

_ANNOTATOR_LABELS: dict[str, str] = dict(ANNOTATOR_DISPLAY_NAMES)

# Every entity type belongs to one colour family, so types added by new annotators
# get a colour without touching the CSS. The family colours are defined in
# template.html; the type itself is shown as a small label inside the highlight.
_FAMILY_LABELS: dict[str, str] = {
    "gene": "Gene / protein",
    "drug": "Chemical / drug",
    "disease": "Disease / problem",
    "species": "Species",
    "variant": "Variant",
    "cell": "Cell",
    "anatomy": "Anatomy",
    "procedure": "Test / treatment",
    "clinical": "Clinical detail",
    "other": "Other",
}
_FAMILY_OF_TYPE: dict[str, str] = {
    **dict.fromkeys(("gene", "dna", "rna", "sequence_ontology"), "gene"),
    **dict.fromkeys(("drug", "amino_acid"), "drug"),
    **dict.fromkeys(
        ("disease", "problem", "sign_symptom", "cancer", "pathological_formation", "observation"), "disease"
    ),
    "species": "species",
    "variant": "variant",
    **dict.fromkeys(("cell_line", "cell_type", "cell", "cell_component", "cellular_component"), "cell"),
    **dict.fromkeys(
        (
            "anatomical", "anatomical_system", "organ", "tissue", "multi_tissue_structure",
            "organism_subdivision", "organism_substance", "immaterial_anatomical_entity",
            "developing_anatomical_structure", "biological_structure",
        ),
        "anatomy",
    ),
    **dict.fromkeys(
        ("test", "treatment", "diagnostic_procedure", "therapeutic_procedure", "lab_value", "dosage", "administration"),
        "procedure",
    ),
    **dict.fromkeys(
        (
            "anatomy_modifier", "observation_modifier", "uncertainty", "severity", "detailed_description",
            "color", "shape", "texture", "area", "volume", "distance", "height", "weight", "mass",
            "quantitative_concept", "qualitative_concept", "frequency", "duration", "date", "time", "age",
            "sex", "subject", "occupation", "history", "family_history", "personal_background", "activity",
            "clinical_event", "outcome", "nonbiological_location", "biological_attribute", "coreference",
            "other_event", "other_entity",
        ),
        "clinical",
    ),
}
# MedCAT returns UMLS semantic type codes (TUIs) instead of type names.
_FAMILY_OF_TUI: dict[str, str] = {
    **dict.fromkeys(("T028", "T086", "T114", "T116", "T087", "T088"), "gene"),
    **dict.fromkeys(
        ("T103", "T104", "T109", "T120", "T121", "T122", "T123", "T125", "T126", "T127", "T129",
         "T130", "T131", "T167", "T192", "T195", "T196", "T197", "T200"),
        "drug",
    ),
    **dict.fromkeys(
        ("T019", "T020", "T033", "T037", "T046", "T047", "T048", "T049", "T050", "T184", "T190", "T191"), "disease"
    ),
    **dict.fromkeys(
        ("T001", "T002", "T004", "T005", "T007", "T008", "T010", "T011", "T012", "T013", "T014",
         "T015", "T016", "T194", "T204"),
        "species",
    ),
    **dict.fromkeys(("T025", "T026"), "cell"),
    **dict.fromkeys(("T017", "T018", "T021", "T022", "T023", "T024", "T029", "T030", "T031"), "anatomy"),
    **dict.fromkeys(("T058", "T059", "T060", "T061", "T063"), "procedure"),
    **dict.fromkeys(("T034", "T201"), "clinical"),
}


def entity_family(entity_type: str | None) -> str:
    """The colour family of an entity type ("other" for anything unknown)."""
    key = (entity_type or "").strip()
    if key.upper() in _FAMILY_OF_TUI:
        return _FAMILY_OF_TUI[key.upper()]
    return _FAMILY_OF_TYPE.get(key.lower(), "other")


def _tui_name(entity_type: str | None) -> str | None:
    """Name of a UMLS semantic type code (MedCAT), e.g. "T191" -> "Neoplastic Process"."""
    return UMLS_SEMANTIC_TYPE_NAMES.get((entity_type or "").strip().upper())


def _type_label(entity_type: str | None) -> str:
    """Readable label of an entity type: known label, else the type with spaces."""
    tui_name = _tui_name(entity_type)
    if tui_name:
        return f"{(entity_type or '').strip().upper()} · {tui_name}"
    key = (entity_type or "unknown").lower()
    return _ENTITY_TYPE_LABELS.get(key) or (entity_type or "unknown").replace("_", " ").capitalize()


def _short_type_label(entity_type: str | None) -> str:
    """The small label shown inside a highlight, e.g. "organ" or "T047 · disease or syndrome"."""
    raw = (entity_type or "unknown").strip()
    tui_name = _tui_name(raw)
    if tui_name:
        return f"{raw.upper()} · {tui_name.lower()}"
    return raw.replace("_", " ").lower()

_ENTITY_TYPE_LABELS: dict[str, str] = {
    "gene": "Gene / protein",
    "disease": "Disease",
    "drug": "Chemical / drug",
    "species": "Species",
    "variant": "Variant / mutation",
    "cell_line": "Cell line",
    # BERN2-only categories, kept as their own buckets.
    "dna": "DNA",
    "rna": "RNA ",
    "cell_type": "Cell type",
}


# "no concept found"
_NULL_CANONICAL_IDS: frozenset[str] = frozenset({"cui-less", "-", ""})


def _is_real_canonical_id(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return text not in _NULL_CANONICAL_IDS


def _json_safe(value: Any) -> Any:
    """Replace NaN/Infinity floats with None so the result is valid JSON.

    Python's json emits a bare NaN (e.g. from a BERN2 confidence), which the
    browser's JSON.parse rejects, so the popup would silently fail to open.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


# Server-side mirror of the JS `databaseLink`.
def _database_link(canonical_id: str | None, entity_type: str | None) -> str | None:
    if not canonical_id:
        return None
    raw = str(canonical_id).strip()
    if not raw:
        return None
    lowered = raw.lower()
    if lowered.startswith("mesh:"):
        return f"https://meshb.nlm.nih.gov/record/ui?ui={raw.split(':', 1)[1]}"
    if lowered.startswith("ncbigene:") or lowered.startswith("ncbi_gene:") or lowered.startswith("ncbi-gene:"):
        return f"https://www.ncbi.nlm.nih.gov/gene/{raw.split(':', 1)[1]}"
    if (
        lowered.startswith("ncbitaxon:") or lowered.startswith("ncbitaxonomy:")
        or lowered.startswith("ncbi_taxonomy:") or lowered.startswith("ncbi-taxonomy:")
        or lowered.startswith("taxonomy:") or lowered.startswith("taxon:")
    ):
        return f"https://www.ncbi.nlm.nih.gov/taxonomy/{raw.split(':', 1)[1]}"
    if lowered.startswith("dbsnp:") or lowered.startswith("rs:"):
        return f"https://www.ncbi.nlm.nih.gov/snp/{raw.split(':', 1)[1]}"
    if lowered.startswith("chebi:"):
        return f"https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:{raw.split(':', 1)[1]}"
    if lowered.startswith("drugbank:"):
        return f"https://go.drugbank.com/drugs/{raw.split(':', 1)[1]}"
    if lowered.startswith("cvcl:") or lowered.startswith("cellosaurus:"):
        suffix = raw.split(":", 1)[1]
        ref = suffix if suffix.startswith("CVCL_") else f"CVCL_{suffix}"
        return f"https://www.cellosaurus.org/{ref}"
    if lowered.startswith("omim:") or lowered.startswith("mim:"):
        return f"https://www.omim.org/entry/{raw.split(':', 1)[1]}"
    if entity_type == "gene" and raw.isdigit():
        return f"https://www.ncbi.nlm.nih.gov/gene/{raw}"
    if entity_type == "species" and raw.isdigit():
        return f"https://www.ncbi.nlm.nih.gov/taxonomy/{raw}"
    # OBO ontologies (e.g. BERN2 cell_type -> Cell Ontology "CL:..."):
    # resolve via the PURL redirect.
    for obo_prefix in ("cl", "go", "doid", "uberon", "bto", "fma", "pato"):
        if lowered.startswith(obo_prefix + ":"):
            return f"https://purl.obolibrary.org/obo/{obo_prefix.upper()}_{raw.split(':', 1)[1]}"
    return None


_ID_PREFIX_CANONICAL: dict[str, str] = {
    "mesh": "MESH",
    "ncbigene": "NCBIGene", "ncbi_gene": "NCBIGene", "ncbi-gene": "NCBIGene",
    "ncbitaxon": "NCBITaxon", "ncbitaxonomy": "NCBITaxon", "ncbi_taxonomy": "NCBITaxon",
    "taxonomy": "NCBITaxon", "taxon": "NCBITaxon",
    "dbsnp": "dbSNP", "chebi": "CHEBI", "drugbank": "DrugBank",
    "cellosaurus": "CVCL", "cvcl": "CVCL", "omim": "OMIM", "mim": "OMIM",
    "cl": "CL", "go": "GO", "doid": "DOID", "uberon": "UBERON", "bto": "BTO", "fma": "FMA", "pato": "PATO",
}


def _format_canonical_id(canonical_id: Any, entity_type: str | None = None) -> str:
    """Render an id with one consistent prefix casing (mirror of the JS formatId).

    Only the prefix casing changes; the id value is untouched, and a bare
    gene/species number gains the prefix the prefixed annotators use.
    """
    if not canonical_id:
        return ""
    raw = str(canonical_id).strip()
    if ":" not in raw:
        if raw.isdigit():
            if entity_type == "gene":
                return f"NCBIGene:{raw}"
            if entity_type == "species":
                return f"NCBITaxon:{raw}"
        return raw
    prefix, rest = raw.split(":", 1)
    canon = _ID_PREFIX_CANONICAL.get(prefix.lower())
    return f"{canon}:{rest}" if canon else raw


def write_html_report(payload: dict[str, Any], output_path: Path) -> Path:
    """Generates a standalone HTML report next to the run's other outputs.

    Returns the absolute path of the file that was written.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content_html = _render_body(payload)
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    html = template.replace("<!--CONTENT-->", content_html)
    output_path.write_text(html, encoding="utf-8")
    return output_path.resolve()


def _render_body(payload: dict[str, Any]) -> str:
    summary = payload.get("annotation_summary") or {}
    documents = list(payload.get("documents") or [])
    annotations = list(payload.get("annotations") or [])

    annotators_used = sorted(
        {a.get("source") for a in annotations if a.get("source")}, key=_source_priority
    )
    annotators_text = ", ".join(
        _ANNOTATOR_LABELS.get(name, name) for name in annotators_used
    ) or "none"
    total_annotations = summary.get("annotation_count", len(annotations))
    document_count = payload.get("document_count", len(documents))

    parts: list[str] = []
    parts.append('<section class="summary">')
    parts.append('<div class="summary-headline">')
    parts.append(
        f'<p class="lede"><span class="big-number">{total_annotations}</span> '
        f'annotation{"s" if total_annotations != 1 else ""} across '
        f'<span class="big-number">{document_count}</span> '
        f'document{"s" if document_count != 1 else ""}</p>'
    )
    parts.append(f'<p class="meta">Annotators: {escape(annotators_text)}</p>')
    parts.append("</div>")
    if annotations:
        parts.append(_render_stats_panel(
            _compute_stats(annotations),
            heading="Bioconcepts in this run",
            css_class="stats-run",
        ))
    parts.append("</section>")
    parts.append(_render_legend(annotations))
    if annotations:
        parts.append(_render_filter_bar(annotators_used, annotations))

    if annotations:
        parts.append(_render_type_histogram(annotations))
    if len(documents) > 1:
        parts.append(_render_documents_overview(documents, annotations))

    for document in documents:
        parts.append(_render_document(document, annotations, annotators_used))

    if not documents:
        parts.append('<p class="hint">No documents in this run.</p>')

    if annotations and documents:
        parts.append(_render_graph(documents, annotations))
    parts.append(_render_config(annotators_used, annotations))
    return "\n".join(parts)


# A sentence ends at . ! or ? followed by space and a capital, digit or bracket, or at a line break.
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])|\n+")


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of each sentence of the text, spaces around it excluded."""
    spans = []
    start = 0
    for match in [*_SENTENCE_BREAK.finditer(text), None]:
        end = match.start() if match else len(text)
        piece = text[start:end]
        if piece.strip():
            left = start + len(piece) - len(piece.lstrip())
            spans.append((left, start + len(piece.rstrip())))
        if match:
            start = match.end()
    return spans


def build_graph_data(documents: list[dict[str, Any]], annotations: list[dict[str, Any]]) -> dict[str, Any]:
    """Entities and the sentences they occur in, for the co-mention graph.

    One node per keyword (case and extra spaces ignored, as in the comparison
    table), whichever annotators found it. Each mention records its document,
    sentence, annotator and colour family, so the page can draw the links for
    the annotators and entity types the user keeps switched on.
    """
    node_index: dict[str, int] = {}
    node_forms: list[Counter] = []
    node_families: list[Counter] = []
    node_types: list[set[str]] = []
    docs: list[dict[str, Any]] = []
    mentions: list[list[Any]] = []

    for document in documents:
        document_id = document.get("document_id")
        title_text = (document.get("title") or "").strip()
        abstract_text = (document.get("abstract") or "").strip()
        document_annotations = [a for a in annotations if a.get("document_id") == document_id]
        title_annotations, abstract_annotations = _split_annotations_by_region(document_annotations, len(title_text))

        sentences: list[str] = []
        doc_number = len(docs)
        for region_text, region_annotations in ((title_text, title_annotations), (abstract_text, abstract_annotations)):
            if not region_text:
                continue
            spans = sentence_spans(region_text)
            if not spans:
                continue
            starts = [start for start, _ in spans]
            first_sentence = len(sentences)
            sentences.extend(region_text[start:end] for start, end in spans)
            for annotation in _trim_spans(region_text, region_annotations):
                start, end = annotation.get("start"), annotation.get("end")
                if start is None or end is None or end <= start:
                    continue
                key = _span_key(region_text[start:end])
                if not key:
                    continue
                sentence = max(bisect_right(starts, start) - 1, 0)
                sentence_start, sentence_end = spans[sentence]
                if key not in node_index:
                    node_index[key] = len(node_forms)
                    node_forms.append(Counter())
                    node_families.append(Counter())
                    node_types.append(set())
                node = node_index[key]
                family = entity_family(annotation.get("entity_type"))
                node_forms[node][" ".join(region_text[start:end].split())] += 1
                node_families[node][family] += 1
                node_types[node].add(_type_label(annotation.get("entity_type")))
                mentions.append([
                    node,
                    doc_number,
                    first_sentence + sentence,
                    annotation.get("source") or "unknown",
                    family,
                    max(start - sentence_start, 0),
                    min(end, sentence_end) - sentence_start,
                ])
        docs.append(
            {
                "id": str(document_id or ""),
                "pmid": str(document.get("pmid") or ""),
                "title": title_text or str(document_id or "Document"),
                "anchor": _anchor_for(str(document_id or "")),
                "sentences": sentences,
            }
        )

    nodes = [
        {
            "label": forms.most_common(1)[0][0],
            "fam": families.most_common(1)[0][0],
            "types": sorted(types),
        }
        for forms, families, types in zip(node_forms, node_families, node_types)
    ]
    return {"docs": docs, "nodes": nodes, "mentions": mentions}


def _render_graph(documents: list[dict[str, Any]], annotations: list[dict[str, Any]]) -> str:
    """The co-mention graph: the section with its controls, and its data for the page's JavaScript."""
    data = build_graph_data(documents, annotations)
    if not data["nodes"]:
        return ""
    scope_options = ['<option value="all">All documents</option>'] if len(data["docs"]) > 1 else []
    for number, doc in enumerate(data["docs"]):
        name = doc["title"] if len(doc["title"]) <= 70 else doc["title"][:67] + "..."
        prefix = f'PMID {doc["pmid"]}: ' if doc["pmid"] else ""
        scope_options.append(f'<option value="{number}">{escape(prefix + name)}</option>')
    # "</" cannot appear inside a <script> element, so escape it in the JSON.
    payload = json.dumps(_json_safe(data), ensure_ascii=False).replace("</", "<\\/")
    return (
        '<section class="graph-section" id="entity-graph">'
        "<h3>Entity graph</h3>"
        '<p class="hint">Entities are linked when they are mentioned together. Bigger circles are mentioned more; '
        "thicker lines link entities that occur together more often. Click a circle or a line to see the sentences. "
        "The annotator and entity type filters above apply here too. Drag circles to rearrange them.</p>"
        '<div class="graph-controls">'
        f'<label>Show <select data-graph="scope">{"".join(scope_options)}</select></label>'
        '<label>Linked when in the same <select data-graph="mode">'
        '<option value="sentence">sentence</option><option value="document">document</option></select></label>'
        '<label>Entities <input type="range" data-graph="top" min="5" max="200" value="50"> '
        '<span data-graph-value="top">50</span></label>'
        '<label>Min. times together <input type="range" data-graph="min" min="1" max="10" value="1"> '
        '<span data-graph-value="min">1</span></label>'
        "</div>"
        '<div class="graph-layout">'
        '<div class="graph-canvas"><svg role="img" aria-label="Entity co-mention graph"></svg>'
        '<p class="graph-empty hint" hidden>No entities to show with the current filters.</p></div>'
        '<aside class="graph-panel"><p class="hint">Click an entity or a link to see where it occurs.</p></aside>'
        "</div>"
        f'<script type="application/json" id="graph-data">{payload}</script>'
        "</section>"
    )


def _render_config(annotators: list[str], annotations: list[dict[str, Any]]) -> str:
    """Labels and annotator order for the page's JavaScript (popup, filters, redraw)."""
    types = {a.get("entity_type") for a in annotations if a.get("entity_type")}
    config = {
        "annotator_labels": {name: _ANNOTATOR_LABELS.get(name, name) for name in annotators},
        "annotator_order": annotators,
        # keyed like the page's data: lowercase ("t191"), as in the popup payload
        "type_labels": {entity_type.lower(): _type_label(entity_type) for entity_type in types},
        "family_labels": _FAMILY_LABELS,
    }
    # "</" cannot appear inside a <script> element, so escape it in the JSON.
    payload = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/json" id="report-config">{payload}</script>'


def _render_filter_bar(annotators: list[str], annotations: list[dict[str, Any]]) -> str:
    """Checkboxes to show or hide highlights per annotator and per entity family."""
    present_families = {entity_family(a.get("entity_type")) for a in annotations}
    parts = ['<section class="filter-bar" aria-label="Highlight filters">']
    parts.append('<div class="filter-group"><span class="filter-title">Annotators</span>')
    for name in annotators:
        parts.append(
            f'<label class="filter-chip"><input type="checkbox" data-filter="source" '
            f'value="{escape(name, quote=True)}" checked> {escape(_ANNOTATOR_LABELS.get(name, name))}</label>'
        )
    parts.append("</div>")
    parts.append('<div class="filter-group"><span class="filter-title">Entity types</span>')
    for family, label in _FAMILY_LABELS.items():
        if family not in present_families:
            continue
        parts.append(
            f'<label class="filter-chip fam-{family}"><input type="checkbox" data-filter="family" '
            f'value="{family}" checked> {escape(label)}</label>'
        )
    parts.append("</div>")
    parts.append(
        '<div class="filter-group"><label class="filter-chip filter-option">'
        '<input type="checkbox" data-filter="labels" checked> Show type labels</label></div>'
    )
    parts.append("</section>")
    return "\n".join(parts)


def _compute_stats(annotations: list[dict[str, Any]]) -> dict[str, list[tuple[str, int]]]:
    """Group annotations by entity type, then by case-insensitive span text.
    Multiple annotators tagging the same span at the same
    offset count as one mention, matching PubTator3's "Bioconcepts and
    mentions" panel.
    """
    positions: dict[str, dict[str, set[tuple[Any, Any]]]] = {}
    canonical: dict[str, dict[str, str]] = {}
    for annotation in annotations:
        span_text = " ".join((annotation.get("span_text") or "").split())
        if not span_text:
            continue
        entity_type = (annotation.get("entity_type") or "unknown").lower()
        key = _span_key(span_text)
        positions.setdefault(entity_type, {}).setdefault(key, set()).add(
            (annotation.get("start"), annotation.get("end"))
        )
        canonical.setdefault(entity_type, {}).setdefault(key, span_text)

    result: dict[str, list[tuple[str, int]]] = {}
    for entity_type, by_key in positions.items():
        rows = [
            (canonical[entity_type][key], len(positions_set))
            for key, positions_set in by_key.items()
        ]
        rows.sort(key=lambda item: (-item[1], item[0].casefold()))
        result[entity_type] = rows
    return result


def _render_stats_panel(
    stats: dict[str, list[tuple[str, int]]],
    *,
    heading: str,
    css_class: str,
    limit_per_type: int = 15,
) -> str:
    if not stats:
        return ""
    type_order = [
        key for key in ("disease", "drug", "gene", "species", "variant", "cell_line")
        if key in stats
    ]
    type_order += [key for key in stats if key not in type_order]

    parts: list[str] = [f'<aside class="stats-panel {css_class}">']
    parts.append(f'<h4>{escape(heading)}</h4>')
    for entity_type in type_order:
        rows = stats[entity_type]
        if not rows:
            continue
        label = _type_label(entity_type)
        total = sum(count for _, count in rows)
        parts.append(
            f'<details class="stats-group stats-group-{escape(entity_type)} fam-{entity_family(entity_type)}">'
            f'<summary><span class="stats-type">{escape(label)}</span>'
            f'<span class="stats-type-total">{total}</span></summary>'
        )
        parts.append('<ul class="stats-list">')
        max_count = rows[0][1] if rows else 1
        for keyword, count in rows[:limit_per_type]:
            width_pct = max(6, int(round(100 * count / max_count))) if max_count else 0
            parts.append(
                f'<li>'
                f'<span class="stats-keyword">{escape(keyword)}</span>'
                f'<span class="stats-bar-track"><span class="stats-bar-fill" style="width:{width_pct}%"></span></span>'
                f'<span class="stats-count">{count}</span>'
                f'</li>'
            )
        if len(rows) > limit_per_type:
            remaining = len(rows) - limit_per_type
            parts.append(f'<li class="stats-more">+{remaining} more</li>')
        parts.append("</ul></details>")
    parts.append("</aside>")
    return "\n".join(parts)


def _render_type_histogram(annotations: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for annotation in annotations:
        entity_type = (annotation.get("entity_type") or "unknown").lower()
        counts[entity_type] = counts.get(entity_type, 0) + 1
    if not counts:
        return ""
    ordered = [
        key for key in ("disease", "drug", "gene", "species", "variant", "cell_line")
        if key in counts
    ]
    ordered += sorted(key for key in counts if key not in ordered)
    max_count = max(counts.values())

    parts = ['<section class="chart-card">',
             '<h4>Entity type distribution</h4>',
             '<ul class="type-histogram">']
    for entity_type in ordered:
        count = counts[entity_type]
        label = _type_label(entity_type)
        width = max(4, int(round(100 * count / max_count)))
        parts.append(
            f'<li class="hist-row hist-row-{escape(entity_type)} fam-{entity_family(entity_type)}">'
            f'<span class="hist-label">{escape(label)}</span>'
            f'<span class="hist-track"><span class="hist-fill" style="width:{width}%"></span></span>'
            f'<span class="hist-count">{count}</span>'
            f'</li>'
        )
    parts.append('</ul></section>')
    return "\n".join(parts)


def _render_documents_overview(
    documents: list[dict[str, Any]], annotations: list[dict[str, Any]]
) -> str:
    by_doc: dict[Any, dict[str, int]] = {}
    for annotation in annotations:
        document_id = annotation.get("document_id")
        entity_type = (annotation.get("entity_type") or "unknown").lower()
        by_doc.setdefault(document_id, {})[entity_type] = (
            by_doc.setdefault(document_id, {}).get(entity_type, 0) + 1
        )

    doc_totals = [
        (doc, sum(by_doc.get(doc.get("document_id"), {}).values()))
        for doc in documents
    ]
    max_total = max((total for _, total in doc_totals), default=0)
    if max_total == 0:
        return ""

    type_order = ("disease", "drug", "gene", "species", "variant", "cell_line")

    parts = ['<section class="chart-card">',
             '<h4>Annotations per document</h4>',
             '<ul class="doc-overview">']
    for document, total in doc_totals:
        doc_id = str(document.get("document_id") or "")
        pmid = document.get("pmid")
        title = (document.get("title") or doc_id or "Document")
        truncated = title if len(title) <= 70 else title[:67] + "..."
        link_text = f"PMID {pmid}" if pmid else doc_id or "Document"
        anchor = _anchor_for(doc_id)
        type_counts = by_doc.get(document.get("document_id"), {})
        ordered_types = [t for t in type_order if t in type_counts]
        ordered_types += [t for t in type_counts if t not in ordered_types]

        segments: list[str] = []
        running_total = sum(type_counts.values())
        for entity_type in ordered_types:
            seg_count = type_counts[entity_type]
            seg_width = 100 * seg_count / running_total if running_total else 0
            segments.append(
                f'<span class="doc-seg doc-seg-{escape(entity_type)} fam-{entity_family(entity_type)}" '
                f'style="width:{seg_width:.2f}%" '
                f'title="{escape(_type_label(entity_type))}: {seg_count}"></span>'
            )
        bar_width = max(8, int(round(100 * total / max_total)))
        parts.append(
            f'<li class="doc-row">'
            f'<a class="doc-link" href="#{escape(anchor, quote=True)}">{escape(link_text)}</a>'
            f'<span class="doc-title">{escape(truncated)}</span>'
            f'<span class="doc-track"><span class="doc-bar" style="width:{bar_width}%">{"".join(segments)}</span></span>'
            f'<span class="doc-count">{total}</span>'
            f'</li>'
        )
    parts.append('</ul></section>')
    return "\n".join(parts)


def _anchor_for(document_id: str) -> str:
    return "doc-" + "".join(ch if ch.isalnum() else "-" for ch in document_id).strip("-").lower()


def _render_legend(annotations: list[dict[str, Any]] | None = None) -> str:
    """One chip per colour family; hovering a chip lists the entity types it holds.

    If annotations are passed, only families (and types) present in this run are
    shown; otherwise every family is shown.
    """
    if annotations is None:
        families = {family: [] for family in _FAMILY_LABELS}
    else:
        families: dict[str, list[str]] = {}
        for annotation in annotations:
            entity_type = annotation.get("entity_type") or "unknown"
            types = families.setdefault(entity_family(entity_type), [])
            label = _type_label(entity_type)
            if label not in types:
                types.append(label)
    items = []
    for family, label in _FAMILY_LABELS.items():
        if family not in families:
            continue
        types = sorted(families[family])
        title = f' title="{escape(", ".join(types), quote=True)}"' if types else ""
        items.append(f'<span class="legend-chip fam-{family}"{title}>{escape(label)}</span>')
    return '<div class="legend">' + "".join(items) + "</div>"


def _render_document(
    document: dict[str, Any],
    all_annotations: list[dict[str, Any]],
    annotators: list[str] | None = None,
) -> str:
    document_id = document.get("document_id")
    document_annotations = [
        annotation for annotation in all_annotations
        if annotation.get("document_id") == document_id
    ]
    comparison_rows = group_annotations_by_span(document_annotations)
    cross_lookup = {_span_key(row["keyword"]): row["by_source"] for row in comparison_rows}

    title_text = (document.get("title") or "").strip()
    abstract_text = (document.get("abstract") or "").strip()
    title_annotations, abstract_annotations = _split_annotations_by_region(
        document_annotations, len(title_text)
    )

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
    parts: list[str] = [f'<details class="document" id="{escape(anchor, quote=True)}">']
    parts.append(
        f'<summary class="doc-summary">'
        f'<span class="doc-summary-title">{plain_title}</span>'
        f'<span class="doc-summary-count">{count_label}</span>'
        f"</summary>"
    )
    parts.append('<div class="doc-body">')
    parts.append(f"<h2>{title_html}</h2>")
    parts.append(
        f'<p class="meta">{pmid_html}'
        f"{' | ' if pmid else ''}{count_label} on this document</p>"
    )
    parts.append('<div class="doc-grid">')
    parts.append('<div class="doc-main">')
    parts.append("<h3>Abstract</h3>")
    parts.append('<p class="hint">Highlights show entities found by any annotator. Click a highlight for full details across annotators.</p>')
    if abstract_text:
        parts.append(_annotated_text("div", "annotated-text", abstract_text, abstract_annotations, cross_lookup))
    else:
        parts.append('<div class="annotated-text"><span class="hint">No abstract available.</span></div>')
    parts.append("</div>")
    parts.append(_render_stats_panel(
        _compute_stats(document_annotations),
        heading="Bioconcepts in this document",
        css_class="stats-doc",
    ))
    parts.append("</div>")

    parts.append(
        f'<details class="comparison-section">'
        f'<summary><h3>Comparison across annotators</h3>'
        f'<span class="hint">{len(comparison_rows)} unique keyword'
        f'{"s" if len(comparison_rows) != 1 else ""} found by at least one annotator</span></summary>'
    )
    parts.append('<div class="comparison-scroll">')
    parts.append(_render_comparison_table(comparison_rows, annotators))
    parts.append("</div></details>")
    parts.append("</div>")
    parts.append("</details>")
    return "\n".join(parts)


def _split_annotations_by_region(
    annotations: list[dict[str, Any]], title_length: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition canonical-scheme annotations into title-region and abstract-region.

    Canonical text is `title + "\\n" + abstract`. Annotations with offsets
    fully inside [0, title_length) belong to the title. Annotations starting
    at or past `title_length + 2` belong to the abstract; their offsets are
    rebased so position 0 maps to the start of the abstract.
    """
    title_annotations: list[dict[str, Any]] = []
    abstract_annotations: list[dict[str, Any]] = []
    # Document.text is "title\n\nabstract" only when there is a title; a
    # title-less doc (e.g. plain-text input) is just the abstract, no shift.
    body_offset = title_length + 2 if title_length else 0
    for annotation in annotations:
        start = annotation.get("start")
        end = annotation.get("end")
        if start is None or end is None:
            continue
        if title_length and end <= title_length:
            title_annotations.append(annotation)
        elif start >= body_offset:
            abstract_annotations.append(
                {**annotation, "start": start - body_offset, "end": end - body_offset}
            )
    return title_annotations, abstract_annotations


def _render_comparison_table(rows: list[dict[str, Any]], sources: list[str] | None = None) -> str:
    """One column per annotator: every annotator of the run, or those in these rows."""
    if not rows:
        return '<p class="hint">No annotations to compare.</p>'

    if not sources:
        sources = sorted({source for row in rows for source in row["by_source"]}, key=_source_priority)
    head_cells = "".join(
        f"<th>{escape(_ANNOTATOR_LABELS.get(source, source))}</th>" for source in sources
    )
    body_rows: list[str] = []
    for row in rows:
        cells = [f'<td><code>{escape(row["keyword"])}</code></td>']
        for source in sources:
            hits = row["by_source"].get(source) or []
            cells.append(f"<td>{_render_hits_cell(hits)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<table class="comparison"><thead><tr>'
        f"<th>Keyword</th>{head_cells}"
        "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table>"
    )


def _render_hits_cell(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return '<span class="absent">·</span>'
    lines: list[str] = []
    for hit in hits:
        entity_type = (hit.get("entity_type") or "").lower() or "unknown"
        label = _type_label(entity_type)
        canonical_id = hit.get("canonical_id") if _is_real_canonical_id(hit.get("canonical_id")) else None
        canonical_name = hit.get("canonical_name")
        mentions = hit.get("mentions")
        line = f'<div class="entity-type">{escape(str(label))}</div>'
        if canonical_id:
            link = _database_link(canonical_id, entity_type)
            code = f'<code>{escape(_format_canonical_id(canonical_id, entity_type))}</code>'
            if link:
                code = f'<a href="{escape(link, quote=True)}" target="_blank" rel="noopener">{code}</a>'
            line += f"<div>{code}</div>"
        if canonical_name:
            line += f"<div><small>{escape(str(canonical_name))}</small></div>"
        score = hit.get("normalization_score")
        if isinstance(score, (int, float)) and math.isfinite(score):
            line += f"<div><small>norm score {score:.3f}</small></div>"
        if mentions and mentions > 1:
            line += f'<div><small>{mentions} mentions</small></div>'
        lines.append(line)
    return "<br>".join(lines)


def build_canonical_text(document: dict[str, Any]) -> str:
    title = document.get("title") or ""
    abstract = document.get("abstract") or ""
    if title and abstract:
        return f"{title}\n{abstract}"
    return title or abstract


def _source_priority(source: str | None) -> tuple[int, str]:
    """Order of annotators: the listed ones first, then the rest alphabetically."""
    return (_SOURCE_PRIORITY.get(source or "", 99), source or "")


def render_highlighted_text(
    text: str,
    annotations: list[dict[str, Any]],
    cross_annotator_lookup: dict[str, dict[str, list[dict[str, Any]]]] | None = None,
) -> str:
    """Render the document text with non-overlapping <mark> spans.

    """
    if not annotations:
        return escape(text).replace("\n", "<br>\n")

    sorted_annotations = sorted(
        annotations,
        key=lambda a: (
            a.get("start") or 0,
            _source_priority(a.get("source")),
            -((a.get("end") or 0) - (a.get("start") or 0)),
        ),
    )

    chosen: list[dict[str, Any]] = []
    last_end = -1
    for annotation in sorted_annotations:
        start = annotation.get("start")
        end = annotation.get("end")
        if start is None or end is None or end <= start:
            continue
        if start >= last_end:
            chosen.append(annotation)
            last_end = end

    out: list[str] = []
    position = 0
    for annotation in chosen:
        start = annotation["start"]
        end = annotation["end"]
        if start > position:
            out.append(escape(text[position:start]).replace("\n", "<br>\n"))
        rendered_span = escape(text[start:end])
        entity_type = (annotation.get("entity_type") or "unknown").lower()
        popup_payload = _popup_payload(annotation, text, start, end, cross_annotator_lookup)
        data_attribute = escape(json.dumps(_json_safe(popup_payload), default=str), quote=True)

        out.append(
            f'<mark class="entity entity-{escape(entity_type)}" '
            f'data-family="{entity_family(annotation.get("entity_type"))}" '
            f'data-label="{escape(_short_type_label(annotation.get("entity_type")), quote=True)}" '
            f'data-entity="{data_attribute}" tabindex="0" role="button">{rendered_span}</mark>'
        )
        position = end
    if position < len(text):
        out.append(escape(text[position:]).replace("\n", "<br>\n"))
    return "".join(out)


def _popup_payload(
    annotation: dict[str, Any],
    text: str,
    start: int,
    end: int,
    cross_annotator_lookup: dict[str, dict[str, list[dict[str, Any]]]] | None,
) -> dict[str, Any]:
    """What the popup shows for a highlight: the entity plus every annotator's hits."""
    source = annotation.get("source") or "unknown"
    raw_canonical_id = annotation.get("canonical_id")
    canonical_id = raw_canonical_id if _is_real_canonical_id(raw_canonical_id) else ""
    keyword_key = _span_key(annotation.get("span_text") or text[start:end])
    cross_hit = cross_annotator_lookup.get(keyword_key) if cross_annotator_lookup else None
    return {
        "keyword": text[start:end],
        "entity_type": (annotation.get("entity_type") or "unknown").lower(),
        "canonical_id": canonical_id or None,
        "canonical_name": annotation.get("canonical_name") or None,
        "primary_source": source,
        "by_source": cross_hit or {source: [_hit_record(annotation)]},
    }


def _trim_spans(text: str, annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Move span offsets past leading/trailing spaces, so highlights hold only the entity."""
    trimmed = []
    for annotation in annotations:
        start, end = annotation.get("start"), annotation.get("end")
        if start is None or end is None or end <= start:
            trimmed.append(annotation)
            continue
        while start < end and text[start:start + 1].isspace():
            start += 1
        while end > start and text[end - 1:end].isspace():
            end -= 1
        if (start, end) != (annotation["start"], annotation["end"]):
            annotation = {**annotation, "start": start, "end": end, "span_text": text[start:end]}
        trimmed.append(annotation)
    return trimmed


def _span_key(span_text: str) -> str:
    """Comparison key of a keyword: case and extra spaces ignored ("Breast  cancer " = "breast cancer")."""
    return " ".join(span_text.split()).casefold()


def _annotated_text(
    tag: str,
    css_class: str,
    text: str,
    annotations: list[dict[str, Any]],
    cross_annotator_lookup: dict[str, dict[str, list[dict[str, Any]]]] | None,
) -> str:
    """Highlighted text, plus the data the page needs to redraw it when filters change.

    The highlights are drawn here, so the page works without JavaScript; the
    data-* attributes let the browser redraw them for the annotators and entity
    types the user keeps switched on (revealing tags hidden under others).
    """
    annotations = _trim_spans(text, annotations)
    items = []
    for annotation in annotations:
        start, end = annotation.get("start"), annotation.get("end")
        if start is None or end is None or end <= start:
            continue
        items.append(
            {
                "s": start,
                "e": end,
                "src": annotation.get("source") or "unknown",
                "type": (annotation.get("entity_type") or "unknown").lower(),
                "fam": entity_family(annotation.get("entity_type")),
                "lab": _short_type_label(annotation.get("entity_type")),
                "p": _popup_payload(annotation, text, start, end, cross_annotator_lookup),
            }
        )
    data = escape(json.dumps(_json_safe(items), default=str), quote=True)
    body = render_highlighted_text(text, annotations, cross_annotator_lookup)
    return (
        f'<{tag} class="{css_class}" data-text="{escape(text, quote=True)}" '
        f'data-annotations="{data}">{body}</{tag}>'
    )


def group_annotations_by_span(annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group annotations across annotators by case-insensitive span text.

    Each row carries the keyword and a dict of annotator -> list of hits.
    Within each source, hits with identical (entity_type, canonical_id,
    canonical_name) collapse to one row with a `mentions` count.
    """
    groups: dict[str, dict[str, Any]] = {}
    for annotation in annotations:
        span_text = " ".join((annotation.get("span_text") or "").split())
        if not span_text:
            continue
        key = _span_key(span_text)
        bucket = groups.setdefault(
            key,
            {
                "keyword": span_text,
                "by_source": defaultdict(list),
                "first_offset": annotation.get("start") or 0,
            },
        )
        source = annotation.get("source") or "unknown"
        bucket["by_source"][source].append(_hit_record(annotation))
        if (annotation.get("start") or 0) < bucket["first_offset"]:
            bucket["first_offset"] = annotation.get("start") or 0

    rows: list[dict[str, Any]] = []
    for bucket in groups.values():
        by_source = {source: _dedupe_hits(hits) for source, hits in bucket["by_source"].items()}
        rows.append(
            {
                "keyword": bucket["keyword"],
                "by_source": by_source,
                "annotator_count": len(by_source),
                "first_offset": bucket["first_offset"],
            }
        )
    rows.sort(key=lambda row: (row["first_offset"], row["keyword"].casefold()))
    return rows


def _hit_record(annotation: dict[str, Any]) -> dict[str, Any]:
    canonical_id = annotation.get("canonical_id")
    return {
        "entity_type": annotation.get("entity_type"),
        "canonical_id": canonical_id if _is_real_canonical_id(canonical_id) else None,
        "canonical_name": annotation.get("canonical_name"),
        "start": annotation.get("start"),
        "end": annotation.get("end"),
        "confidence": annotation.get("confidence"),
        "normalization_score": annotation.get("normalization_score"),
    }


def _dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse hits with identical (entity_type, canonical_id, canonical_name).

    Keeps the highest confidence and normalization score, and tracks how many mentions collapsed.
    """
    deduped: dict[tuple[Any, Any, Any], dict[str, Any]] = {}
    for hit in hits:
        key = (hit.get("entity_type"), hit.get("canonical_id"), hit.get("canonical_name"))
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = {**hit, "mentions": 1}
            continue
        existing["mentions"] += 1
        for score in ("confidence", "normalization_score"):
            new_value = hit.get(score)
            old_value = existing.get(score)
            if isinstance(new_value, (int, float)) and (
                not isinstance(old_value, (int, float)) or new_value > old_value
            ):
                existing[score] = new_value
    return list(deduped.values())
